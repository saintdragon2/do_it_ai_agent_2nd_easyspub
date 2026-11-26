import os
from datetime import datetime

import pytz
import yfinance as yf
import streamlit as st
from dotenv import load_dotenv

from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma

from langchain.agents import create_agent
from langchain.messages import (
    HumanMessage,
    AIMessage,
    AIMessageChunk,
    ToolMessage,
)

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# -----------------------------
# Data
# -----------------------------

persist_directory = "chap09/chroma_store"

embedding = OpenAIEmbeddings(model='text-embedding-3-large', api_key=OPENAI_API_KEY)

if not os.path.exists(persist_directory):
    print("Creating new Chroma store")

    # 텍스트 데이터를 1000자 단위로 나눔. overlap은 100자로 설정
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    loader = PyPDFLoader("chap09/data/OneNYC_2050_Strategic_Plan.pdf")
    data_nyc = loader.load()
    nyc_splits = text_splitter.split_documents(data_nyc)
    
    loader_seoul = PyPDFLoader("chap09/data/2040_seoul_plan.pdf")
    data_seoul = loader_seoul.load()
    seoul_splits = text_splitter.split_documents(data_seoul)

    all_splits = nyc_splits + seoul_splits

    vectorstore = Chroma.from_documents(
        documents=all_splits,
        embedding=embedding,
        persist_directory=persist_directory
    )
else:
    print("Loading existing Chroma store")
    vectorstore = Chroma(
        persist_directory=persist_directory,
        embedding_function=embedding
    )

# -----------------------------
# Tools
# -----------------------------



def retrieve_docs(query):
    """
    vector store에서 query에 대한 관련 문서를 검색하고, 검색된 문서들을 직렬화하여 반환하는 함수
    """
    retriever = vectorstore.as_retriever(k=3)
    docs = retriever.invoke(query)
    
    serialized_docs = "\n\n".join(
        f"Source: {doc.metadata}\nContent: {doc.page_content}" for doc in docs
    )

    return serialized_docs





# -----------------------------
# Agent
# -----------------------------


agent = create_agent(
    model="openai:gpt-5.4-mini",
    system_prompt="도시 계획 관련 질문에 대해 친절하게 답변하는 도우미 역할을 수행합니다. 존댓말로 공손히 답하라. 도시 계획 관련한 내용은 반드시 도구를 이용해서 근거에 기반하여 답하라.",
    tools=[
        retrieve_docs
    ],
)



# -----------------------------
# UI
# -----------------------------
st.title("AI Agent with Streamlit")

if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.tool_calls_by_id = {}

# 저장된 LangChain 메시지를 Streamlit 채팅 UI에 출력
for message in st.session_state.messages:
    if isinstance(message, HumanMessage):
        with st.chat_message("user"):
            st.markdown(message.content)

    elif isinstance(message, AIMessage):
        # tool call만 있는 AIMessage는 일반 답변처럼 보여주지 않음
        if message.content:
            with st.chat_message("assistant"):
                st.markdown(message.content)

    elif isinstance(message, ToolMessage):
        # 필요 없으면 이 블록 전체를 주석 처리해도 됨
        with st.chat_message("tool"):
            tool_name = getattr(message, "name", "tool")
            tool_args = st.session_state.tool_calls_by_id.get(getattr(message, "tool_call_id", ""), {}).get("args", {})
            st.markdown(f"도구 실행 결과: `{tool_name}`\t{tool_args}")
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
        for chunk in agent.stream(
            {"messages": st.session_state.messages},
            stream_mode=["messages", "updates", "values"],
            version="v2",
        ):
            # LangChain v2 streaming format:
            # chunk["type"] == "messages" -> token stream
            # chunk["type"] == "updates"  -> completed model/tool messages
            if chunk["type"] == "messages":
                token, metadata = chunk["data"]

                if isinstance(token, AIMessageChunk):
                    # 일반 텍스트 토큰만 화면에 표시
                    if token.text:
                        streamed_text += token.text
                        response_box.markdown(streamed_text)

            elif chunk["type"] == "updates":
                if "tools" in chunk["data"]:
                    tools = chunk["data"]["tools"]["messages"]

                    for t in tools:
                        st.expander(f"도구: {getattr(t, 'name', 'tool')}\t{tool_calls_by_id[t.tool_call_id]["args"]}").code(str(t.content))   
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
        st.session_state.tool_calls_by_id = tool_calls_by_id

    except Exception as e:
        response_box.error(f"오류가 발생했습니다: {e}")

    for message in st.session_state.messages:
        message.pretty_print()