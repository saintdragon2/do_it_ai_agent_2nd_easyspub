from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

response = client.responses.create(
    model="gpt-6-luna",
    instructions="너는 백설공주 이야기 속의 마법 거울이야. 그 이야기의 캐릭터에 부합하게 답변해 줘.", # 추가
    input="세상에서 누가 가장 아름답니?", # 수정
    reasoning={
        "effort": "none"  # none, low, medium, high, xhigh, max
    }
)

print(response)
print('-----')
print(response.output_text)