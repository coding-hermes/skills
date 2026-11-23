# Storage: search engines (Elasticsearch, OpenSearch, Vespa class)

## What a complete search-engine spec documents
- Index/mapping definitions: every field's type, analyzer, and why it is indexed vs stored.
- The query set: every query shape the app runs (term, phrase, filtered, aggregations),
  with the expected result-quality metric per query class.
- Ingestion pipeline: source-of-truth sync (CDC? dual-write? reindex), lag budget, and
  what reconciles drift.
- Reindex/zero-downtime story: alias swap, versioned indices, the migration runbook.
- Relevance: how ranking is evaluated (judged set? business metrics?) and who owns tuning.

## The questions the spec must answer
- What is the consistency contract vs the source DB (eventual is fine — name the lag SLO)?
- What is the shard/replica plan at the stated corpus size and QPS?
- Deep pagination: what replaces 'page 10000' (search-after/cursor), and what breaks if ignored?
- What does a mapping change cost (full reindex?) and what is the downtime story?

## Rating checks
- FAIL if the sync mechanism from source-of-truth is unstated (search results go stale forever).
- FAIL if any aggregation/feature is promised without naming its cost class.
- FAIL if there is no reindex/migration runbook — mappings ALWAYS change.
