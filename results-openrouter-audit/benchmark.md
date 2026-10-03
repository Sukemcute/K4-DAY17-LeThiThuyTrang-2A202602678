# Benchmark results

Mode: live. Token counts are estimates, not billing usage. Quality is a heuristic proxy.

## Standard Benchmark

| Agent | Agent tokens only | Prompt tokens processed | Cross-session recall | Response quality | Memory growth (bytes) | Compactions |
|---|---:|---:|---:|---:|---:|---:|
| Baseline | 8098 | 52821 | 10.7% | 10.7% | 0 | 0 |
| Advanced | 12344 | 65896 | 100.0% | 100.0% | 1499 | 9 |

### Actual API usage (provider-reported)

| Agent | Calls | Input tokens | Output tokens | Total tokens | Calls missing usage |
|---|---:|---:|---:|---:|---:|
| Baseline | 115 | 57892 | 9008 | 66900 | 0 |
| Advanced | 115 | 76814 | 14593 | 91407 | 0 |

## Long-Context Stress Benchmark

| Agent | Agent tokens only | Prompt tokens processed | Cross-session recall | Response quality | Memory growth (bytes) | Compactions |
|---|---:|---:|---:|---:|---:|---:|
| Baseline | 3168 | 44430 | 0.0% | 0.0% | 0 | 0 |
| Advanced | 3455 | 18374 | 100.0% | 100.0% | 1360 | 16 |

### Actual API usage (provider-reported)

| Agent | Calls | Input tokens | Output tokens | Total tokens | Calls missing usage |
|---|---:|---:|---:|---:|---:|
| Baseline | 19 | 48203 | 3497 | 51700 | 0 |
| Advanced | 19 | 20603 | 3957 | 24560 | 0 |
