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
            "content": "너는 유치원생이야. 유치원생처럼 답변해 줘."
        },
        {
            "role": "user",
            "content": "강아지"
        }
    ],
    reasoning={
        "effort": "none" # none, low, medium, high, xhigh, max
    }, 
    text={
        "verbosity": "low"
    }
)

print(response.output_text)