# 최종 백엔드 실행하기

저장소 루트에서 `app.py`가 있는 폴더로 이동한 뒤 다음 명령을 실행합니다.

```bash
cd chap16/backend_sample
uv run fastapi dev app.py
```

`app.py`, `chatbot.py`, `retriever.py`가 같은 폴더에 있으므로 각 파일은 `from chatbot import ...`, `from retriever import ...`처럼 서로를 가져옵니다. FastAPI CLI는 `app.py`의 `app` 객체를 자동으로 찾아 Uvicorn 개발 서버로 실행합니다.

- 상태 확인: <http://localhost:8000/health>
- API 문서: <http://localhost:8000/docs>
- 일반 응답: `POST /chat`
- 스트리밍 응답: `POST /chat/stream`

이 예제는 9장과 15장에서 만든 PDF 및 Chroma DB를 사용합니다. 먼저 해당 장의 RAG 실습을 완료하고 `.env`에 `OPENAI_API_KEY`를 설정해야 합니다.

두 POST 엔드포인트는 `{"messages": [{"role": "user", "content": "안녕"}]}` 형식으로 전체 대화 히스토리를 받습니다. 백엔드는 요청 사이의 대화 내용을 저장하지 않습니다.
