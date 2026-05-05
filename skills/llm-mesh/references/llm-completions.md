# LLM Completions

## Multipart Messages

For messages that include images or other media:

```python
completion = llm.new_completion()
msg = completion.new_multipart_message(role="user")
msg.with_text("Describe this chart.")
msg.with_image(image_bytes)
response = completion.execute()
```

## Context and Memory

### Add Context

```python
completion = llm.new_completion()
completion.with_context("The current project is a customer churn prediction pipeline.")
completion.with_message("What features should I include?", role="user")
response = completion.execute()
```

### Memory Fragments (Stateful Conversations)

```python
# First turn
completion = llm.new_completion()
completion.with_message("Remember that I'm working with healthcare data.", role="user")
response = completion.execute()
memory = response.memory_fragment

# Second turn (continues context)
completion = llm.new_completion()
completion.with_memory_fragment(memory)
completion.with_message("What compliance considerations should I keep in mind?", role="user")
response = completion.execute()
```

## Guardrails

```python
completion = llm.new_completion()
guardrail = completion.new_guardrail(type="content_filter")
# Configure guardrail parameters...
completion.with_message("Generate a report.", role="user")
response = completion.execute()
```

## Tool Calls

When an LLM response includes tool calls:

```python
response = completion.execute()

if response.tool_calls:
    for tool_call in response.tool_calls:
        print(f"Tool: {tool_call['name']}")
        print(f"Args: {tool_call['arguments']}")

if response.tool_validation_requests:
    for request in response.tool_validation_requests:
        print(f"Validation needed: {request}")
```

## Response Properties

| Property | Type | Description |
|----------|------|-------------|
| `text` | str | Raw text response |
| `json` | dict | Parsed JSON (if `with_json_output` was used) |
| `parsed` | object | Structured output instance (if `with_structured_output` was used) |
| `success` | bool | Whether the query succeeded |
| `tool_calls` | list | Tool invocations requested by the LLM |
| `memory_fragment` | object | State for continuing conversations |
| `log_probs` | list | Token probabilities (if model supports) |
| `trace` | dict | Execution trace for debugging |
| `total_usage` | dict | Token consumption metrics |

## Reranking

For reranking documents by relevance:

```python
llm = project.get_llm("my_reranking_model")
query = llm.new_reranking()
query.with_query("customer churn prediction")
query.with_document("This document is about customer retention strategies.")
query.with_document("This document is about inventory management.")
query.with_document("This document is about predicting customer attrition.")

response = query.execute()
for doc in response.documents:
    print(f"Index: {doc.index}, Score: {doc.relevance_score:.3f}")
```

## Pitfalls

**LLM ID is not the model name:** The `llm_id` passed to `project.get_llm()` is the Dataiku-configured LLM identifier, not the upstream model name (e.g., not `"gpt-4"` but the ID shown in the LLM Mesh settings).

**`text_overflow_mode` matters for embeddings:** When input text exceeds the model's token limit, `"FAIL"` raises an error (default), `"TRUNCATE"` silently truncates. Choose based on your use case.
