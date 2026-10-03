# Benchmark results

Mode: offline. Token counts are estimates, not billing usage. Quality is a heuristic proxy.

## Standard Benchmark

| Agent | Agent tokens only | Prompt tokens processed | Cross-session recall | Response quality | Memory growth (bytes) | Compactions |
|---|---:|---:|---:|---:|---:|---:|
| Baseline | 1349 | 24185 | 0.0% | 0.0% | 0 | 0 |
| Advanced | 1350 | 32966 | 100.0% | 100.0% | 1499 | 0 |

## Long-Context Stress Benchmark

| Agent | Agent tokens only | Prompt tokens processed | Cross-session recall | Response quality | Memory growth (bytes) | Compactions |
|---|---:|---:|---:|---:|---:|---:|
| Baseline | 305 | 24248 | 0.0% | 0.0% | 0 | 0 |
| Advanced | 340 | 14494 | 100.0% | 100.0% | 1360 | 3 |
