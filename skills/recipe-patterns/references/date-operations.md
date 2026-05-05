# Date Operations Reference

Processors and GREL functions for parsing, formatting, and extracting date components.

## Pitfalls

**Parse before extracting:** `datePart()` requires a parsed date column. If your date is stored as a string, use a `DateParser` step first, then call `datePart()` on the parsed column. Using `datePart()` on an unparsed string returns null silently.

**Format patterns are Java-style:** Use `yyyy` (not `YYYY`), `MM` for month (not `mm` which is minutes), `dd` for day. Getting these wrong parses silently to wrong values.

## DateParser

Parse a string column into a date using a format pattern.

```python
{
    "type": "DateParser",
    "params": {
        "column": "date_string",
        "format": "yyyy-MM-dd",
        "outColumn": "parsed_date"
    }
}
```

Common format patterns:
| Pattern | Example Input |
|---------|---------------|
| `yyyy-MM-dd` | `2024-06-15` |
| `MM/dd/yyyy` | `06/15/2024` |
| `dd-MMM-yyyy` | `15-Jun-2024` |
| `yyyy-MM-dd HH:mm:ss` | `2024-06-15 14:30:00` |

## DateFormatter

Format a date column into a string representation.

```python
{
    "type": "DateFormatter",
    "params": {
        "column": "date_col",
        "format": "MM/dd/yyyy",
        "outColumn": "formatted_date"
    }
}
```

## datePart (GREL)

Extract a component from a date column using `CreateColumnWithGREL`.

```python
# Extract month
{
    "type": "CreateColumnWithGREL",
    "params": {
        "column": "month",
        "expression": "datePart(order_date, 'month')"
    }
}
```

Available parts:

| Part | Returns |
|------|---------|
| `year` | Four-digit year (e.g. `2024`) |
| `month` | 1-12 |
| `day` | 1-31 |
| `hour` | 0-23 |
| `minute` | 0-59 |
| `second` | 0-59 |
| `dayOfWeek` | 1 (Monday) - 7 (Sunday) |

## Filtering by Date Range

Use `FilterOnFormula` with string comparison on ISO-formatted dates.

```python
{
    "type": "FilterOnFormula",
    "params": {
        "formula": "order_date >= '2024-01-01' && order_date < '2025-01-01'",
        "action": "KEEP"
    }
}
```
