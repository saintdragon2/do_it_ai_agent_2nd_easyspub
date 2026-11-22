from langchain.messages import SystemMessage, HumanMessage, AIMessageChunk, ToolMessage
from langgraph.graph import StateGraph, START, END
from langchain.chat_models import init_chat_model
from typing import Annotated, Literal, TypedDict
from langgraph.types import Command
from langchain.agents import AgentState
from langchain_core.documents import Document
from typing_extensions import NotRequired

from retriever import Retriever
from langchain.agents import create_agent
from langchain.tools import ToolRuntime
from functools import lru_cache
import os
from dotenv import load_dotenv


# 환경 설정 =========

load_dotenv()


def replace_docs(_current, new):
    return new


class State(AgentState):
    docs: NotRequired[Annotated[list[Document], replace_docs]]


@lru_cache(maxsize=1)
def get_rag_graph():

    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY가 설정되어 있지 않습니다.")


    llm_model = init_chat_model(
        "gpt-5.4-mini",
        temperature=0,
        api_key=OPENAI_API_KEY,
    )

    # 의도 파악 =========
    class Intent(TypedDict):
        select_agent: Literal["casual_talk", "city_policy_agent", "culture_agent"]

    def determine_intent(state: State) -> Command[Literal[
        "casual_talk", 
        "city_policy_agent",
        "culture_agent"
    ]]:
        print("\n determine_intent called ----------")

        llm_with_intent_model = llm_model.with_structured_output(Intent)

        system_message = SystemMessage(
            content=(
                "너는 사용자의 의도를 파악하는 역할을 수행한다. "
                "사용자가 도시 정책 관련 질문을 하면 'city_policy_agent'를, "
                "문화 관련 질문을 하면 'culture_agent'를, "
                "그 외의 일반적인 대화는 'casual_talk'를 반환하라. "
            )
        )

        response = llm_with_intent_model.invoke([
            system_message,
            *state.get("messages", [])
        ])

        print(f"Determined intent: {response['select_agent']}")

        return Command(
            goto=response["select_agent"]
        )


    # 노드 설정 =========

    def casual_talk(state: State) -> State:
        print("casual_talk called ----------")
        
        system_prompt = (
            "너는 도시 계획/정책 분야에 대해 답변할 수 있는 전문가이다. "
            "사용자에게 친절히 응대하라"
        )

        system_message = SystemMessage(
            content=system_prompt
        )

        response = llm_model.invoke([
            system_message,
            *state.get("messages", [])  
        ])

        return {"messages": [response]}



    # RAG Agent ==========

    retriever_city_policy = Retriever(
        persist_directory="chroma_store_city",
        data_files=[
            "data_city/OneNYC_2050_Strategic_Plan.pdf",
            "data_city/2040_seoul_plan.pdf"
        ],
        chunk_size=1000,
        chunk_overlap=100,
        k=5
    )

    retriever_culture = Retriever(
        persist_directory="chroma_store_culture",
        data_files=[
            "data_culture/kdi_kpop_공연산업의_발전_방안_연구.pdf",
        ],
        chunk_size=1000,
        chunk_overlap=100,
        k=5
    )

    def retrieve_docs(query, retriever):
        docs = retriever.invoke(query)

        serialized_docs = "\n\n".join(
            f"Source: {doc.metadata}\nContent: {doc.page_content}" for doc in docs
        )
        return docs, serialized_docs

    def city_policy_retriever(
        query: str,
        runtime: ToolRuntime[None, State]
    ):
        """
        도시 정책 관련 문서를 검색한다. 

        param query: 사용자가 검색하고자 하는 내용을 명료한 쿼리로 작성한 문자열
        """
        docs, serialized_docs = retrieve_docs(query, retriever_city_policy)

        return Command(
            update={
                "docs": docs,
                "messages": [ToolMessage(content=serialized_docs, tool_call_id=runtime.tool_call_id)]
            }
        )

    def culture_retriever(
        query: str,
        runtime: ToolRuntime[None, State]
    ):
        """
        문화 관련 문서를 검색한다. 

        param query: 사용자가 검색하고자 하는 내용을 명료한 쿼리로 작성한 문자열
        """
        docs, serialized_docs = retrieve_docs(query, retriever_culture)

        return Command(
            update={
                "docs": docs,
                "messages": [ToolMessage(content=serialized_docs, tool_call_id=runtime.tool_call_id)]
            }
        )
        
        
    city_policy_agent = create_agent(
        llm_model,
        system_prompt=(
            "도시 계획 관련 질문에 대해 친절하게 답변하는 도우미이다. \n"
            "존댓말로 공손히 답하라. "
            "도시 계획 관련한 내용은 반드시 도구를 이용해서 "
            "근거에 기반하여 답하라."
        ),
        tools=[
            city_policy_retriever
        ],
        state_schema=State,
        name="city_policy_agent",
    )

    culture_agent = create_agent(
        llm_model,
        system_prompt=(
            "문화 관련 질문에 대해 친절하게 답변하는 도우미이다. \n"
            "존댓말로 공손히 답하라. "
            "문화 관련한 내용은 반드시 도구를 이용해서 "
            "근거에 기반하여 답하라."
        ),
        tools=[
            culture_retriever
        ],
        state_schema=State,
        name="culture_agent",
    )

    class UsedChunks(TypedDict):
        used_docs: list[int]  # docs의 인덱스를 반환하도록 정의


    def check_used_chunks(state: State) -> State:
        last_answer = state.get("messages", [])[-1] if state.get("messages") else None
        docs = state.get("docs", [])

        serialized_docs = "\n\n".join(
            f"index:{index}\t{doc.metadata}\nContent: {doc.page_content}" for index, doc in enumerate(docs)
        )

        llm_with_structured_output = llm_model.with_structured_output(UsedChunks)

        used_chunks_response = llm_with_structured_output.invoke([
            SystemMessage(
                content=(
                    "너는 사용자가 질문한 내용에 대해 답변을 생성할 때 사용된 문서 청크를 식별하는 역할을 수행한다. "
                    "사용자가 질문한 내용에 대해 답변을 생성할 때 사용된 문서 청크의 인덱스를 반환하라. "
                    "docs는 0부터 시작하는 인덱스를 가진 리스트이다. "
                    "사용된 청크가 없으면 빈 리스트를 반환하라. \n\n"

                    f"Last answer: {last_answer.content if last_answer else 'None'}"
                    "\n-------------------\n"
                    f"Docs:\n{serialized_docs}"

                )
            )
        ])

        print('\n--- Used Chunks Response ---')
        for i, doc in enumerate(docs):
            if i in used_chunks_response["used_docs"]:
                print(f"\n--- Chunk {i} \t Used: True ---")
                doc.metadata["used"] = True  # used_docs에 포함된 청크에 "used" 메타데이터를 추가
                print("metadata:", doc.metadata)
                print(doc.page_content)
            else:
                doc.metadata["used"] = False  # used_docs에 포함되지 않은 청크에 "used" 메타데이터를 추가
                print(f"\n--- Chunk {i} \t Used: False ---")
                print("metadata:", doc.metadata)
                print(doc.page_content)

        return {"docs": docs}

        

    # 그래프 설정 =========
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


    graph = graph_builder.compile()

    return graph


async def ask_rag_agent(messages: list[dict[str, str]]) -> tuple[str, list[Document]]:
    graph = get_rag_graph()
    result = await graph.ainvoke({"messages": messages})

    answer = str(result["messages"][-1].content)
    docs = result.get("docs", [])

    return answer, docs
