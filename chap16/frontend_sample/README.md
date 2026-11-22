# 최종 프론트엔드 실행하기

이 예제는 Vite와 순수 HTML·CSS·자바스크립트로 만든 프론트엔드입니다. React나 Vue는 사용하지 않으며 Tailwind CSS와 daisyUI로 화면을 구성합니다. AI 답변은 Marked로 마크다운을 HTML로 변환하고 DOMPurify로 정화한 뒤 말풍선에 표시합니다.

```text
frontend_sample/
├── index.html
├── package.json
├── package-lock.json
├── vite.config.js
└── src/
    ├── main.js
    └── style.css
```

백엔드를 먼저 실행한 뒤 새 터미널에서 다음 명령을 실행합니다. `npm install`은 처음 한 번만 실행하면 됩니다.

```bash
cd chap16/frontend_sample
npm install
npm run dev
```

브라우저에서 <http://localhost:5173>에 접속합니다.

대화 히스토리는 `src/main.js`의 `chatHistory` 리스트에 저장되며, 메시지를 보낼 때마다 전체 리스트가 백엔드로 전달됩니다. 화면에는 daisyUI의 `chat-bubble`로 사용자와 AI 메시지를 구분하지만, 히스토리에는 렌더링 전 마크다운 문자열을 저장합니다. 페이지를 새로 고치거나 `새 대화`를 누르면 히스토리가 초기화됩니다.

스트리밍 중에는 도착한 문자열을 누적해 마크다운을 다시 렌더링합니다. Marked가 만든 HTML은 반드시 DOMPurify를 거친 뒤 화면에 넣습니다.

배포용 파일이 정상적으로 만들어지는지 확인하려면 `npm run build`를 실행합니다. 결과는 `dist` 폴더에 생성됩니다.
