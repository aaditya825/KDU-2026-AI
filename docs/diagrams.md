# RAG Chatbot Walkthrough Diagrams

This file groups the diagrams needed for the walkthrough video into one place.

## 1. Overall System Design

```mermaid
flowchart LR
    A["User uploads PDF or blog URL"] --> B["Document loader"]
    B --> C["Normalize into Document model"]
    C --> D["Contextual chunking<br/>chunk_size=512, overlap=50"]
    D --> E["Generate embeddings<br/>sentence-transformers"]
    D --> F["Create BM25 index"]
    E --> G["Store vectors in ChromaDB"]
    F --> H["Store keyword index"]
    I["User asks a question in Streamlit UI"] --> J["Semantic retrieval top-10"]
    I --> K["Keyword retrieval top-10"]
    J --> L["RRF fusion + deduplication"]
    K --> L
    L --> M["Cross-encoder reranking"]
    M --> N["Top-5 chunks"]
    N --> O["Gemini response generation"]
    O --> P["Answer + citations + metrics"]
```

## 2. Document Ingestion And Chunking

```mermaid
flowchart TD
    A["PDF or blog URL"] --> B["Source-specific loader"]
    B --> C["Common Document model"]
    C --> D["Extract sections if available"]
    D --> E["Contextual chunker"]
    E --> F["Recursive fallback splitter"]
    F --> G["Chunks with metadata"]
    G --> H["chunk_id"]
    G --> I["document_id"]
    G --> J["position"]
    G --> K["section_title"]
    G --> L["source metadata"]
    G --> M["Embedding generation"]
    G --> N["Keyword indexing"]
```

## 3. Hybrid Search And Reranking

```mermaid
flowchart LR
    A["User query"] --> B["Semantic retriever"]
    A --> C["BM25 keyword retriever"]
    B --> D["Top-10 semantic results"]
    C --> E["Top-10 keyword results"]
    D --> F["Deduplicate by chunk_id"]
    E --> F
    F --> G["Reciprocal Rank Fusion"]
    G --> H["Fused top-10 candidates"]
    H --> I["Cross-encoder reranker"]
    I --> J["Final top-5 chunks"]
    H --> K["Fallback if reranker unavailable"]
```

## 4. Final Response Generation

Use this when explaining how the final answer stays grounded in retrieved evidence.

```mermaid
flowchart TD
    A["Final top-5 chunks"] --> B["Context builder"]
    B --> C["Prompt manager"]
    C --> D["Gemini LLM"]
    E["User question"] --> C
    D --> F["Grounded answer"]
    B --> G["Source citations"]
    F --> H["Streamlit UI"]
    G --> H
    I["Latency and retrieval metrics"] --> H
```
