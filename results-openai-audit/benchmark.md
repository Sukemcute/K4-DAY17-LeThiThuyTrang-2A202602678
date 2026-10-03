# Benchmark results

Mode: live. Token counts are estimates, not billing usage. Quality is a heuristic proxy.

## Standard Benchmark

| Agent | Agent tokens only | Prompt tokens processed | Cross-session recall | Response quality | Memory growth (bytes) | Compactions |
|---|---:|---:|---:|---:|---:|---:|
| Baseline | 6503 | 44801 | 10.7% | 10.7% | 0 | 0 |
| Advanced | 11987 | 67412 | 100.0% | 100.0% | 1499 | 8 |

### Actual API usage (provider-reported)

| Agent | Calls | Input tokens | Output tokens | Total tokens | Calls missing usage |
|---|---:|---:|---:|---:|---:|
| Baseline | 115 | 48858 | 7225 | 56083 | 0 |
| Advanced | 115 | 78463 | 14179 | 92642 | 0 |

## Long-Context Stress Benchmark

| Agent | Agent tokens only | Prompt tokens processed | Cross-session recall | Response quality | Memory growth (bytes) | Compactions |
|---|---:|---:|---:|---:|---:|---:|
| Baseline | 3344 | 45734 | 0.0% | 0.0% | 0 | 0 |
| Advanced | 3207 | 17920 | 100.0% | 100.0% | 1360 | 15 |

### Actual API usage (provider-reported)

| Agent | Calls | Input tokens | Output tokens | Total tokens | Calls missing usage |
|---|---:|---:|---:|---:|---:|
| Baseline | 19 | 49247 | 3634 | 52881 | 0 |
| Advanced | 19 | 20279 | 3777 | 24056 | 0 |
