from glob import glob
from openai import OpenAI
from dotenv import load_dotenv
import os
import base64

load_dotenv()
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
client = OpenAI(api_key=OPENAI_API_KEY)


# 이미지를 인코딩하는 함수
def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def image_quiz(image_path):
    base64_image = encode_image(image_path)
    
    quiz_prompt = """
        제공한 이미지를 바탕으로, 다음과 같은 양식으로 퀴즈를 만들어 주세요.
        정답은 (1)~(4) 중 하나만 해당하도록 출제하세요.
        아래는 예시입니다.
        ----- 예시 -----
        Q: 다음 이미지에 대한 설명 중 옳지 않은 것은 무엇인가요?
        - (1) 베이커리에서 사람들이 빵을 사는 모습이 담겨 있습니다.
        - (2) 맨 앞에 서 있는 사람은 빨간색 셔츠를 입었습니다.
        - (3) 기차를 타기 위해 줄을 서 있는 사람들이 있습니다.
        - (4) 점원은 노란색 티셔츠를 입었습니다.
        
        정답: (4) 점원은 노란색 티셔츠가 아닌 파란색 티셔츠를 입었습니다.
        ======
    """

    messages = [{
        "role": "user",
        "content": [
            {
                "type": "input_text", 
                "text": quiz_prompt
            },
            {
                "type": "input_image",
                "image_url": f"data:image/jpeg;base64,{base64_image}"
            },
        ],
        
    }]

    response = client.responses.create(
        model="gpt-5.6-luna",
        input=messages
    )

    return response.output_text

image_path = "chap06/images/busan_dive.jpg"
q = image_quiz(image_path)
print(q)

txt = ''        # 1
no = 1          # 1
for g in glob('./chap06/images/*.jpg'): # 2
    try:
        q = image_quiz(g)
    except Exception as e:
        print(e)
        continue
    
    divider = f'## 문제 {no}\n\n'
    print(divider)                          # 2 끝
    
    txt += divider                          # 3 시작
    filename = os.path.basename(g)
    txt += f'![image]({filename})\n\n'
    
    # 문제 추가
    print(q)
    txt += q + '\n\n---------------------\n\n'  # 3 끝
    
    with open('./chap06/images/image_quiz.md', 'w', encoding='utf-8') as f:    # 4
        f.write(txt)
    
    no += 1 # 문제 번호 증가