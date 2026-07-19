# DeepSeek Usage Data Analysis Pattern

## How to Extract and Analyze DeepSeek CSV Exports

Bane periodically exports DeepSeek API usage data as ZIP files containing two CSVs:
- `cost-*.csv` — daily cost per model (`utc_date, model, wallet_type, cost, currency`)
- `amount-*.csv` — detailed token breakdown per API key (`utc_date, model, api_key_name, type, price, amount`)

### Extraction

```bash
unzip -o usage_data_*.zip -d /tmp/usage-analysis/
```

### Analysis Script Template

```python
import csv
from collections import defaultdict

# Read cost data
costs = []
with open('/tmp/usage-analysis/cost-*.csv') as f:
    for row in csv.DictReader(f):
        costs.append(row)

# Read amount (detailed token) data
amounts = []
with open('/tmp/usage-analysis/amount-*.csv') as f:
    for row in csv.DictReader(f):
        amounts.append(row)

# Cost by day and model
daily_cost = defaultdict(lambda: defaultdict(float))
total_cost = 0
for row in costs:
    day = row['utc_date']
    model = row['model']
    cost = float(row['cost'])
    daily_cost[day][model] += cost
    total_cost += cost

# Token breakdown by model
token_data = defaultdict(lambda: {'cache_hit': 0, 'cache_miss': 0, 'output': 0, 'requests': 0})
for row in amounts:
    model = row['model']
    typ = row['type']
    amt = int(row['amount']) if row['amount'] else 0
    if typ == 'input_cache_hit_tokens':
        token_data[model]['cache_hit'] += amt
    elif typ == 'input_cache_miss_tokens':
        token_data[model]['cache_miss'] += amt
    elif typ == 'output_tokens':
        token_data[model]['output'] += amt
    elif typ == 'request_count':
        token_data[model]['requests'] += amt

# Cache hit rate
for model, d in token_data.items():
    total_input = d['cache_hit'] + d['cache_miss']
    hit_rate = (d['cache_hit'] / total_input * 100) if total_input > 0 else 0
    print(f"{model}: {hit_rate:.2f}% cache hit, {d['requests']:,} requests")

# By API key
key_tokens = defaultdict(lambda: defaultdict(int))
for row in amounts:
    key = row['api_key_name'] if row['api_key_name'] else 'unknown'
    typ = row['type']
    amt = int(row['amount']) if row['amount'] else 0
    if typ in ('input_cache_hit_tokens', 'input_cache_miss_tokens', 'output_tokens'):
        key_tokens[key][typ] += amt
    elif typ == 'request_count':
        key_tokens[key]['requests'] += amt
```

## Key Metrics to Report

1. **Total cost + daily average** — monthly projection
2. **Daily spend trend** — are costs going up or down?
3. **Cache hit rate per model** — the single most important metric for DeepSeek economics
4. **Cache hit rate per API key** — which workloads are cache-friendly vs cache-hostile?
5. **Comparison to previous period** — is optimization working?
6. **Top API keys** — who's driving spend?

## Cache Economics (DeepSeek Pricing)

| Model | Cache HIT $/M | Cache MISS $/M | Output $/M |
|-------|--------------|----------------|------------|
| v4-pro | $0.003625 | $0.435 | $0.87 |
| v4-flash | $0.0028 | $0.14 | $0.28 |

Cache hits are **120× cheaper** than cache misses. A 1% improvement in cache hit rate at scale saves dollars, not cents.

## Historical Baselines

| Period | Days | Total | Daily | Cache (v4-pro) | Cache (v4-flash) |
|--------|------|-------|-------|-----------------|-------------------|
| Jun 1-9, 2026 | 9 | $155.31 | $17.26 | 89.0% | — |
| Jun 14-Jul 13, 2026 | 30 | $430.26 | $14.34 | 96.72% | 96.88% |

Trend: costs down 17% despite 3× longer period. Cache improvement from 89% → 96.7% saved ~$285 over the 30-day window.
