from gpt_functions import get_current_time, tools, get_yf_stock_info, get_yf_stock_history, get_yf_stock_recommendations
from openai import OpenAI
from dotenv import load_dotenv
import os
import json
import streamlit as st

load_dotenv()
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

client = OpenAI(api_key=OPENAI_API_KEY)

def stream_ai_response(messages: list[dict], tools=None, instructions=None, placeholder=None, model="gpt-5.4"):
    stream = client.responses.create(
        model=model,
        instructions=instructions,
        input=messages,
        reasoning={"effort": "none"},
        text={"verbosity": "low"},
        tools=tools,
        stream=True
    )

    response = None
    output_text = ""

    for event in stream:
        if event.type == "response.output_text.delta":
            output_text += event.delta
            if placeholder is None:
                placeholder = st.chat_message("assistant").empty()
            placeholder.markdown(output_text + "▌")
        elif event.type == "response.completed":
            response = event.response

    if placeholder is not None:
        placeholder.markdown(output_text)

    return response, output_text


def get_ai_response(messages: list[dict], tools=None, placeholder=None):
    response, output_text = stream_ai_response(
        messages=messages,
        tools=tools,
        placeholder=placeholder
    )

    print(response.output)
    
    messages += response.output

    tool_use = False

    for item in response.output:
        if item.type == "function_call":
            if item.name == "get_current_time":
                arguments = json.loads(item.arguments)

                result = get_current_time(timezone=arguments["timezone"])

                messages.append({
                    "type": "function_call_output",
                    "call_id": item.call_id,
                    "output": result
                })
                st.chat_message("function").write(f"{item.name}: {result}") # Streamlit에서 함수 호출 결과 출력
            elif item.name == "get_yf_stock_info":
                arguments = json.loads(item.arguments)

                result = get_yf_stock_info(ticker=arguments["ticker"])

                messages.append({
                    "type": "function_call_output",
                    "call_id": item.call_id,
                    "output": str(result)
                })
                st.chat_message("function").write(f"{item.name}: {result}") # Streamlit에서 함수 호출 결과 출력
            elif item.name == "get_yf_stock_history": # get_yf_stock_history 함수 호출 처리
                arguments = json.loads(item.arguments)

                result = get_yf_stock_history(
                    ticker=arguments["ticker"], 
                    period=arguments.get("period", "1mo")
                )

                messages.append({
                    "type": "function_call_output",
                    "call_id": item.call_id,
                    "output": str(result)
                })
                st.chat_message("function").write(result) # Streamlit에서 함수 호출 결과 출력
            
            elif item.name == "get_yf_stock_recommendations": # get_yf_stock_recommendations 함수 호출 처리
                arguments = json.loads(item.arguments)

                result = get_yf_stock_recommendations(
                    ticker=arguments["ticker"]
                )

                messages.append({
                    "type": "function_call_output",
                    "call_id": item.call_id,
                    "output": str(result)
                })
                st.chat_message("function").write(result) # Streamlit에서 함수 호출 결과 출력
            
            tool_use = True
    
    if tool_use:
        response, output_text = stream_ai_response(
            instructions=f"{item.name} 결과를 이용해 사용자에게 친절하게 답변하라.",
            tools=tools,
            messages=messages,
            placeholder=placeholder,
            model="gpt-5.6-luna"
        )

    return output_text, messages

st.title("Chatbot")

if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "developer", "content": "너는 사용자를 도와주는 상담사야."},
    ]


for msg in st.session_state.messages:
    if type(msg) == dict:
        if "role" in msg and "content" in msg:
            st.chat_message(msg["role"]).write(msg["content"])
        elif "type" in msg and msg["type"] == "function_call_output":
            st.chat_message("function").write(msg['output'])


if user_input := st.chat_input("사용자: "):
    st.session_state.messages.append({"role": "user", "content": user_input})
    st.chat_message("user").write(user_input)

    assistant_text, st.session_state.messages = get_ai_response(
        st.session_state.messages,
        tools=tools
    )

    st.session_state.messages.append({"role": "assistant", "content": assistant_text})
    
    
