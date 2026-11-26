from pathlib import Path

import pypdf
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter


class Retriever:
    def __init__(
        self,
        persist_directory: str | Path,
        data_files: list[str | Path],
        chunk_size: int = 1000,
        chunk_overlap: int = 100,
        k: int = 5,
    ):
        self.persist_directory = Path(persist_directory)
        self.data_files = [Path(data_file) for data_file in data_files]
        self.chunk_overlap = chunk_overlap
        self.embedding = OpenAIEmbeddings(model="text-embedding-3-large")

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

        if self.persist_directory.exists():
            self.vectorstore = Chroma(
                persist_directory=str(self.persist_directory),
                embedding_function=self.embedding,
            )
        else:
            missing_files = [path for path in self.data_files if not path.exists()]
            if missing_files:
                missing_names = ", ".join(str(path) for path in missing_files)
                raise FileNotFoundError(
                    f"RAG 원본 파일을 찾을 수 없습니다: {missing_names}"
                )

            all_splits = []
            for data_file in self.data_files:
                documents = self.load_pdf_pages(data_file)
                all_splits.extend(text_splitter.split_documents(documents))

            self.vectorstore = Chroma.from_documents(
                documents=all_splits,
                embedding=self.embedding,
                persist_directory=str(self.persist_directory),
            )

        self.retriever = self.vectorstore.as_retriever(
            search_kwargs={"k": k}
        )

    def load_pdf_pages(self, file_path: str | Path) -> list[Document]:
        reader = pypdf.PdfReader(file_path)
        documents = []
        original_texts = []

        for page_number, page in enumerate(reader.pages):
            page_content = page.extract_text() or ""
            if not page_content.strip():
                continue

            previous_page_tail = (
                original_texts[-1][-self.chunk_overlap:]
                if original_texts
                else ""
            )
            overlapped_content = previous_page_tail + "\n\n" + page_content
            original_texts.append(page_content)

            documents.append(Document(
                page_content=overlapped_content,
                metadata={
                    "source": str(file_path),
                    "page": page_number,
                    "total_pages": len(reader.pages),
                },
            ))

        return documents

    def invoke(self, query: str) -> list[Document]:
        return self.retriever.invoke(query)
