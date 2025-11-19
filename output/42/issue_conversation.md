# Issue #42 — RAG

## Original Post by @tbrandenburg

@task Embed the following python file in an uv project and test it. I want to run it via "uv run pyrag". No other commandline parameters or environment variables.
Apply a proper RAG architecture, but without adding features - keep it simple as it is - only restructure into loader, chunker, embedder, storage and search for clarity.
Do not use an HuggingFace token, instead use all-MiniLM-L6-v2 sentence transformer.
Apply PEP8 and run uv ruff check and uv ruff format.

#!/usr/bin/env python3
"""
Docling RAG with LangChain Example
Converted from: https://github.com/docling-project/docling/blob/main/docs/examples/rag_langchain.ipynb

This script demonstrates a complete RAG pipeline using:
- Docling for document processing
- LangChain for document loading and chain creation
- Milvus for vector storage
- HuggingFace for embeddings and LLM
"""

import os
import json
from pathlib import Path
from tempfile import mkdtemp
from dotenv import load_dotenv

from langchain_core.prompts import PromptTemplate
from langchain_docling import DoclingLoader
from langchain_docling.loader import ExportType
from docling.chunking import HybridChunker
from langchain_text_splitters import MarkdownHeaderTextSplitter
from langchain_huggingface.embeddings import HuggingFaceEmbeddings
from langchain_milvus import Milvus
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_huggingface import HuggingFaceEndpoint


def _get_env_from_colab_or_os(key):
    """Get environment variable from Colab secrets or OS environment."""
    try:
        from google.colab import userdata
        try:
            return userdata.get(key)
        except userdata.SecretNotFoundError:
            pass
    except ImportError:
        pass
    return os.environ.get(key, "")


def clip_text(text, threshold=100):
    """Clip text to a maximum length."""
    return f"{text[:threshold]}..." if len(text) > threshold else text


def main():
    # Load environment variables
    load_dotenv()
    
    # Configuration
    FILE_PATH = "https://arxiv.org/pdf/2408.09869"  # Docling Technical Report
    EXPORT_TYPE = ExportType.DOC_CHUNKS  # Options: ExportType.DOC_CHUNKS or ExportType.MARKDOWN
    EMBED_MODEL_ID = "sentence-transformers/all-MiniLM-L6-v2"
    GEN_MODEL_ID = "mistralai/Mistral-7B-Instruct-v0.2"
    TOP_K = 5
    QUESTION = "Which are the main AI models in Docling?"
    
    # Get HuggingFace token
    HF_TOKEN = _get_env_from_colab_or_os("HF_TOKEN")
    if not HF_TOKEN:
        print("Warning: HF_TOKEN not found. Set it in .env file or environment.")
    
    # Define prompt template
    PROMPT = PromptTemplate.from_template(
        """You are a helpful assistant. Answer the following question based on the provided context.

Context:
{context}

Question: {input}

Answer:"""
    )
    
    print("=" * 80)
    print("Docling RAG with LangChain Pipeline")
    print("=" * 80)
    
    # Step 1: Load documents with Docling
    print(f"\n1. Loading document from: {FILE_PATH}")
    print(f"   Export type: {EXPORT_TYPE}")
    
    loader = DoclingLoader(
        file_path=FILE_PATH,
        export_type=EXPORT_TYPE,
        chunker=HybridChunker(tokenizer=EMBED_MODEL_ID),
    )
    docs = loader.load()
    print(f"   Loaded {len(docs)} document(s)")
    
    # Step 2: Split documents based on export type
    print("\n2. Splitting documents...")
    
    if EXPORT_TYPE == ExportType.DOC_CHUNKS:
        splits = docs
        print(f"   Using doc chunks: {len(splits)} chunks")
    elif EXPORT_TYPE == ExportType.MARKDOWN:
        splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=[
                ("#", "Header_1"),
                ("##", "Header_2"),
                ("###", "Header_3"),
            ],
        )
        splits = [split for doc in docs for split in splitter.split_text(doc.page_content)]
        print(f"   Markdown splitting produced: {len(splits)} chunks")
    else:
        raise ValueError(f"Unexpected export type: {EXPORT_TYPE}")
    
    # Step 3: Create embeddings and vector store
    print(f"\n3. Creating embeddings with model: {EMBED_MODEL_ID}")
    embedding = HuggingFaceEmbeddings(model_name=EMBED_MODEL_ID)
    
    print("   Initializing Milvus vector store...")
    milvus_uri = str(Path(mkdtemp()) / "docling.db")
    print(f"   Vector DB location: {milvus_uri}")
    
    vectorstore = Milvus.from_documents(
        documents=splits,
        embedding=embedding,
        collection_name="docling_demo",
        connection_args={"uri": milvus_uri},
        index_params={"index_type": "FLAT"},
        drop_old=True,
    )
    print(f"   Vector store created with {len(splits)} documents")
    
    # Step 4: Create retrieval chain
    print(f"\n4. Setting up RAG chain with LLM: {GEN_MODEL_ID}")
    print(f"   Top-K retrieval: {TOP_K}")
    
    retriever = vectorstore.as_retriever(search_kwargs={"k": TOP_K})
    
    llm = HuggingFaceEndpoint(
        repo_id=GEN_MODEL_ID,
        huggingfacehub_api_token=HF_TOKEN,
    )
    
    question_answer_chain = create_stuff_documents_chain(llm, PROMPT)
    rag_chain = create_retrieval_chain(retriever, question_answer_chain)
    
    # Step 5: Query the RAG system
    print("\n5. Querying the RAG system...")
    print(f"   Question: {QUESTION}")
    print("\n" + "-" * 80)
    
    resp_dict = rag_chain.invoke({"input": QUESTION})
    
    # Display results
    clipped_answer = clip_text(resp_dict["answer"], threshold=200)
    print(f"\nQuestion:\n{resp_dict['input']}\n")
    print(f"Answer:\n{clipped_answer}\n")
    
    print("-" * 80)
    print("\nRetrieved Sources:")
    print("-" * 80)
    
    for i, doc in enumerate(resp_dict["context"]):
        print(f"\nSource {i + 1}:")
        print(f"  text: {json.dumps(clip_text(doc.page_content, threshold=350))}")
        for key in doc.metadata:
            if key != "pk":
                val = doc.metadata.get(key)
                clipped_val = clip_text(val) if isinstance(val, str) else val
                print(f"  {key}: {clipped_val}")
    
    print("\n" + "=" * 80)
    print("RAG pipeline completed successfully!")
    print("=" * 80)


if __name__ == "__main__":
    main()

## Comments
