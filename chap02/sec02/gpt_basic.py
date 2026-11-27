from openai import OpenAI

OPENAI_API_KEY = "your_openai_api_key_here"

client = OpenAI(api_key=OPENAI_API_KEY)

response = client.responses.create(
    model="gpt-6-luna",
    input="2026 월드컵 우승팀은 어디야?",
    reasoning={
        "effort": "none"  # none, low, medium, high, xhigh, max
    }
)

print(response)

print('-----')
print(response.output_text)
