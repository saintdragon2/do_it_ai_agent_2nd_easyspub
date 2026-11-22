import DOMPurify from "dompurify";
import { marked } from "marked";

import "./style.css";


marked.use({ breaks: true, gfm: true });


const API_URL =
  import.meta.env.VITE_API_URL ?? "http://localhost:8000/chat/stream";
const form = document.querySelector("#chat-form");
const input = document.querySelector("#message-input");
const messages = document.querySelector("#messages");
const sendButton = document.querySelector("#send-button");
const resetButton = document.querySelector("#reset-button");
const status = document.querySelector("#status");
let chatHistory = [];


function appendMessage(role, content = "") {
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


function renderMarkdown(element, content) {
  const html = marked.parse(content);
  element.innerHTML = DOMPurify.sanitize(html, {
    USE_PROFILES: { html: true },
  });
}


function setLoading(isLoading) {
  input.disabled = isLoading;
  sendButton.disabled = isLoading;
  status.textContent = isLoading ? "답변 중" : "준비됨";
  status.className = isLoading
    ? "badge badge-warning badge-sm"
    : "badge badge-success badge-sm";
}


async function sendMessage(message) {
  appendMessage("user", message);
  chatHistory.push({ role: "user", content: message });
  const answerBubble = appendMessage("assistant");
  setLoading(true);

  try {
    const response = await fetch(API_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ messages: chatHistory }),
    });

    if (!response.ok) {
      const detail = await response.text();
      throw new Error(detail || "서버 응답 오류");
    }
    if (!response.body) throw new Error("스트림을 읽을 수 없습니다.");

    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");
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
    chatHistory.push({
      role: "assistant",
      content: answer,
    });
  } catch (error) {
    console.error(error);
    chatHistory.pop();
    renderMarkdown(
      answerBubble,
      "서버에 연결하지 못했습니다. 백엔드 실행 상태를 확인해 주세요.",
    );
  } finally {
    setLoading(false);
    input.focus();
  }
}


form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const message = input.value.trim();
  if (!message || sendButton.disabled) return;
  input.value = "";
  await sendMessage(message);
});


input.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    form.requestSubmit();
  }
});


document.querySelectorAll(".example-button").forEach((button) => {
  button.addEventListener("click", () => {
    input.value = button.textContent.trim();
    input.focus();
  });
});


resetButton.addEventListener("click", () => {
  chatHistory = [];
  messages.innerHTML = "";
  appendMessage("assistant", "새 대화를 시작했습니다. 무엇이 궁금한가요?");
  input.focus();
});
