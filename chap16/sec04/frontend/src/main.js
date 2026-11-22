import DOMPurify from "dompurify";
import { marked } from "marked";

import "./style.css";


marked.use({ breaks: true, gfm: true });


const API_URLS = {
  chat: import.meta.env.VITE_CHAT_API_URL ?? "http://localhost:8000/chat",
  chat_stream: import.meta.env.VITE_CHAT_STREAM_API_URL
    ?? "http://localhost:8000/chat/stream",
  rag: import.meta.env.VITE_RAG_API_URL ?? "http://localhost:8000/rag",
  rag_stream: import.meta.env.VITE_RAG_STREAM_API_URL
    ?? "http://localhost:8000/rag/stream",
};
const form = document.querySelector("#chat-form");
const input = document.querySelector("#message-input");
const messages = document.querySelector("#messages");
const sendButton = form.querySelector("button");
const modeInputs = [...document.querySelectorAll('input[name="api-mode"]')];
const chatHistory = [];


function renderMarkdown(element, content) {
  const html = marked.parse(content);
  element.innerHTML = DOMPurify.sanitize(html, {
    USE_PROFILES: { html: true },
  });
}


function addMessage(role, content) {
  const wrapper = document.createElement("div");
  wrapper.className = role === "user" ? "chat chat-end" : "chat chat-start";

  const label = document.createElement("div");
  label.className = "chat-header mb-1 text-xs text-base-content/60";
  label.textContent = role === "user" ? "나" : "AI";

  const bubble = document.createElement("div");
  bubble.className = role === "user"
    ? "chat-bubble chat-bubble-primary"
    : "chat-bubble markdown-body bg-base-200 text-base-content";

  if (role === "assistant") {
    renderMarkdown(bubble, content);
  } else {
    bubble.textContent = content;
  }

  wrapper.append(label, bubble);
  messages.appendChild(wrapper);
  messages.scrollTop = messages.scrollHeight;
  return bubble;
}


function addDocuments(docs) {
  const usedDocs = docs.filter((doc) => doc.metadata?.used === true);
  if (!usedDocs.length) return;

  const details = document.createElement("details");
  details.className =
    "collapse collapse-arrow mt-3 border border-base-300 bg-base-200";

  const summary = document.createElement("summary");
  summary.className = "collapse-title font-semibold text-primary";
  summary.textContent = `답변에 사용한 문서 청크 ${usedDocs.length}개`;
  details.appendChild(summary);

  const list = document.createElement("div");
  list.className =
    "collapse-content flex max-h-80 flex-col gap-3 overflow-y-auto";

  usedDocs.forEach((retrievedDocument, index) => {
    const card = document.createElement("article");
    card.className = "card border border-base-300 bg-base-100";

    const body = document.createElement("div");
    body.className = "card-body gap-2 p-4";

    const title = document.createElement("strong");
    title.className = "text-sm text-primary";
    const source = retrievedDocument.metadata?.source ?? "출처 정보 없음";
    const fileName = source.split(/[\\/]/).pop();
    const page = Number.isInteger(retrievedDocument.metadata?.page)
      ? ` · ${retrievedDocument.metadata.page + 1}쪽`
      : "";
    title.textContent = `청크 ${index + 1} · ${fileName}${page}`;

    const content = document.createElement("p");
    content.className = "document-content text-sm text-base-content/75";
    content.textContent = retrievedDocument.page_content;

    body.append(title, content);
    card.appendChild(body);
    list.appendChild(card);
  });

  details.appendChild(list);
  messages.appendChild(details);
  messages.scrollTop = messages.scrollHeight;
}


async function readTextStream(response, answerBubble) {
  if (!response.body) throw new Error("스트림을 읽을 수 없습니다.");

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let answer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;

    answer += decoder.decode(value, { stream: true });
    renderMarkdown(answerBubble, answer);
    messages.scrollTop = messages.scrollHeight;
  }

  answer += decoder.decode();
  renderMarkdown(answerBubble, answer);
  return answer;
}


async function readRagStream(response, answerBubble) {
  if (!response.body) throw new Error("스트림을 읽을 수 없습니다.");

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let answer = "";

  function handleEvent(line) {
    if (!line.trim()) return;

    const event = JSON.parse(line);
    if (event.type === "token") {
      answer += event.content;
      renderMarkdown(answerBubble, answer);
      messages.scrollTop = messages.scrollHeight;
    } else if (event.type === "documents") {
      addDocuments(event.documents ?? []);
    } else if (event.type === "error") {
      throw new Error(event.message);
    }
  }

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";
    lines.forEach(handleEvent);
  }

  buffer += decoder.decode();
  handleEvent(buffer);
  return answer;
}


form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const message = input.value.trim();
  if (!message || sendButton.disabled) return;
  const selectedMode = modeInputs.find((mode) => mode.checked)?.value ?? "chat";

  addMessage("user", message);
  const answerBubble = addMessage("assistant", "");
  const loadingIndicator = document.createElement("span");
  loadingIndicator.className = "loading loading-dots loading-xl";
  loadingIndicator.setAttribute("aria-label", "답변 생성 중");
  answerBubble.appendChild(loadingIndicator);
  chatHistory.push({ role: "user", content: message });
  input.value = "";
  input.disabled = true;
  sendButton.disabled = true;
  modeInputs.forEach((mode) => { mode.disabled = true; });

  try {
    const response = await fetch(API_URLS[selectedMode], {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ messages: chatHistory }),
    });

    if (!response.ok) throw new Error("서버 응답 오류");

    let answer = "";

    if (selectedMode === "chat_stream") {
      answer = await readTextStream(response, answerBubble);
    } else if (selectedMode === "rag_stream") {
      answer = await readRagStream(response, answerBubble);
    } else {
      const data = await response.json();
      answer = data.answer;
      renderMarkdown(answerBubble, answer);
      if (selectedMode === "rag") addDocuments(data.docs ?? []);
    }

    chatHistory.push({ role: "assistant", content: answer });
  } catch (error) {
    console.error(error);
    chatHistory.pop();
    renderMarkdown(answerBubble, "서버에 연결하지 못했습니다.");
  } finally {
    input.disabled = false;
    sendButton.disabled = false;
    modeInputs.forEach((mode) => { mode.disabled = false; });
    input.focus();
  }
});
