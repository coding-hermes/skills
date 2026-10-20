# Delegate Task Output Schema

When using `delegate_task` to structure subagent output, provide a valid JSON Schema via the `output_schema` parameter.

For a list of up to N strings (e.g., findings), use:

```json
{
  "properties": {
    "findings": {
      "items": {"type": "string"},
      "maxItems": N,
      "type": "array"
    }
  },
  "type": "object"
}

Note: Do not pass an integer for `maxItems` directly; it must be inside the schema as shown.

Example for max 4 findings:

```json
{
  "properties": {
    "findings": {
      "items": {"type": "string"},
      "maxItems": 4,
      "type": "array"
    }
  },
  "type": "object"
}
```

This ensures the subagent's output validates against the schema before being returned.