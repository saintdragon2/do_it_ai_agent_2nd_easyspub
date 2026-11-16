from gpt_functions import get_current_time, tools
from openai import OpenAI
from dotenv import load_dotenv
import os
import json # GPT가 JSON 형태의 문자열을 반환할 때 읽기 위한 라이브러리 임포트

load_dotenv()
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

client = OpenAI(api_key=OPENAI_API_KEY)

def get_ai_response(messages: list[dict], tools=None):
    response = client.responses.create(
        model="gpt-5.6-luna",
        input=messages,
        reasoning={"effort": "none"},
        text={"verbosity": "low"},
        tools=tools
    )

    print(response.output)
    
    messages += response.output

    tool_use = False  # (1) 도구 사용 여부를 추적하는 변수 추가

    for item in response.output:
        if item.type == "function_call":
            if item.name == "get_current_time":
                arguments = json.loads(item.arguments)  # GPT가 전달한 arguments를 JSON으로 파싱

                result = get_current_time(timezone=arguments["timezone"])

                messages.append({
                    "type": "function_call_output",
                    "call_id": item.call_id,
                    "output": result
                })
                tool_use = True  # (2) 도구 사용 여부를 True로 설정
    
    if tool_use:  # (3) 도구를 사용한 경우에만 추가 응답 생성
        response = client.responses.create(
            model="gpt-5.6-luna",
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
