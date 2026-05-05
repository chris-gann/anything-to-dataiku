---
name: wikis
description: "Use when creating, reading, or updating Dataiku project wiki articles, managing wiki taxonomy, or exporting wikis"
---

# Wiki Patterns

Reference patterns for managing Dataiku project wikis via the Python API.

## Key Concepts

| Concept | What it is | Scope |
|---------|-----------|-------|
| **Wiki** | A collection of markdown articles in a project | Per project |
| **Article** | A single wiki page with markdown content and attachments | Per wiki |
| **Taxonomy** | The hierarchical structure of articles (parent-child relationships) | Per wiki |
| **Home Article** | The default landing page of the wiki | Per wiki |

## Access the Project Wiki

```python
wiki = project.get_wiki()
```

## List Articles

```python
articles = wiki.list_articles()
for article in articles:
    data = article.get_data()
    print(f"{data.get_name()} (id: {article})")
```

## Create an Article

```python
article = wiki.create_article(
    article_name="Getting Started",
    content="# Getting Started\n\nThis project contains the customer churn pipeline.",
    parent_id=None  # Top-level article (or pass parent article ID)
)
```

## Read Article Content

```python
article = wiki.get_article("getting-started")  # By name or ID
data = article.get_data()

# Get the markdown body
body = data.get_body()
print(body)

# Get article name
name = data.get_name()
```

## Update Article Content

```python
article = wiki.get_article("getting-started")
data = article.get_data()

data.set_body("""
# Getting Started

## Overview
This project implements a customer churn prediction pipeline.

## Data Sources
- `CUSTOMERS` — Customer demographics
- `TRANSACTIONS` — Purchase history
- `INTERACTIONS` — Support ticket data

## Pipeline Steps
1. Data cleaning and preparation
2. Feature engineering
3. Model training
4. Scoring and deployment
""")

data.save()
```

## Rename an Article

```python
article = wiki.get_article("old-name")
data = article.get_data()
data.set_name("New Article Name")
data.save()
```

## Delete an Article

```python
article = wiki.get_article("obsolete-article")
article.delete()
```

## Wiki Taxonomy

The taxonomy defines the hierarchy of articles:

```python
settings = wiki.get_settings()

# Get the current taxonomy
taxonomy = settings.get_taxonomy()
print(taxonomy)

# Set a new taxonomy (list of article IDs with children)
settings.set_taxonomy([
    {
        "id": "home-article-id",
        "children": [
            {"id": "setup-id", "children": []},
            {"id": "architecture-id", "children": [
                {"id": "data-model-id", "children": []}
            ]}
        ]
    }
])
settings.save()

# Move an article to a new parent
settings.move_article_in_taxonomy("article-id", parent_article_id="new-parent-id")
settings.save()
```

## Home Article

```python
settings = wiki.get_settings()

# Get the home article
home_id = settings.get_home_article_id()

# Set a different home article
settings.set_home_article_id("new-home-article-id")
settings.save()
```

## Attachments

```python
article = wiki.get_article("my-article")

# Upload an attachment
with open("diagram.png", "rb") as f:
    article.upload_attachement(f, "diagram.png")

# Download an attachment
response = article.get_uploaded_file("upload_id")
```

## Export Wiki

```python
# Export entire wiki as PDF/ZIP
wiki.export_to_file("wiki_export.pdf", paper_size="A4")

# Export with attachments
wiki.export_to_file("wiki_export.zip", paper_size="A4", export_attachment=True)

# Export a single article
article = wiki.get_article("my-article")
article.export_to_file("article.pdf", paper_size="A4")

# Export article with children
article.export_to_file("article_tree.pdf", paper_size="A4", export_children=True)
```

### Paper Sizes

| Size | Value |
|------|-------|
| A4 | `"A4"` |
| A3 | `"A3"` |
| US Letter | `"US_LETTER"` |
| Ledger | `"LEDGER"` |

## Detailed References

- [references/wiki-content.md](references/wiki-content.md) — Markdown formatting, metadata, article discussions

## Related Skills

- [skills/workspaces/](../workspaces/) — Adding wiki articles to workspaces
- [skills/projects/](../projects/) — Project-level metadata and documentation
