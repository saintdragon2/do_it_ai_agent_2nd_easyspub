import os
from functools import lru_cache
from pathlib import Path
from typing import Literal, TypedDict

from dotenv import load_dotenv
from langchain.agents import AgentState, create_agent
from langchain.chat_models import init_chat_model
from langchain.messages import (
    AIMessageChunk,
    SystemMessage,
    ToolMessage,
)
from langchain.tools import ToolRuntime
from langchain_core.documents import Document
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command
from typing_extensions import NotRequired

from retriever import Retriever


load_dotenv()

REPO_ROOT = Path(__file__).resolve().parents[2]


class State(AgentState):
    docs: NotRequired[list[Document]]


class Intent(TypedDict):
    select_agent: Literal[
        "casual_talk",
        "city_policy_agent",
        "culture_agent",
    ]


def _serialize_docs(docs: list[Document]) -> str:
    return "\n\n".join(
        f"Source: {doc.metadata}\nContent: {doc.page_content}"
        for doc in docs
    )


@lru_cache(maxsize=1)
def get_chat_graph():
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY가 설정되어 있지 않습니다.")

    llm_model = init_chat_model(
        "gpt-5.4-mini",
        temperature=0,
    )

    city_retriever = Retriever(
        persist_directory=REPO_ROOT / "chap09/chroma_store",
        data_files=[
            REPO_ROOT / "chap09/data/OneNYC_2050_Strategic_Plan.pdf",
            REPO_ROOT / "chap09/data/2040_seoul_plan.pdf",
        ],
    )
    culture_retriever = Retriever(
        persist_directory=REPO_ROOT / "chap15/chroma_store",
        data_files=[
            REPO_ROOT / "chap15/data/kdi_kpop_공연산업의_발전_방안_연구.pdf",
        ],
    )

    def determine_intent(state: State) -> Command[Literal[
        "casual_talk",
        "city_policy_agent",
        "culture_agent",
    ]]:
        llm_with_intent = llm_model.with_structured_output(Intent)
        response = llm_with_intent.invoke([
            SystemMessage(content=(
                "너는 사용자의 의도를 분류한다. "
                "도시 계획이나 정책 질문은 'city_policy_agent', "
                "공연과 문화산업 질문은 'culture_agent', "
                "그 외 대화는 'casual_talk'를 반환하라."
            )),
            *state.get("messages", []),
        ])
        return Command(goto=response["select_agent"])

    def casual_talk(state: State) -> State:
        response = llm_model.invoke([
            SystemMessage(content=(
                "너는 도시 정책과 문화산업을 안내하는 친절한 도우미이다. "
                "존댓말로 간결하게 답하라."
            )),
            *state.get("messages", []),
        ])
        return {"messages": [response]}

    def city_policy_tool(
        query: str,
        runtime: ToolRuntime[None, State],
    ):
        """도시 계획과 정책 문서를 검색한다."""
        docs = city_retriever.invoke(query)
        return Command(update={
            "docs": docs,
            "messages": [ToolMessage(
                content=_serialize_docs(docs),
                tool_call_id=runtime.tool_call_id,
            )],
        })

    def culture_tool(
        query: str,
        runtime: ToolRuntime[None, State],
    ):
        """공연과 문화산업 문서를 검색한다."""
        docs = culture_retriever.invoke(query)
        return Command(update={
            "docs": docs,
            "messages": [ToolMessage(
                content=_serialize_docs(docs),
                tool_call_id=runtime.tool_call_id,
            )],
        })

    city_policy_agent = create_agent(
        llm_model,
        system_prompt=(
            "도시 계획과 정책 질문에 친절하게 답하라. "
            "관련 질문에는 반드시 도구로 문서를 검색한 뒤 근거에 기반해 답하라."
        ),
        tools=[city_policy_tool],
        state_schema=State,
        name="city_policy_agent",
    )
    culture_agent = create_agent(
        llm_model,
        system_prompt=(
            "공연과 문화산업 질문에 친절하게 답하라. "
            "관련 질문에는 반드시 도구로 문서를 검색한 뒤 근거에 기반해 답하라."
        ),
        tools=[culture_tool],
        state_schema=State,
        name="culture_agent",
    )

    graph_builder = StateGraph(State)
    graph_builder.add_node("determine_intent", determine_intent)
    graph_builder.add_node("casual_talk", casual_talk)
    graph_builder.add_node("city_policy_agent", city_policy_agent)
    graph_builder.add_node("culture_agent", culture_agent)

    graph_builder.add_edge(START, "determine_intent")
    graph_builder.add_edge("casual_talk", END)
    graph_builder.add_edge("city_policy_agent", END)
    graph_builder.add_edge("culture_agent", END)

    return graph_builder.compile()


def _message_text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            block.get("text", "")
            for block in content
            if isinstance(block, dict) and block.get("type") == "text"
        )
    return ""


async def ask_chatbot(messages: list[dict[str, str]]) -> str:
    graph = get_chat_graph()
    result = await graph.ainvoke(
        {"messages": messages, "docs": []},
    )
    return _message_text(result["messages"][-1].content)


async def stream_chatbot(messages: list[dict[str, str]]):
    graph = get_chat_graph()

    async for part in graph.astream(
        {"messages": messages, "docs": []},
        stream_mode="messages",
        subgraphs=True,
        version="v2",
    ):
        if part["type"] != "messages":
            continue

        message_chunk, metadata = part["data"]
        namespace = part["ns"]
        node = metadata.get("langgraph_node")

        is_answer_node = node == "casual_talk" or (
            namespace
            and (
                namespace[0].startswith("city_policy_agent:")
                or namespace[0].startswith("culture_agent:")
            )
        )

        if (
            is_answer_node
            and isinstance(message_chunk, AIMessageChunk)
            and not message_chunk.tool_call_chunks
        ):
            text = _message_text(message_chunk.content)
            if text:
                yield text
