from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Literal
from chat_graph import ask_chatbot
from multi_rag_graph import ask_rag_agent
from langchain_core.documents import Document


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
    docs: list[Document] = Field(default_factory=list)



def get_messages(request: ChatRequest) -> list[dict[str, str]]:
    if request.messages[-1].role != "user":
        raise HTTPException(
            status_code=400,
            detail="마지막 메시지는 user 역할이어야 합니다.",
        )
    return [message.model_dump() for message in request.messages]

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    messages = get_messages(request)
    answer = await ask_chatbot(messages)
    return ChatResponse(answer=answer)


@app.post("/rag", response_model=ChatResponse)
async def rag(request: ChatRequest):
    messages = get_messages(request)
    answer, docs = await ask_rag_agent(messages)
    return ChatResponse(answer=answer, docs=docs)