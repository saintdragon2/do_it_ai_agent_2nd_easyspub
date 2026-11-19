from langchain.agents import create_agent
from langchain.messages import HumanMessage
from datetime import datetime
import pytz
import yfinance as yf

import os
from dotenv import load_dotenv

load_dotenv()
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')


def get_current_time(timezone: str) -> str:
    """
    주어진 시간대의 현재 시간을 문자열로 반환합니다.

    Args:
        timezone (str): 시간대 문자열 (예: "Asia/Seoul")

    Returns:
        str: 현재 시간과 시간대 문자열
    """
    tz = pytz.timezone(timezone)
    now = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
    now_timezone = f"{now} {timezone}"
    print(now_timezone)
    return now_timezone


def get_yf_stock_recommendations(ticker: str):
    """
    주어진 주식 티커에 대한 추천 정보를 마크다운 형식으로 반환합니다.

    Args:
        ticker (str): 주식 티커 (예: "AAPL")

    Returns:
        str: 추천 정보를 마크다운 형식으로 변환한 문자열
    """
    stock = yf.Ticker(ticker)
    recommendations = stock.recommendations
    recommendations_md = recommendations.to_markdown() # 데이터프레임을 마크다운 형식으로 변환
    print(recommendations_md)
    return recommendations_md


agent = create_agent(
    model="openai:gpt-5.4-mini",
    system_prompt="너는 친절한 도우미다. 존댓말로 공손히 답하라.",
    tools=[
        get_current_time, 
        get_yf_stock_recommendations
    ]
)

messages = []

while True:
    user_input = input("\n사용자: ")
    if not user_input or user_input.lower() in ["종료", "exit", "quit"]:
        print("대화를 종료합니다.")
        break
    
    messages.append(HumanMessage(content=user_input))

    result = agent.invoke({
        "messages": messages
    })

    print("AI:", result["messages"][-1].content)

    messages = result["messages"]
    