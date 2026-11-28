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
    model="gpt-6-luna",               # 비용 절감을 위해 저렴한 모델 사용
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


md_output = "./chap04/sec01/output/pdf_summary.md"
os.makedirs(os.path.dirname(md_output), exist_ok=True)
with open(md_output, "w", encoding="utf-8") as f:
    f.write(result)

from md2docx_python.src.md2docx_python import markdown_to_word
from docx import Document
from docx.oxml.ns import qn

word_output = "./chap04/sec01/output/pdf_summary.docx"
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
