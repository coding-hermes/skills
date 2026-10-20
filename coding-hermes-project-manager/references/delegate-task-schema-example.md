# delegate_task hunter payload — example

The `tasks` argument to `delegate_task` is a JSON array of `{goal, context, output_schema?}` objects — one entry per hunter subagent. Never a bare string, never a non-array. Build it with Python `json.dumps` or `jq -c` and pass the result; hand-written JSON in tool arguments is where schema errors come from. Validate every `output_schema` as Draft 2020-12 before dispatch: the root is an object, each `properties` entry is itself a schema, and array schemas put `type: array` and `items` beside `properties` rather than nesting `type: object` as a property.

Full worked example (project `bunker`, findings lens):

```json
[
  {
    "goal": "Find gaps in the bunker project: look for missing README, missing tests, broken build, missing documentation, outdated dependencies, etc.",
    "context": "Bunker project workdir: ~/bunker. Board: ~/bunker/.coding-hermes/board/tasks.jsonl. Events: ~/bunker/.coding-hermes/board/events.jsonl. README: ~/bunker/README.md. Go.mod: ~/bunker/go.mod. Main package: ./...",
    "output_schema": {
      "type": "object",
      "properties": {
        "findings": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "id_candidate": {"type": "string"},
              "problem": {"type": "string"},
              "how_user_hits_it": {"type": "string"},
              "fix_direction": {"type": "string"},
              "observable_pass_criteria": {"type": "string"}
            },
            "required": ["id_candidate", "problem", "how_user_hits_it", "fix_direction", "observable_pass_criteria"]
          }
        }
      }
    }
  }
]
```

A minimal smoke payload used to probe whether the delegation transport works on an unattended surface: `[{"goal": "t", "context": "t"}]` — if the smoke passes but the real payload fails, the payload is malformed (usually a schema nesting error), not the transport.
