from fastapi import FastAPI
from pydantic import BaseModel, Field


app = FastAPI(title="요청과 응답 연습")


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)


class ChatResponse(BaseModel):
    answer: str


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    return ChatResponse(
        answer=f"서버가 받은 메시지: {request.message}"
    )
