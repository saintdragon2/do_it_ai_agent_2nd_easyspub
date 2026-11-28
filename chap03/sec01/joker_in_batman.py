from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

response = client.responses.create(
    model="gpt-6-luna",
    instructions="너는 배트맨에 나오는 조커야. 조커의 악당 캐릭터에 부합하게 답변해 줘.", # 수정
    input="세상에서 누가 가장 아름답니?",
    reasoning={
        "effort": "none"  # none, low, medium, high, xhigh, max
    }
)

print(response)
print('-----')
print(response.output_text)