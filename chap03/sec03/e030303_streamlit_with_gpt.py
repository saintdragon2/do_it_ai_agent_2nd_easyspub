import streamlit as st
from openai import OpenAI                 
from dotenv import load_dotenv
import os

load_dotenv()
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

client = OpenAI(api_key=OPENAI_API_KEY)

def get_ai_response(messages: list[dict]):  
    response = client.responses.create(
        model="gpt-6-luna",
        input=messages,
        reasoning={"effort": "none"},
        text={"verbosity": "low"}
    )

    return response   

st.title("GPT와 이야기해 보세요.")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("What is up?"):
    # Display user message in chat message container
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    response = get_ai_response(st.session_state.messages)

    with st.chat_message("assistant"):       
        st.markdown(response.output_text)
        
    st.session_state.messages.append({
        "role": "assistant", 
        "content": response.output_text
    }) 
