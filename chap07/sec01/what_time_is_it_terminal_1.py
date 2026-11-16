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
    
    messages += response.output

    for item in response.output:
        if item.type == "function_call":
            if item.name == "get_current_time":
                result = get_current_time()

                messages.append({
                    "type": "function_call_output",
                    "call_id": item.call_id,
                    "output": result
                })

            response = client.responses.create(
                model="gpt-5.5",
                instructions=f"{item.name} 결과를 이용해 사용자에게 친절하게 답변하라.",
                tools=tools,
                input=messages
            )
    
    messages.append({"role": "assistant", "content": response.output_text})

    return response, messages


messages = [                                    
    {"role": "developer", "content": "너는 사용자를 도와주는 상담사야."},
]                                               

while True:
    user_input = input("사용자: ")

    if user_input == 'exit':
        break
    
    messages.append({"role": "user", "content": user_input})

    response, messages = get_ai_response(messages, tools=tools)
    print("AI: ", response.output_text)
