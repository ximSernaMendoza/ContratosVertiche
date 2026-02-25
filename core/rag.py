import os
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings

def build_vectorstore_from_pdf(pdf_path: str, persist_dir: str, collection_name: str):
    loader = PyPDFLoader(pdf_path)
    docs = loader.load()

    splitter = RecursiveCharacterTextSplitter(chunk_size=900, chunk_overlap=120)
    chunks = splitter.split_documents(docs)

    emb_model = HuggingFaceEmbeddings(model_name=os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2"))

    vs = Chroma.from_documents(
        documents=chunks,
        embedding=emb_model,
        persist_directory=persist_dir,
        collection_name=collection_name
    )
    return vs

def get_retriever(vs: Chroma, k: int = 6):
    return vs.as_retriever(search_kwargs={"k": k})
