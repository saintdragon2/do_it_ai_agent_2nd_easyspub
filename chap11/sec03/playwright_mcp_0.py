
import asyncio
import sys
from langchain_mcp_adapters.client import MultiServerMCPClient

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

    tools = await mcp_client.get_tools()

    for tool in tools:
        print(tool.name, "-", tool.description)


if __name__ == "__main__":
    asyncio.run(main())


