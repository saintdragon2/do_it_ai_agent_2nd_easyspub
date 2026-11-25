from langchain.messages import SystemMessage, HumanMessage
from langchain_core.messages import BaseMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict
from typing import Annotated
from langchain.chat_models import init_chat_model
from langgraph.checkpoint.memory import InMemorySaver

import os
from dotenv import load_dotenv

# ============================================================
# 환경 설정
# ============================================================

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY가 설정되어 있지 않습니다.")


llm_model = init_chat_model(
    "gpt-5.5",
    temperature=0,
    api_key=OPENAI_API_KEY,
)

# ===========================================================
# 상태 정의
# ============================================================

class State(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


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

# ============================================================
# 그래프 설정
# ============================================================

graph_builder = StateGraph(State)

graph_builder.add_node("casual_talk", casual_talk)

graph_builder.add_edge(START, "casual_talk")
graph_builder.add_edge("casual_talk", END)

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

# ============================================================
# CLI 설정
# ============================================================
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
        version="v2"
    ):
        if event["type"] == "messages":
            msg, metadata = event["data"]
            print(msg.content, end="", flush=True)

    print("\n--------------------------------\n")