from gpt_functions import get_current_time, tools
from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

client = OpenAI(api_key=OPENAI_API_KEY)

def get_ai_response(messages: list[dict], tools=None):
    response = client.responses.create(
        model="gpt-5.4",
        input=messages,
        reasoning={"effort": "none"},
        text={"verbosity": "low"},
        tools=tools
    )

    return response

messages = [                                    
    {"role": "developer", "content": "너는 사용자를 도와주는 상담사야."},
]                                               


while True:
    user_input = input("사용자: ")              

    if user_input == 'exit':
        break
    
    messages.append({"role": "user", "content": user_input})    

    response = get_ai_response(messages, tools=tools)                        
    
    messages.append({"role": "assistant", "content": response.output_text})
    print("AI: ", response.output_text)                         


