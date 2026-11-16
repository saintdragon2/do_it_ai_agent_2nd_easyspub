from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

client = OpenAI(api_key=OPENAI_API_KEY)

with open("chap04/sec02/easy_judgement_prompt.md", "r", encoding="utf-8") as f:
    easy_judgement_prompt = f.read()
        

def easy_judgement(pdf_path: str, md_output: str):
    file = client.files.create(
        file=open(pdf_path, "rb"),
        purpose="user_data"
    )

    response = client.responses.create(
        model="gpt-5.4-nano",
        input=[
            {
                "role": "developer", 
                "content": easy_judgement_prompt,
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_file",
                        "file_id": file.id,
                    }
                ]
            }
        ]
    )

    result = response.output_text

    client.files.delete(file.id)
    
    with open(md_output, "w", encoding="utf-8") as f:
        f.write(result)

    return result

if __name__ == "__main__":
    result = easy_judgement(
        "chap04/sec02/samples/2023가단5428832.pdf",
        "chap04/sec02/output/2023가단5428832.md"
    )

    print(result)
