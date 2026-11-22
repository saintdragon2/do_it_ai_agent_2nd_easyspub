from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Literal
from chat_graph import ask_chatbot


app = FastAPI(title="요청과 응답 연습")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=2000)


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(min_length=1, max_length=50)


class ChatResponse(BaseModel):
    answer: str


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    messages = [message.model_dump() for message in request.messages]
    answer = await ask_chatbot(messages)
    return ChatResponse(answer=answer)