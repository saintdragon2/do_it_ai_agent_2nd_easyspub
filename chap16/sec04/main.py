import json
import logging
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from langchain_core.documents import Document
from pydantic import BaseModel, Field

from chat_graph import ask_chatbot, get_chat_graph, stream_chatbot
from rag_graph import ask_rag_agent, get_rag_graph, stream_rag_agent


logger = logging.getLogger(__name__)
app = FastAPI(title="도시 정책·문화 챗봇 API")

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


@app.post(
    "/chat/stream",
    response_class=StreamingResponse,
    responses={
        200: {
            "description": "일반 대화 답변 텍스트 스트림",
            "content": {
                "text/plain": {
                    "schema": {"type": "string"},
                }
            },
        }
    },
)
async def chat_stream(request: ChatRequest):
    messages = get_messages(request)

    try:
        graph = get_chat_graph()
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail="챗봇을 준비하지 못했습니다.",
        ) from error

    async def generate():
        try:
            async for text in stream_chatbot(graph, messages):
                yield text
        except Exception:
            logger.exception("일반 대화 스트리밍 중 오류가 발생했습니다.")
            yield "\n\n답변을 생성하는 중 오류가 발생했습니다."

    return StreamingResponse(
        generate(),
        media_type="text/plain; charset=utf-8",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/rag", response_model=ChatResponse)
async def rag(request: ChatRequest):
    messages = get_messages(request)
    answer, docs = await ask_rag_agent(messages)
    return ChatResponse(answer=answer, docs=docs)


@app.post(
    "/rag/stream",
    response_class=StreamingResponse,
    responses={
        200: {
            "description": "RAG 답변과 문서의 NDJSON 스트림",
            "content": {
                "application/x-ndjson": {
                    "schema": {"type": "string"},
                }
            },
        }
    },
)
async def rag_stream(request: ChatRequest):
    messages = get_messages(request)

    try:
        graph = get_rag_graph()
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail="RAG 에이전트를 준비하지 못했습니다.",
        ) from error

    async def generate():
        try:
            async for event in stream_rag_agent(graph, messages):
                yield json.dumps(event, ensure_ascii=False) + "\n"

            yield json.dumps({"type": "done"}) + "\n"
        except Exception:
            logger.exception("RAG 답변 스트리밍 중 오류가 발생했습니다.")
            error_event = {
                "type": "error",
                "message": "답변을 생성하는 중 오류가 발생했습니다.",
            }
            yield json.dumps(error_event, ensure_ascii=False) + "\n"

    return StreamingResponse(
        generate(),
        media_type="application/x-ndjson",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
