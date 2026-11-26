from retriever import Retriever
from langchain.agents import create_agent


retriever = Retriever(
    persist_directory="chap09/chroma_store",
    data_files=[
        "chap09/data/OneNYC_2050_Strategic_Plan.pdf",
        "chap09/data/2040_seoul_plan.pdf"
    ],
    chunk_size=1000,
    chunk_overlap=100,
    k=5
)

def retrieve_docs(query):
    """
    vector store에서 query에 대한 관련 문서를 검색하고, 검색된 문서들을 직렬화하여 반환하는 함수
    """
    
    docs = retriever.invoke(query)
    
    serialized_docs = "\n\n".join(
        f"Source: {doc.metadata}\nContent: {doc.page_content}" for doc in docs
    )

    return serialized_docs


# -----------------------------
# Agent
# -----------------------------


rag_agent = create_agent(
    model="openai:gpt-5.4-mini",
    system_prompt="도시 계획 관련 질문에 대해 친절하게 답변하는 도우미 역할을 수행합니다. 존댓말로 공손히 답하라. 도시 계획 관련한 내용은 반드시 도구를 이용해서 근거에 기반하여 답하라.",
    tools=[
        retrieve_docs
    ],
)


if __name__ == "__main__":
    query = "서울시 쓰레기 저감 정책은?"
    results = retrieve_docs(query)
    print(results)

    print('-----------------------------')
    agent_response = rag_agent.invoke({
        "messages": [
            {"role": "user", "content": query}
        ]
    })
    for message in agent_response["messages"]:
        message.pretty_print()



