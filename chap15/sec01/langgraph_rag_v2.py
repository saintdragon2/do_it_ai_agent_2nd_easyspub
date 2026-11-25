from langchain.messages import SystemMessage, HumanMessage, AIMessageChunk
from langchain_core.messages import BaseMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict
from typing import Annotated
from langchain.chat_models import init_chat_model
from langgraph.checkpoint.memory import InMemorySaver

import os
from dotenv import load_dotenv


# 환경 설정 =========

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY가 설정되어 있지 않습니다.")


llm_model = init_chat_model(
    "gpt-5.5",
    temperature=0,
    api_key=OPENAI_API_KEY,
)

# 상태 정의 =========
class State(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


# 의도 파악 =========
from typing import Literal, TypedDict
from langgraph.types import Command


class Intent(TypedDict):
    select_agent: Literal["casual_talk", "city_policy_agent"]

def determine_intent(state: State) -> Command[Literal["casual_talk", "city_policy_agent"]]:
    print("\n determine_intent called ----------")

    llm_with_intent_model = llm_model.with_structured_output(Intent)

    system_message = SystemMessage(
        content=(
            "너는 사용자의 의도를 파악하는 역할을 수행한다. "
            "사용자가 도시 정책 관련 질문을 하면 'city_policy_agent'를, "
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
from retriever import Retriever
from langchain.agents import create_agent

retriever_city_policy = Retriever(
    persist_directory="chap09/chroma_store",
    data_files=[
        "chap09/data/OneNYC_2050_Strategic_Plan.pdf",
        "chap09/data/2040_seoul_plan.pdf"
    ],
    chunk_size=1000,
    chunk_overlap=100,
    k=5
)


def retrieve_docs(query, retriever):
    docs = retriever.invoke(query)
    
    return docs


def city_policy_retriever(query):
    """
    도시 정책 관련 문서를 검색한다. 

    param query: 사용자가 검색하고자 하는 내용을 명료한 쿼리로 작성한 문자열
    """
    return retrieve_docs(query, retriever_city_policy)


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
    name="city_policy_agent",
)
    

# 그래프 설정 =========
graph_builder = StateGraph(State)

graph_builder.add_node("determine_intent", determine_intent)
graph_builder.add_node("casual_talk", casual_talk)
graph_builder.add_node("city_policy_agent", city_policy_agent)

graph_builder.add_edge(START, "determine_intent")
graph_builder.add_edge("casual_talk", END)
graph_builder.add_edge("city_policy_agent", END)

graph = graph_builder.compile(
    checkpointer=InMemorySaver()
)

absolute_path = os.path.abspath(__file__)
graph.get_graph().draw_mermaid_png(output_file_path=absolute_path.replace('.py', '.png'))

thread_config = {
    "configurable": {
        "thread_id": "some_unique_thread_id"
    }
}

# CLI 설정 =========
while True:
    user_input = input("User: ")
    
    if user_input.lower() in ["exit", "quit"]:
        print("프로그램을 종료합니다.")
        break

    input_state = {
        "messages": [HumanMessage(content=user_input)]
    }

    for event in graph.stream(
        input_state,
        config=thread_config,
        stream_mode=["messages"],
        subgraphs=True,
        version="v2"
    ):
        if event["type"] == "messages":
            msg, metadata = event["data"]
            
            node = metadata.get("langgraph_node")
            ns = event["ns"]

            if node == "casual_talk":
                if msg.content:
                    print(msg.content, end="", flush=True)
            
            elif (
                ns
                and ns[0].startswith("city_policy_agent:")
            ):
                if (
                    isinstance(msg, AIMessageChunk)
                    and msg.content
                    and not msg.tool_call_chunks
                ):
                    print(
                        msg.content,
                        end="",
                        flush=True
                    )
       

    print("\n--------------------------------\n")