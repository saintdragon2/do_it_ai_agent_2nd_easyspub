import os
from collections.abc import AsyncIterator
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal, TypedDict

from dotenv import load_dotenv
from langchain.agents import AgentState, create_agent
from langchain.chat_models import init_chat_model
from langchain.messages import AIMessageChunk, SystemMessage, ToolMessage
from langchain.tools import ToolRuntime
from langchain_core.documents import Document
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command
from typing_extensions import NotRequired

from retriever import Retriever


load_dotenv()

SEC02_DIR = Path(__file__).resolve().parent.parent / "sec02"


def replace_docs(_current, new):
    return new


class State(AgentState):
    docs: NotRequired[Annotated[list[Document], replace_docs]]


@lru_cache(maxsize=1)
def get_rag_graph():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY가 설정되어 있지 않습니다.")

    llm_model = init_chat_model(
        "gpt-5.4-mini",
        temperature=0,
        api_key=api_key,
    )

    class Intent(TypedDict):
        select_agent: Literal[
            "casual_talk",
            "city_policy_agent",
            "culture_agent",
        ]

    def determine_intent(state: State) -> Command[Literal[
        "casual_talk",
        "city_policy_agent",
        "culture_agent",
    ]]:
        llm_with_intent_model = llm_model.with_structured_output(Intent)
        system_message = SystemMessage(
            content=(
                "너는 사용자의 의도를 파악하는 역할을 수행한다. "
                "사용자가 도시 정책 관련 질문을 하면 'city_policy_agent'를, "
                "문화 관련 질문을 하면 'culture_agent'를, "
                "그 외의 일반적인 대화는 'casual_talk'를 반환하라."
            )
        )
        response = llm_with_intent_model.invoke([
            system_message,
            *state.get("messages", []),
        ])
        return Command(goto=response["select_agent"])

    def casual_talk(state: State) -> State:
        system_message = SystemMessage(
            content=(
                "너는 도시 정책과 문화 분야를 설명하는 친절한 도우미이다. "
                "사용자의 일반적인 대화에도 친절하게 답하라."
            )
        )
        response = llm_model.invoke([
            system_message,
            *state.get("messages", []),
        ])
        return {"messages": [response]}

    retriever_city_policy = Retriever(
        persist_directory=SEC02_DIR / "chroma_store_city",
        data_files=[
            SEC02_DIR / "data_city" / "OneNYC_2050_Strategic_Plan.pdf",
            SEC02_DIR / "data_city" / "2040_seoul_plan.pdf",
        ],
        chunk_size=1000,
        chunk_overlap=100,
        k=5,
    )
    retriever_culture = Retriever(
        persist_directory=SEC02_DIR / "chroma_store_culture",
        data_files=[
            SEC02_DIR
            / "data_culture"
            / "kdi_kpop_공연산업의_발전_방안_연구.pdf",
        ],
        chunk_size=1000,
        chunk_overlap=100,
        k=5,
    )

    def retrieve_docs(query: str, retriever: Retriever):
        docs = retriever.invoke(query)
        serialized_docs = "\n\n".join(
            f"Source: {doc.metadata}\nContent: {doc.page_content}"
            for doc in docs
        )
        return docs, serialized_docs

    def city_policy_retriever(
        query: str,
        runtime: ToolRuntime[None, State],
    ):
        """도시 정책 관련 문서를 검색한다.

        param query: 사용자가 검색하고자 하는 내용을 명료하게 작성한 문자열
        """
        docs, serialized_docs = retrieve_docs(query, retriever_city_policy)
        return Command(
            update={
                "docs": docs,
                "messages": [ToolMessage(
                    content=serialized_docs,
                    tool_call_id=runtime.tool_call_id,
                )],
            }
        )

    def culture_retriever(
        query: str,
        runtime: ToolRuntime[None, State],
    ):
        """문화 관련 문서를 검색한다.

        param query: 사용자가 검색하고자 하는 내용을 명료하게 작성한 문자열
        """
        docs, serialized_docs = retrieve_docs(query, retriever_culture)
        return Command(
            update={
                "docs": docs,
                "messages": [ToolMessage(
                    content=serialized_docs,
                    tool_call_id=runtime.tool_call_id,
                )],
            }
        )

    city_policy_agent = create_agent(
        llm_model,
        system_prompt=(
            "도시 계획 관련 질문에 친절하고 공손하게 답하라. "
            "도시 계획 관련 내용은 반드시 도구로 검색하고 근거에 기반하여 답하라."
        ),
        tools=[city_policy_retriever],
        state_schema=State,
        name="city_policy_agent",
    )
    culture_agent = create_agent(
        llm_model,
        system_prompt=(
            "문화 관련 질문에 친절하고 공손하게 답하라. "
            "문화 관련 내용은 반드시 도구로 검색하고 근거에 기반하여 답하라."
        ),
        tools=[culture_retriever],
        state_schema=State,
        name="culture_agent",
    )

    class UsedChunks(TypedDict):
        used_docs: list[int]

    def check_used_chunks(state: State) -> State:
        last_answer = (
            state.get("messages", [])[-1]
            if state.get("messages")
            else None
        )
        docs = state.get("docs", [])
        serialized_docs = "\n\n".join(
            f"index:{index}\t{doc.metadata}\nContent: {doc.page_content}"
            for index, doc in enumerate(docs)
        )
        llm_with_structured_output = llm_model.with_structured_output(UsedChunks)
        used_chunks_response = llm_with_structured_output.invoke([
            SystemMessage(
                content=(
                    "사용자의 질문에 대한 마지막 답변을 만들 때 사용된 문서 청크의 "
                    "인덱스를 반환하라. docs는 0부터 시작하며, 사용된 청크가 없으면 "
                    "빈 리스트를 반환하라.\n\n"
                    f"Last answer: {last_answer.content if last_answer else 'None'}"
                    "\n-------------------\n"
                    f"Docs:\n{serialized_docs}"
                )
            )
        ])

        for index, doc in enumerate(docs):
            doc.metadata["used"] = index in used_chunks_response["used_docs"]
        return {"docs": docs}

    graph_builder = StateGraph(State)
    graph_builder.add_node("determine_intent", determine_intent)
    graph_builder.add_node("casual_talk", casual_talk)
    graph_builder.add_node("city_policy_agent", city_policy_agent)
    graph_builder.add_node("culture_agent", culture_agent)
    graph_builder.add_node("check_used_chunks", check_used_chunks)

    graph_builder.add_edge(START, "determine_intent")
    graph_builder.add_edge("casual_talk", END)
    graph_builder.add_edge("city_policy_agent", "check_used_chunks")
    graph_builder.add_edge("culture_agent", "check_used_chunks")
    graph_builder.add_edge("check_used_chunks", END)

    return graph_builder.compile()


async def ask_rag_agent(
    messages: list[dict[str, str]],
) -> tuple[str, list[Document]]:
    graph = get_rag_graph()
    result = await graph.ainvoke({"messages": messages})
    answer = str(result["messages"][-1].content)
    docs = result.get("docs", [])
    return answer, docs


async def stream_rag_agent(
    graph,
    messages: list[dict[str, str]],
) -> AsyncIterator[dict[str, object]]:
    documents_sent = False

    async for namespace, mode, data in graph.astream(
        {"messages": messages},
        stream_mode=["messages", "updates"],
        subgraphs=True,
    ):
        if mode == "messages":
            message_chunk, metadata = data
            if not isinstance(message_chunk, AIMessageChunk):
                continue

            node = metadata.get("langgraph_node")
            from_rag_agent = bool(namespace) and node == "model" and (
                namespace[0].startswith("city_policy_agent:")
                or namespace[0].startswith("culture_agent:")
            )
            if node != "casual_talk" and not from_rag_agent:
                continue

            if message_chunk.text:
                yield {
                    "type": "token",
                    "content": message_chunk.text,
                }

        if mode == "updates" and not namespace:
            check_result = data.get("check_used_chunks", {})
            if "docs" not in check_result:
                continue

            documents_sent = True
            yield {
                "type": "documents",
                "documents": [
                    document.model_dump()
                    for document in check_result["docs"]
                    if document.metadata.get("used") is True
                ],
            }

    if not documents_sent:
        yield {
            "type": "documents",
            "documents": [],
        }
