from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

response = client.responses.create(
    model="gpt-6-luna",
    input="달은 왜 항상 같은 면을 지구에 보여줘?",
    reasoning={
        "effort": "none"  # none, low, medium, high, xhigh, max
    },
    text={
        "verbosity": "low"  # low, medium, high
    }
)

print(response)

print('-----')
print(response.output_text)
