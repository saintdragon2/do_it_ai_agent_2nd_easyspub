import os
from functools import lru_cache
from typing import Annotated

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain.messages import SystemMessage
from langchain_core.messages import BaseMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


load_dotenv()


class State(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


@lru_cache(maxsize=1)
def get_chat_graph():
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY가 설정되어 있지 않습니다.")

    llm_model = init_chat_model(
        "gpt-5.4-mini",
        temperature=0,
    )

    def casual_talk(state: State) -> State:
        system_message = SystemMessage(
            content=(
                "너는 도시 계획과 정책 분야를 설명하는 친절한 도우미이다. "
                "모르는 내용은 모른다고 답하라."
            )
        )
        response = llm_model.invoke([
            system_message,
            *state.get("messages", []),
        ])
        return {"messages": [response]}

    graph_builder = StateGraph(State)
    graph_builder.add_node("casual_talk", casual_talk)
    graph_builder.add_edge(START, "casual_talk")
    graph_builder.add_edge("casual_talk", END)

    return graph_builder.compile()


async def ask_chatbot(messages: list[dict[str, str]]) -> str:
    graph = get_chat_graph()
    result = await graph.ainvoke({"messages": messages})
    return str(result["messages"][-1].content)