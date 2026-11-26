from rag_agent import rag_agent
import streamlit as st
from langchain.messages import (
    HumanMessage,
    AIMessage,
    AIMessageChunk,
    ToolMessage,
)

st.title("RAG Agent with Streamlit")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    if isinstance(message, HumanMessage):
        with st.chat_message("user"):
            st.markdown(message.content)

    elif isinstance(message, AIMessage):
        with st.chat_message("assistant"):
            st.markdown(message.content)

    elif isinstance(message, ToolMessage):
        with st.chat_message("tool"):
            tool_name = getattr(message, "name", "tool")
            st.markdown(f"도구 실행 결과: `{tool_name}`\t")
            st.code(str(message.content))
    else:
        content = getattr(message, "content", "")
        if content:
            with st.chat_message("assistant"):
                st.markdown(content)

user_input = st.chat_input("메시지를 입력하세요")

if user_input:
    user_message = HumanMessage(content=user_input)
    st.session_state.messages.append(user_message)

    with st.chat_message("user"):
        st.markdown(user_input)

    assistant_placeholder = st.chat_message("assistant")
    response_box = assistant_placeholder.empty()

    streamed_text = ""

    sources = []
    tool_calls_by_id = {}

    try:
        for chunk in rag_agent.stream(
            {"messages": st.session_state.messages},
            stream_mode=["messages", "updates", "values"],
            version="v2",
        ):
            if chunk["type"] == "messages":
                token, metadata = chunk["data"]

                if isinstance(token, AIMessageChunk):
                    if token.text:
                        streamed_text += token.text
                        response_box.markdown(streamed_text)
            
            elif chunk["type"] == "updates":
                if "tools" in chunk["data"]:
                    tools = chunk["data"]["tools"]["messages"]

                    for t in tools:
                        tool_name = getattr(t, "name", "tool")
                        tool_call_args = tool_calls_by_id[t.tool_call_id]["args"]
                        st.expander(f"도구: {tool_name}\t{tool_call_args}").code(str(t.content))
                        sources.append(t.content)

                    
            elif chunk["type"] == "values":
                print(                                         
                    "\n------ values ------ message length", 
                    len(chunk["data"]["messages"]),
                    type(chunk["data"]["messages"][-1])
                )                                              
                messages = chunk["data"]["messages"]

                for message in messages:
                    if isinstance(message, AIMessage):
                        if message.tool_calls:
                            for tool_call in message.tool_calls:
                                print(f"{tool_call = }")
                                tool_calls_by_id[tool_call.get('id')] = tool_call

                    if isinstance(message, ToolMessage):
                        tool_name = getattr(message, "name", "tool")
                        tool_call_id = getattr(message, "tool_call_id", "unknown")
                        print(f"ToolMessage: {tool_name}, tool_call_id: {tool_call_id}, content: {message.content}") 


        st.session_state.messages = messages

    except Exception as e:
        response_box.error(f"오류가 발생했습니다: {e}")

    for message in st.session_state.messages:
        message.pretty_print()
