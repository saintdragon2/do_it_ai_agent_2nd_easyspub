from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

client = OpenAI(api_key=OPENAI_API_KEY)

while True:
    user_input = input("사용자: ")

    if user_input == 'exit':
        break
    
    response = client.responses.create(
        model="gpt-6-luna",
        input=[
            {"role": "developer", "content": "너는 사용자를 도와주는 상담사야."},
            {"role": "user", "content": user_input},
        ],
        reasoning={"effort": "none"},
        text={"verbosity": "low"}
    )

    print("AI: ", response.output_text)
