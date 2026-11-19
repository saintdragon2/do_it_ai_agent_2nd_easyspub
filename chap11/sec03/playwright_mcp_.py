
import asyncio
import sys
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools
from langchain.agents.middleware import ToolRetryMiddleware
from langchain.agents import create_agent

from dotenv import load_dotenv

load_dotenv()


async def main():
    mcp_client = MultiServerMCPClient(
        {
            "playwright": {
                "transport": "stdio",
                "command": "npx.cmd" if sys.platform == "win32" else "npx",
                "args": [
                    "-y",
                    "@playwright/mcp@latest",
                    "--browser",
                    "chrome",
                    "--isolated",
                    "--viewport-size",
                    "1280x800",
                ],
            }
        }
    )

    allowed = {
        "browser_navigate",
        "browser_snapshot",
        "browser_click",
        "browser_wait_for",
    }

    # 접속, 스냅샷, 클릭이 같은 브라우저에서 실행되도록 세션을 유지합니다.
    async with mcp_client.session("playwright") as session:
        tools = await load_mcp_tools(session)
        tools = [tool for tool in tools if tool.name in allowed]
        for tool in tools:
            print(tool.name, "-", tool.description)

        agent = create_agent(
            model="openai:gpt-5.5",
            system_prompt="""
            당신은 웹 사이트에서 정보를 정확하게 수집하는 에이전트입니다.

            반드시 Playwright MCP 도구를 사용하십시오.
            페이지에 접속한 뒤 browser_snapshot으로 구조를 확인하십시오.
            직접 클릭해서 상세 페이지로 가는 것을 권장합니다.
            페이지에 실제로 표시된 정보만 수집하십시오.
            """,
            tools=tools,
            middleware=[ToolRetryMiddleware(max_retries=3)],
        )
        result = await agent.ainvoke(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": """
                        https://easyspub.co.kr/Main 에 접속하세요.

                        최근 나온 책들을 10권 알려주세요. 저자와 가격, 그리고 주요 소개를 함께 알려주세요. 
                        아마 저자와 가격 같은 정보는 상세 페이지에 들어가야 알 수 있으니까 그렇게 해주세요. 
                        """,
                    }
                ]
            }
        )

        for message in result["messages"]:
            message.pretty_print()


if __name__ == "__main__":
    asyncio.run(main())


