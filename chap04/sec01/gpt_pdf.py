from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

client = OpenAI(api_key=OPENAI_API_KEY)             

file = client.files.create(                         
    file=open("chap04/sec01/samples/AI에이전트_북토크_2025_1015_pdf.pdf", "rb"),
    purpose="user_data"
)

response = client.responses.create(
    model="gpt-5.4-nano",               # 비용 절감을 위해 저렴한 모델 사용
    input=[
        {
            "role": "user",
            "content": [
                {                           
                    "type": "input_file",
                    "file_id": file.id,
                },
                {
                    "type": "input_text",
                    "text": "이 자료의 저자는 누구인지, 그리고 어떤 내용을 담은 자료인지 설명하라.",
                },
            ]
        }
    ]
)

result = response.output_text

print(result)

print('-------------')              
r = client.files.delete(file.id)
print(r)
