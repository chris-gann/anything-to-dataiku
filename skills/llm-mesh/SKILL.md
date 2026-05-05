---
name: llm-mesh
description: "Use when working with Dataiku LLM Mesh for completions, embeddings, image generation, knowledge banks, or RAG patterns"
---

# LLM Mesh Patterns

Reference patterns for using Dataiku's LLM Mesh via the Python API.

## Key Concepts

| Concept | What it is | Scope |
|---------|-----------|-------|
| **LLM Mesh** | Dataiku's unified API for accessing LLMs (OpenAI, Anthropic, etc.) | Instance-level |
| **DSSLLM** | A handle to a specific LLM configured in Dataiku | Per project |
| **Knowledge Bank** | A vector store for RAG (retrieval-augmented generation) | Per project |
| **Completion** | A text generation request to an LLM | Per query |
| **Embedding** | A text-to-vector transformation | Per query |

## List Available LLMs

```python
llms = project.list_llms()
for llm in llms:
    print(f"{llm.id} — {llm.description}")
```

## Get an LLM Handle

```python
llm = project.get_llm("llm_id")
```

## Text Completion

### Simple Completion

```python
llm = project.get_llm("my_llm_id")
completion = llm.new_completion()
completion.with_message("Explain what a join recipe does in Dataiku.", role="user")
response = completion.execute()

print(response.text)
print(f"Success: {response.success}")
```

### Multi-Turn Conversation

```python
completion = llm.new_completion()
completion.with_message("You are a helpful data engineering assistant.", role="system")
completion.with_message("How do I create a prepare recipe?", role="user")
response = completion.execute()
print(response.text)
```

### JSON Output

```python
completion = llm.new_completion()
completion.with_message("List 3 common data quality issues as JSON.", role="user")
completion.with_json_output(schema={
    "type": "object",
    "properties": {
        "issues": {
            "type": "array",
            "items": {"type": "string"}
        }
    }
})
response = completion.execute()
print(response.json)
```

### Structured Output

```python
from pydantic import BaseModel

class DataQualityReport(BaseModel):
    dataset_name: str
    row_count: int
    issues: list[str]

completion = llm.new_completion()
completion.with_message("Analyze the customers dataset.", role="user")
completion.with_structured_output(DataQualityReport)
response = completion.execute()

report = response.parsed  # DataQualityReport instance
print(f"Dataset: {report.dataset_name}, Issues: {report.issues}")
```

### Streaming Completion

```python
completion = llm.new_completion()
completion.with_message("Write a long explanation of ETL pipelines.", role="user")

for chunk in completion.execute_streamed():
    print(chunk, end="", flush=True)
```

## Batch Completions

```python
batch = llm.new_completions()

# Add multiple completions
c1 = batch.new_completion()
c1.with_message("What is a dataset?", role="user")

c2 = batch.new_completion()
c2.with_message("What is a recipe?", role="user")

responses = batch.execute()
for resp in responses:
    print(resp.text)
```

## Embeddings

```python
llm = project.get_llm("my_embedding_model")
query = llm.new_embeddings(text_overflow_mode="TRUNCATE")

query.add_text("Customer churn prediction")
query.add_text("Revenue forecasting model")

response = query.execute()
embeddings = response.get_embeddings()

for i, emb in enumerate(embeddings):
    print(f"Embedding {i}: dimension={len(emb)}")
```

## Image Generation

```python
llm = project.get_llm("my_image_model")
query = llm.new_images_generation()

query.with_prompt("A data pipeline diagram with clean modern design")
query.height = 1024
query.width = 1024

response = query.execute()
image_bytes = response.first_image(as_type="bytes")

with open("pipeline_diagram.png", "wb") as f:
    f.write(image_bytes)
```

## Knowledge Banks (RAG)

### Search a Knowledge Bank

```python
kb = project.get_knowledge_bank("my_kb")

result = kb.search(
    query="How to handle missing values",
    max_documents=5,
    search_type="SIMILARITY"
)

for doc in result.documents:
    print(f"Score: {doc.score:.3f}")
    print(f"Text: {doc.text[:200]}")
    print(f"Metadata: {doc.metadata}")
    print()
```

### Build a Knowledge Bank

```python
kb = project.get_knowledge_bank("my_kb")
job = kb.build(job_type="NON_RECURSIVE_FORCED_BUILD", wait=True)
```

### Knowledge Bank Settings

```python
kb = project.get_knowledge_bank("my_kb")
settings = kb.get_settings()

# Set metadata schema for filtering
settings.set_metadata_schema({
    "category": "string",
    "date": "date",
    "priority": "int"
})
settings.save()
```

### Search Types

| Type | Description |
|------|-------------|
| `SIMILARITY` | Pure cosine similarity search |
| `SIMILARITY_THRESHOLD` | Similarity with minimum score threshold |
| `MMR` | Maximal Marginal Relevance (diversity-aware) |
| `HYBRID` | Combines keyword and semantic search |

## LangChain Integration

```python
# Use LLM as a LangChain chat model
chat_model = llm.as_langchain_chat_model()

# Use LLM as a LangChain embeddings provider
embeddings = llm.as_langchain_embeddings()

# Use Knowledge Bank as a LangChain retriever
retriever = kb.as_langchain_retriever()
```

## Token Usage

```python
response = completion.execute()
usage = response.total_usage
print(f"Input tokens: {usage.get('inputTokens')}")
print(f"Output tokens: {usage.get('outputTokens')}")
```

## Detailed References

- [references/llm-completions.md](references/llm-completions.md) — Multipart messages, guardrails, memory fragments, tool calls
- [references/knowledge-banks.md](references/knowledge-banks.md) — Knowledge bank configuration, search parameters, vector store types

## Related Skills

- [skills/dataset-management/](../dataset-management/) — Datasets used as knowledge bank sources
- [skills/managed-folders/](../managed-folders/) — Folders for knowledge bank images
