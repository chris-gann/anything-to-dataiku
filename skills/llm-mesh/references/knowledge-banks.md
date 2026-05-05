# Knowledge Banks

## Overview

Knowledge banks are vector stores that enable RAG (retrieval-augmented generation) patterns. They index text from datasets or files and make it searchable via semantic similarity.

## List Knowledge Banks

```python
kbs = project.list_knowledge_banks()
for kb in kbs:
    print(f"{kb.name} (id: {kb.id}, project: {kb.project_key})")
```

## Create and Configure

Knowledge banks are typically created in the DSS UI. Once created, configure via the API:

```python
kb = project.get_knowledge_bank("my_kb")
settings = kb.get_settings()

# View configuration
print(f"ID: {settings.id}")
print(f"Vector store type: {settings.vector_store_type}")

# Set metadata schema for filtering during search
settings.set_metadata_schema({
    "source": "string",
    "date": "date",
    "category": "string"
})

# Associate an images folder
settings.set_images_folder("managed_folder_id")

settings.save()
```

## Build the Knowledge Bank

```python
kb = project.get_knowledge_bank("my_kb")
job = kb.build(job_type="NON_RECURSIVE_FORCED_BUILD", wait=True)
```

## Search Parameters

```python
result = kb.search(
    query="How to handle null values",
    max_documents=10,                    # Max results to return
    search_type="SIMILARITY",            # Search strategy
    similarity_threshold=0.5,            # Min score (SIMILARITY_THRESHOLD only)
    mmr_documents_count=20,              # Candidate pool size (MMR only)
    mmr_factor=0.25,                     # Diversity factor (MMR only)
    hybrid_use_advanced_reranking=False,  # Use reranking model (HYBRID only)
    hybrid_rrf_rank_constant=60,         # RRF constant (HYBRID only)
    hybrid_rrf_rank_window_size=4         # RRF window (HYBRID only)
)
```

## Search Result Documents

```python
for doc in result.documents:
    print(f"Text: {doc.text[:200]}")
    print(f"Score: {doc.score:.3f}")
    print(f"Metadata: {doc.metadata}")

    if doc.images:
        print(f"Images: {len(doc.images)}")
    if doc.file_ref:
        print(f"File ref: {doc.file_ref}")
```

## Search Types Explained

| Type | Use When |
|------|----------|
| `SIMILARITY` | Simple semantic search, return top-N most similar |
| `SIMILARITY_THRESHOLD` | Only return results above a minimum score |
| `MMR` | Need diverse results (avoids returning near-duplicates) |
| `HYBRID` | Combine keyword search with semantic search for better recall |

## LangChain Integration

```python
# As a LangChain retriever
retriever = kb.as_langchain_retriever(
    search_type="similarity",
    search_kwargs={"k": 5}
)

# As a LangChain vector store (advanced)
vectorstore = kb.as_langchain_vectorstore()
```

## Inside DSS (dataiku.KnowledgeBank)

```python
import dataiku

kb = dataiku.KnowledgeBank("my_kb")

# Get current version
version = kb.get_current_version()

# Write to the knowledge bank
writer = kb.get_writer()
# ... write documents ...
```

## Delete a Knowledge Bank

```python
kb = project.get_knowledge_bank("my_kb")
kb.delete()
```

## Pitfalls

**Build before search:** A knowledge bank must be built before it can be searched. If you get empty results, check that the build completed successfully.

**Metadata schema must match data:** The metadata schema set via `set_metadata_schema()` must match the actual metadata fields in the indexed documents. Mismatched fields are silently ignored during search filtering.
