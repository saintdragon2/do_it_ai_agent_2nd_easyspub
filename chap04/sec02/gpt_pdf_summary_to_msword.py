from openai import OpenAI
from dotenv import load_dotenv
from glob import glob          
from md2docx_python.src.md2docx_python import markdown_to_word 
from docx import Document
from docx.oxml.ns import qn
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

def save_to_word(md_output: str, word_output: str):
    markdown_to_word(md_output, word_output)

    # 한글 글꼴 설정
    doc = Document(word_output)
    font_name = "맑은 고딕"

    for style in doc.styles:
        if style.type == 1:  # 문단 스타일
            style.font.name = font_name
            style._element.get_or_add_rPr().rFonts.set(
                qn("w:eastAsia"), font_name
            )

    doc.save(word_output)


if __name__ == "__main__":
    for g in glob("chap04/sec02/samples/*.pdf"):     
        print(g)

        filename, ext = os.path.splitext(os.path.basename(g)) 
        print(f"\n----------- {filename} -----------------")

        md_output = f"chap04/sec02/output/{filename}.md"
        word_output = f"chap04/sec02/output/{filename}.docx"

        result = easy_judgement(
            g,
            md_output
        )

        print(result)

        save_to_word(md_output, word_output) 

