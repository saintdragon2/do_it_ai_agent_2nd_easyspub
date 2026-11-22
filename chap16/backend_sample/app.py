import logging
import os
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from chatbot import (
    ask_chatbot,
    get_chat_graph,
    stream_chatbot,
)


logger = logging.getLogger(__name__)
app = FastAPI(
    title="도시 정책·문화 RAG 챗봇 API",
    version="1.0.0",
)

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


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "api_key_configured": bool(os.getenv("OPENAI_API_KEY")),
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    if request.messages[-1].role != "user":
        raise HTTPException(
            status_code=400,
            detail="마지막 메시지는 user 역할이어야 합니다.",
        )

    try:
        messages = [message.model_dump() for message in request.messages]
        answer = await ask_chatbot(messages)
    except Exception as error:
        logger.exception("챗봇 답변 생성에 실패했습니다.")
        raise HTTPException(
            status_code=500,
            detail="챗봇의 답변을 생성하지 못했습니다.",
        ) from error

    return ChatResponse(answer=answer)


@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    if request.messages[-1].role != "user":
        raise HTTPException(
            status_code=400,
            detail="마지막 메시지는 user 역할이어야 합니다.",
        )

    try:
        get_chat_graph()
    except Exception as error:
        logger.exception("챗봇 준비에 실패했습니다.")
        raise HTTPException(
            status_code=500,
            detail="챗봇을 준비하지 못했습니다.",
        ) from error

    async def generate():
        try:
            messages = [message.model_dump() for message in request.messages]
            async for token in stream_chatbot(messages):
                yield token
        except Exception:
            logger.exception("챗봇 스트리밍 중 오류가 발생했습니다.")
            yield "\n\n답변을 생성하는 중 오류가 발생했습니다."

    return StreamingResponse(
        generate(),
        media_type="text/plain; charset=utf-8",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
