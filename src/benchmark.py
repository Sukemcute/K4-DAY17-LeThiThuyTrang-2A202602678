"""Fresh-state, same-input benchmarks. Offline scores are transparent proxies."""
from __future__ import annotations
import argparse
import json
import tempfile
import unicodedata
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any
from agent_advanced import AdvancedAgent
from agent_baseline import BaselineAgent
from config import load_config, provider_from_env

@dataclass
class BenchmarkRow:
    agent_name: str
    agent_tokens_only: int
    prompt_tokens_processed: int
    recall_score: float
    response_quality: float
    memory_growth_bytes: int
    compactions: int

def load_conversations(path: Path) -> list[dict[str, Any]]:
    conversations = json.loads(path.read_text(encoding='utf-8-sig'))
    if not isinstance(conversations, list) or not conversations:
        raise ValueError('Dataset must be a non-empty conversation list')
    for conv in conversations:
        if not all(key in conv for key in ('id', 'user_id', 'turns', 'recall_questions')):
            raise ValueError('Missing conversation field')
        if not all(isinstance(turn, str) for turn in conv['turns']):
            raise ValueError('Turns must be strings')
    return conversations

def normalized(text: str) -> str:
    return unicodedata.normalize('NFC', text).casefold()

def recall_points(answer: str, expected: list[str]) -> float:
    if not expected:
        return 1.0
    matches = sum(normalized(item) in normalized(answer) for item in expected)
    return 1.0 if matches == len(expected) else .5 if matches else 0.0

def heuristic_quality(answer: str, expected: list[str]) -> float:
    """0..1 proxy: 80% fact coverage + 20% brevity; zero for zero coverage.

    This is not an independent LLM judge or a measure of reasoning ability.
    """
    coverage = recall_points(answer, expected)
    if not answer.strip() or coverage == 0:
        return 0.0
    brevity = min(1.0, 400 / max(1, len(answer)))
    return coverage * (.8 + .2 * brevity)

def run_agent_benchmark(agent_name: str, agent, conversations: list[dict[str, Any]], config) -> BenchmarkRow:
    users = {conv['user_id'] for conv in conversations}
    initial_bytes = sum(agent.memory_file_size(user) for user in users) if hasattr(agent, 'memory_file_size') else 0
    threads, details = [], []
    for index, conv in enumerate(conversations):
        if not config.offline:
            print(f'{agent_name}: conversation {index + 1}/{len(conversations)} ({conv["id"]})', flush=True)
        thread = f'train:{index}:{conv["id"]}'
        threads.append(thread)
        for turn in conv['turns']:
            agent.reply(conv['user_id'], thread, turn)
        # Test immediately after each conversation, so future corrections cannot leak backwards.
        for question_index, question in enumerate(conv['recall_questions']):
            recall_thread = f'recall:{index}:{question_index}:{conv["id"]}'
            threads.append(recall_thread)
            answer = agent.reply(conv['user_id'], recall_thread, question['question'])['response']
            details.append({'conversation': conv['id'], 'thread': recall_thread,
                            'question': question['question'], 'expected': question['expected_contains'],
                            'answer': answer, 'recall': recall_points(answer, question['expected_contains']),
                            'quality_proxy': heuristic_quality(answer, question['expected_contains'])})
    agent.benchmark_details = details
    agent.benchmark_usage = agent.usage_ledger.totals()
    growth = sum(agent.memory_file_size(user) for user in users) - initial_bytes if hasattr(agent, 'memory_file_size') else 0
    return BenchmarkRow(agent_name, sum(agent.token_usage(t) for t in threads),
                        sum(agent.prompt_token_usage(t) for t in threads),
                        sum(d['recall'] for d in details) / max(1, len(details)),
                        sum(d['quality_proxy'] for d in details) / max(1, len(details)), growth,
                        sum(agent.compaction_count(t) for t in threads))

def format_rows(rows: list[BenchmarkRow]) -> str:
    header = '| Agent | Agent tokens only | Prompt tokens processed | Cross-session recall | Response quality | Memory growth (bytes) | Compactions |'
    lines = [header, '|---|---:|---:|---:|---:|---:|---:|']
    for r in rows:
        lines.append(f'| {r.agent_name} | {r.agent_tokens_only} | {r.prompt_tokens_processed} | {r.recall_score:.1%} | {r.response_quality:.1%} | {r.memory_growth_bytes} | {r.compactions} |')
    return '\n'.join(lines)

def run_suite(config, dataset, live=False, include_ablation=True):
    rows, details, profiles, summary_work = [], {}, {}, {}
    variants = [('Baseline', BaselineAgent, {}), ('Advanced', AdvancedAgent, {}),
                ('Advanced without compact', AdvancedAgent, {'compact_threshold_tokens': 10**9}),
                ('Advanced strict confidence', AdvancedAgent, {'profile_confidence_threshold': 1.0})]
    if not include_ablation:
        variants = variants[:2]
    for name, cls, overrides in variants:
        with tempfile.TemporaryDirectory(prefix='memory-lab-') as directory:
            isolated = replace(config, state_dir=Path(directory), offline=not live, **overrides)
            agent = cls(isolated, force_offline=not live)
            rows.append(run_agent_benchmark(name, agent, dataset, isolated))
            if live:
                print(f'{name} finished: recall {rows[-1].recall_score:.1%}; usage {agent.benchmark_usage}', flush=True)
            details[name] = agent.benchmark_details
            summary_work.setdefault('_actual_usage', {})[name] = agent.benchmark_usage
            if hasattr(agent, 'compact_memory'):
                summary_work[name] = sum(state['summary_chars_processed'] for state in agent.compact_memory.state.values())
            if name == 'Advanced':
                profiles = {user: agent.profile_store.read_text(user) for user in {c['user_id'] for c in dataset}}
    return rows, details, profiles, summary_work

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live', action='store_true', help='Explicitly call configured paid/local LLM; never silently fall back')
    parser.add_argument('--no-ablation', action='store_true', help='Compare only Baseline and Advanced')
    parser.add_argument('--ablation', action='store_true', help='Include two additional memory-control experiments')
    parser.add_argument('--provider', choices=['openai', 'custom', 'gemini', 'anthropic', 'ollama', 'openrouter'])
    parser.add_argument('--model', help='Override model for the selected provider')
    parser.add_argument('--store', action='store_true', help='Store OpenAI Chat Completions for dashboard inspection')
    parser.add_argument('--suite', choices=['all', 'standard', 'stress'], default='all')
    parser.add_argument('--output-dir', type=Path, default=Path(__file__).resolve().parent.parent / 'results')
    args = parser.parse_args()
    config = load_config()
    if args.provider or args.model:
        config.model = provider_from_env(args.provider or config.model.provider, args.model, explicit_selection=bool(args.provider))
    config.model.store = args.store or config.model.store
    args.output_dir.mkdir(parents=True, exist_ok=True)
    if args.live:
        config.api_log_path = args.output_dir / 'api-calls.jsonl'
        if config.api_log_path.exists():
            parser.error('This output directory already contains API calls. Choose a fresh --output-dir to preserve evidence.')
    report = {'mode': 'live' if args.live else 'offline', 'token_method': 'ceil(stripped characters / 4) + 4 per message',
              'quality_method': 'three-level recall * (0.8 + 0.2 * min(1, 400/answer_chars)); not an LLM judge',
              'recall_method': '0 = no matches; 0.5 = some matches; 1 = all matches; macro average over questions',
              'provider': config.model.provider, 'model': config.model.model_name,
              'openai_store': config.model.store, 'ablation_included': args.ablation and not args.no_ablation,
              'summary_cost': 'Offline extractive CPU work; no LLM tokens. Report chars separately.', 'suites': {}}
    markdown = ['# Benchmark results', '', f'Mode: {report["mode"]}. Token counts are estimates, not billing usage. Quality is a heuristic proxy.', '']
    for title, filename in [('Standard Benchmark', 'conversations.json'), ('Long-Context Stress Benchmark', 'advanced_long_context.json')]:
        if args.suite == 'standard' and filename != 'conversations.json' or args.suite == 'stress' and filename != 'advanced_long_context.json':
            continue
        print(f'Running {title}...', flush=True)
        rows, details, profiles, work = run_suite(config, load_conversations(config.data_dir / filename), args.live,
                                                   include_ablation=args.ablation and not args.no_ablation)
        actual_usage = work.pop('_actual_usage', {})
        report['suites'][title] = {'rows': [asdict(row) for row in rows], 'recall_details': details,
                                  'summary_chars_processed': work, 'actual_api_usage': actual_usage}
        table = format_rows(rows)
        print(f'\n{title}\n{table}')
        markdown.extend([f'## {title}', '', table, ''])
        if args.live:
            markdown.extend(['### Actual API usage (provider-reported)', '',
                             '| Agent | Calls | Input tokens | Output tokens | Total tokens | Calls missing usage |',
                             '|---|---:|---:|---:|---:|---:|'])
            for name, usage in actual_usage.items():
                markdown.append(f'| {name} | {usage["calls"]} | {usage["input_tokens"]} | {usage["output_tokens"]} | {usage["total_tokens"]} | {usage["calls_with_missing_usage"]} |')
            markdown.append('')
        for user, profile in profiles.items():
            (args.output_dir / f'{user}-User.md').write_text(profile, encoding='utf-8')
        # Save completed suites incrementally; API-call JSONL survives a later API failure.
        (args.output_dir / 'benchmark.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        (args.output_dir / 'benchmark.md').write_text('\n'.join(markdown), encoding='utf-8')
    (args.output_dir / 'benchmark.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (args.output_dir / 'benchmark.md').write_text('\n'.join(markdown), encoding='utf-8')
    print(f'\nSaved results to {args.output_dir}')

if __name__ == '__main__':
    main()
