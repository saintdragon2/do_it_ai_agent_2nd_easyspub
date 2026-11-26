import os
import pypdf
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from dotenv import load_dotenv


load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


class Retriever:
    def __init__(
        self,
        persist_directory: str,
        data_files: list,
        chunk_size: int = 1000,
        chunk_overlap: int = 100,
        k: int = 4
    ):
        self.persist_directory = persist_directory
        self.data_files = data_files
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.k = k
        self.embedding = OpenAIEmbeddings(model='text-embedding-3-large', api_key=OPENAI_API_KEY)
        
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size, 
            chunk_overlap=self.chunk_overlap
        )

        if not os.path.exists(self.persist_directory):
            print("Creating new Chroma store")

            all_splits = []
            for file in self.data_files:
                print(f"Loading and splitting file: {file}")
                documents = self.load_pdf_pages(file)
                splits = self.text_splitter.split_documents(documents)
                all_splits.extend(splits)

            self.vectorstore = Chroma.from_documents(
                documents=all_splits,
                embedding=self.embedding,
                persist_directory=self.persist_directory
            )
        else:
            print("Loading existing Chroma store")
            self.vectorstore = Chroma(
                persist_directory=self.persist_directory,
                embedding_function=self.embedding
            )

        self.retriever = self.vectorstore.as_retriever(k=k)

    
    def load_pdf_pages(self, file_path: str) -> list[Document]:
        reader = pypdf.PdfReader(file_path)
        documents = []
        original_texts = []

        for page_number, page in enumerate(reader.pages):
            with pypdf.apply_configuration(
                stream_parsing_work_maximum_count=10_000_000,
            ):
                page_content = page.extract_text() or ""
            
            if not page_content.strip():
                continue

            if len(documents) > 0:
                previous_page_tail = original_texts[-1][-self.chunk_overlap:]
            else:
                previous_page_tail = ""

            overlapped_content = previous_page_tail + "\n\n" +  page_content
            original_texts.append(page_content)  

            metadata = {
                "source": file_path,
                "page": page_number,
                "total_pages": len(reader.pages),
            }
            document = Document(page_content=overlapped_content, metadata=metadata)
            documents.append(document)

        return documents

    def invoke(self, query: str):
        results = self.retriever.invoke(query)
        return results


if __name__ == "__main__":
    retriever = Retriever(
        persist_directory="chap09/chroma_store",
        data_files=[
            "chap09/data/OneNYC_2050_Strategic_Plan.pdf",
            "chap09/data/2040_seoul_plan.pdf"
        ]
    )
    print("Retriever initialized successfully.")

    query = "서울시 쓰레기 저감 정책은?"
    results = retriever.invoke(query)
    
    for i, result in enumerate(results):
        print(f"Result {i+1}:")
        print(result.page_content)
        print("\n---\n")