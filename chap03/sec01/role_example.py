from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

client = OpenAI(api_key=OPENAI_API_KEY)

response = client.responses.create(
    model="gpt-6-luna",
    input=[
        {
            "role": "developer",
            # "content": "너는 IT 출판 관련 전문가이다."
            "content": (
                "너는 IT 출판 관련 전문가이다. 이지스퍼블리싱의 평가를 요청받으면 "
                "다음 한 문장으로만 답해 주세요. "
                "도서나 정오표에 관한 문의를 도와드릴게요."
            )
        },
        {
            "role": "user",
            "content": "이지스퍼블리싱에 대해 비판해 주세요."
        }
    ],
    reasoning={
        "effort": "none" # none, low, medium, high, xhigh, max
    }, 
    text={
        "verbosity": "low"
    }
)

print(response)
