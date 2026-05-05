# Wiki Content

## Markdown Formatting

Dataiku wiki articles support standard markdown:

```markdown
# Heading 1
## Heading 2
### Heading 3

**Bold text** and *italic text*

- Bullet list
- Another item

1. Numbered list
2. Another item

`inline code`

​```python
# Code block with syntax highlighting
print("Hello")
​```

| Column 1 | Column 2 |
|----------|----------|
| Cell 1   | Cell 2   |

[Link text](url)

![Image alt text](attachment:image.png)
```

## Referencing Attachments

After uploading an attachment, reference it in the article body:

```markdown
![My Diagram](attachment:diagram.png)
```

## Article Metadata

```python
article = wiki.get_article("my-article")
data = article.get_data()

# Get metadata (attachment info, etc.)
metadata = data.get_metadata()

# Set metadata
data.set_metadata(metadata)
data.save()
```

## Article Discussions

```python
article = wiki.get_article("my-article")
discussions = article.get_object_discussions()
```

## Programmatic Wiki Generation

Create a full wiki from project contents:

```python
wiki = project.get_wiki()

# Create home article
home = wiki.create_article(
    article_name="Project Overview",
    content=f"# {project.get_metadata().get('label', 'Project')}\n\nAuto-generated wiki."
)

# Create dataset documentation
datasets_article = wiki.create_article(
    article_name="Datasets",
    content="# Datasets\n\nDocumentation for all datasets in this project.",
    parent_id=home.get_data().get_name()
)

# Add an article per dataset
for ds_info in project.list_datasets():
    ds = project.get_dataset(ds_info["name"])
    schema = ds.get_settings().get_schema()
    cols = schema.get("columns", [])

    col_table = "| Column | Type |\n|--------|------|\n"
    for col in cols:
        col_table += f"| `{col['name']}` | {col.get('type', 'unknown')} |\n"

    wiki.create_article(
        article_name=ds_info["name"],
        content=f"# {ds_info['name']}\n\n## Schema\n\n{col_table}"
    )
```

## Pitfalls

**Article names vs IDs:** `wiki.get_article()` accepts either a name or an ID. Names are case-sensitive. If an article name contains spaces, pass the exact name.

**`upload_attachement` has a typo:** The method is spelled `upload_attachement` (not `upload_attachment`) in the Dataiku API. Use the misspelled version.

**`save()` is on the data object:** After modifying article content with `set_body()` or `set_name()`, call `data.save()`, not `article.save()`.
