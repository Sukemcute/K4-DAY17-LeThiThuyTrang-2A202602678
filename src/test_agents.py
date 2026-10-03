"""Behavioral tests: independent values, adversarial corrections and fair accounting."""
from dataclasses import replace
import json
from pathlib import Path
from types import SimpleNamespace
import pytest
from agent_advanced import AdvancedAgent
from agent_baseline import BaselineAgent
from benchmark import load_conversations, recall_points, run_agent_benchmark, run_suite
from config import LabConfig, load_config
from memory_store import CompactMemoryManager, UserProfileStore, estimate_tokens, extract_profile_candidates, extract_profile_updates
from model_provider import ProviderConfig, build_chat_model, normalize_provider
from response_engine import prompt_tokens

ROOT = Path(__file__).resolve().parent.parent

def make_config(tmp_path: Path):
    # No inherited environment/.env; test fixtures are deterministic.
    return LabConfig(ROOT, ROOT / 'data', tmp_path / 'state', 160, 2,
                     ProviderConfig(), ProviderConfig(), summary_max_chars=400)

def test_user_markdown_read_write_edit(tmp_path):
    store = UserProfileStore(tmp_path)
    assert store.read_text('trang') == ''
    path = store.write_text('trang', '# Trang\nNơi ở: Huế\n')
    assert path.name == 'User.md'
    assert store.edit_text('trang', 'Huế', 'Hải Phòng')
    assert not store.edit_text('trang', 'Hà Nội', 'Huế')
    assert 'Hải Phòng' in store.read_text('trang')
    assert store.file_size('trang') == len(store.read_text('trang').encode('utf-8'))
    with pytest.raises(ValueError):
        store.edit_text('trang', '', 'x')

def test_profile_paths_are_contained_and_distinct(tmp_path):
    store = UserProfileStore(tmp_path)
    for user in ['../../escape', '../escape', 'CON', 'a/b', 'a?b', '张三', 'Trang']:
        assert store.write_text(user, user).resolve().is_relative_to(tmp_path.resolve())
    assert store.path_for('a/b') != store.path_for('a?b')
    with pytest.raises(ValueError):
        store.path_for('')

def test_compact_trigger(tmp_path):
    memory = CompactMemoryManager(100, 2, 300)
    for n in range(10):
        memory.append('t', 'user', f'Tin {n}: mục tiêu triển khai pipeline. ' + 'Dữ liệu dài. ' * 30)
    state = memory.context('t')
    assert state['compactions'] > 1
    assert len(state['messages']) == 2
    assert 0 < len(state['summary']) <= 100
    assert state['messages'][-1]['content'].startswith('Tin 9:')
    state['messages'].clear()
    assert memory.context('t')['messages']  # Caller cannot mutate internal state.
    assert memory.context('other')['summary'] == ''

def test_cross_session_recall(tmp_path):
    config = make_config(tmp_path)
    advanced, baseline = AdvancedAgent(config, True), BaselineAgent(config, True)
    for agent in [advanced, baseline]:
        agent.reply('trang', 'first', 'Mình tên là Trang. Mình sống ở Hải Phòng. Mình đang làm data engineer.')
        assert 'Trang' in agent.reply('trang', 'first', 'Mình tên gì?')['response']
    question = 'Tên, nơi ở hiện tại và nghề nghiệp hiện tại của mình là gì?'
    answer = advanced.reply('trang', 'second', question)['response']
    assert all(value in answer for value in ['Trang', 'Hải Phòng', 'data engineer'])
    assert 'Trang' not in baseline.reply('trang', 'second', question)['response']
    restarted = AdvancedAgent(config, True)
    assert 'Trang' in restarted.reply('trang', 'third', 'Mình tên gì?')['response']

def test_compact_reduces_prompt_load_on_long_thread(tmp_path):
    config = make_config(tmp_path)
    compact = AdvancedAgent(config, True)
    full = AdvancedAgent(replace(config, state_dir=tmp_path / 'full', compact_threshold_tokens=10**9), True)
    baseline = BaselineAgent(config, True)
    for agent in [compact, full, baseline]:
        agent.reply('u', 't', 'Mình tên là Linh. Mình sống ở Cần Thơ.')
        for n in range(25):
            agent.reply('u', 't', f'Bản ghi {n}. ' + 'Nội dung vận hành hệ thống. ' * 50)
        assert ('Linh' in agent.reply('u', 'fresh', 'Mình tên gì?')['response']) == (agent is not baseline)
    assert compact.prompt_token_usage('t') < full.prompt_token_usage('t') * .5
    assert compact.prompt_token_usage('t') < baseline.prompt_token_usage('t') * .5
    assert compact.compaction_count('t') > 1
    assert full.compaction_count('t') == 0

@pytest.mark.parametrize('message', [
    'Mình tên gì?', 'Mình đang ở Hà Nội phải không?', 'Bạn có biết DũngCT không?',
    'Nếu mình ở Hà Nội thì sao?', 'Mình đùa là chuyển sang product manager.',
    'Mình không còn làm backend engineer nữa.', 'Hà Nội chỉ là nơi mình bay ra họp.',
    'Nếu sau này mình nhắc lại Huế như ví dụ cũ thì đừng lưu nhé.',
    'Tạm thời trong phiên này mình thích Python và AI.',
    'Lan đang làm product manager.',
    'Trích dẫn: mình tên là Người Khác.',
])
def test_questions_noise_and_negations_are_not_facts(message):
    assert extract_profile_updates(message) == {}

def test_corrections_and_transient_workplace(tmp_path):
    agent = AdvancedAgent(make_config(tmp_path), True)
    agent.reply('u', 'a', 'Mình sống ở Cần Thơ. Mình đang làm backend engineer.')
    agent.reply('u', 'a', 'Mình không còn làm backend engineer nữa, giờ chuyển sang data engineer.')
    agent.reply('u', 'a', 'Giờ mình đang ở Hải Phòng chứ không còn ở Cần Thơ nữa.')
    agent.reply('u', 'a', 'Hôm nay mình làm việc ở quán cà phê gần bến cảng.')
    agent.reply('u', 'a', 'Mình đùa là chuyển sang product manager. Hà Nội chỉ là nơi đi họp.')
    agent.reply('u', 'fresh', 'Nếu ai đó nhắc Cần Thơ hay product manager, nghề và nơi ở hiện tại là gì?')
    facts = agent.profile_store.facts('u')
    assert facts['location'] == 'Hải Phòng'
    assert facts['profession'] == 'data engineer'
    assert agent.profile_store.records('u')['location']['revision'] == 2


def test_confidence_filter_and_idempotent_storage(tmp_path):
    store = UserProfileStore(tmp_path)
    assert not store.upsert_fact('u', 'location', 'Huế', confidence=.6)
    assert store.file_size('u') == 0
    assert store.upsert_fact('u', 'name', 'An', confidence=.95)
    original = store.read_text('u')
    for _ in range(100):
        assert not store.upsert_fact('u', 'name', 'An')
    assert store.read_text('u') == original
    assert store.records('u')['name']['confidence'] == .95
    candidate = extract_profile_candidates('Hôm nay mình làm việc ở quán cà phê.')['location']
    assert candidate.confidence < .85


def test_style_facets_are_merged_and_rendered(tmp_path):
    agent = AdvancedAgent(make_config(tmp_path), True)
    agent.reply('u', 'a', 'Mình tên là Mai. Mình muốn bạn trả lời ngắn gọn thành 3 bullet.')
    agent.reply('u', 'a', 'Mình thích cách giải thích có ví dụ thực chiến và so sánh trade-off.')
    style = agent.profile_store.facts('u')['response_style']
    assert all(value in style for value in ['ngắn gọn', '3 bullet', 'ví dụ thực chiến', 'trade-off'])
    answer = agent.reply('u', 'b', 'Tên và style trả lời mình thích là gì?')['response']
    assert len(answer.splitlines()) == 3
    assert all(line.startswith('- ') for line in answer.splitlines())

@pytest.mark.parametrize('cls', [BaselineAgent, AdvancedAgent])
def test_user_isolation(cls, tmp_path):
    agent = cls(make_config(tmp_path), True)
    agent.reply('alice', 'a', 'Mình tên là Alice.')
    with pytest.raises(ValueError):
        agent.reply('bob', 'a', 'Mình tên gì?')
    assert 'Alice' not in agent.reply('bob', 'b', 'Mình tên gì?')['response']

@pytest.mark.parametrize('cls', [BaselineAgent, AdvancedAgent])
def test_token_accounting(cls, tmp_path):
    agent = cls(make_config(tmp_path), True)
    results = [agent.reply('u', 'a', message) for message in ['Mình tên là Hoa.', 'Mình tên gì?']]
    assert agent.token_usage('a') == sum(r['agent_tokens'] for r in results)
    assert agent.prompt_token_usage('a') == sum(r['prompt_tokens'] for r in results)
    assert all(r['agent_tokens'] == estimate_tokens(r['response']) for r in results)
    assert agent.token_usage('unknown') == 0
    assert agent.prompt_token_usage('unknown') == 0


def test_recall_unicode_and_partial_score():
    assert recall_points('HUE\u0302\u0301', ['Huế']) == 1
    assert recall_points('Python', ['Python', 'AI', 'Rust']) == .5
    assert recall_points('Chưa biết.', ['Python']) == 0
    assert estimate_tokens('   ') == 0
    assert estimate_tokens('abcde') == 2


def test_official_suites_and_ablation(tmp_path):
    config = replace(make_config(tmp_path), compact_threshold_tokens=1200, compact_keep_messages=4, summary_max_chars=1600)
    for filename in ['conversations.json', 'advanced_long_context.json']:
        rows, details, profiles, work = run_suite(config, load_conversations(ROOT / 'data' / filename))
        baseline, advanced, full, strict = rows
        assert baseline.recall_score == 0
        assert advanced.recall_score == full.recall_score == 1
        assert strict.recall_score == 0
        assert all('recall:' in d['thread'] for d in details['Advanced'])
        assert profiles
        if filename.startswith('advanced'):
            assert advanced.compactions > 1
            assert advanced.prompt_tokens_processed < baseline.prompt_tokens_processed
            assert advanced.prompt_tokens_processed < full.prompt_tokens_processed
            assert work['Advanced'] > 0
        else:
            assert advanced.prompt_tokens_processed > baseline.prompt_tokens_processed
    # Re-run on isolated storage and compare exact results, no warm-profile contamination.
    one = run_suite(config, load_conversations(ROOT / 'data' / 'conversations.json'))
    two = run_suite(config, load_conversations(ROOT / 'data' / 'conversations.json'))
    assert one == two

@pytest.mark.parametrize('provider,module,cls_name', [
    ('openai', 'langchain_openai', 'ChatOpenAI'), ('custom', 'langchain_openai', 'ChatOpenAI'),
    ('gemini', 'langchain_google_genai', 'ChatGoogleGenerativeAI'), ('anthropic', 'langchain_anthropic', 'ChatAnthropic'),
    ('ollama', 'langchain_ollama', 'ChatOllama'), ('openrouter', 'langchain_openrouter', 'ChatOpenRouter'),
])
def test_provider_wiring_without_network(monkeypatch, provider, module, cls_name):
    import model_provider
    seen = {}
    class FakeModel:
        def __init__(self, **kwargs):
            seen.update(kwargs)
    def fake_import(name):
        assert name == module
        return SimpleNamespace(**{cls_name: FakeModel})
    monkeypatch.setattr(model_provider, 'import_module', fake_import)
    config = ProviderConfig(provider, 'test-model', .2, 'test-key', 'http://localhost/v1')
    build_chat_model(config)
    expected = {'model': 'test-model', 'temperature': .2}
    if provider != 'ollama':
        expected['api_key'] = 'test-key'
    expected['client_options' if provider == 'gemini' else 'base_url'] = {'api_endpoint': 'http://localhost/v1'} if provider == 'gemini' else 'http://localhost/v1'
    assert seen == expected
    assert 'test-key' not in repr(config)

@pytest.mark.parametrize('cls', [BaselineAgent, AdvancedAgent])
def test_live_path_uses_actual_memory_prompt(tmp_path, monkeypatch, cls):
    import agent_baseline
    import agent_advanced
    calls = []
    class FakeModel:
        def invoke(self, messages):
            calls.append(messages)
            return SimpleNamespace(content='Câu trả lời từ model.')
    monkeypatch.setattr(agent_baseline, 'build_chat_model', lambda config: FakeModel())
    monkeypatch.setattr(agent_advanced, 'build_chat_model', lambda config: FakeModel())
    agent = cls(replace(make_config(tmp_path), offline=False))
    agent.reply('u', 'a', 'Mình tên là Hạnh.')
    result = agent.reply('u', 'b', 'Mình tên gì?')
    assert result['mode'] == 'live'
    assert result['response'] == 'Câu trả lời từ model.'
    joined = '\n'.join(m['content'] for m in calls[-1])
    assert ('Hạnh' in joined) == (cls is AdvancedAgent)
    assert result['prompt_tokens'] == prompt_tokens(calls[-1])


def test_provider_errors_are_explicit():
    assert normalize_provider(' Anthorpic ') == 'anthropic'
    with pytest.raises(ValueError):
        normalize_provider('unknown')
    with pytest.raises(ValueError, match='Missing API key'):
        build_chat_model(ProviderConfig())
    with pytest.raises(ValueError, match='BASE_URL'):
        build_chat_model(ProviderConfig('custom', api_key='test-key'))


def test_benchmark_without_ablation(tmp_path):
    dataset = [{'id': 'small', 'user_id': 'u', 'turns': ['Mình tên là An.'],
                'recall_questions': [{'question': 'Mình tên gì?', 'expected_contains': ['An']}]}]
    rows, details, profiles, work = run_suite(make_config(tmp_path), dataset, include_ablation=False)
    assert [row.agent_name for row in rows] == ['Baseline', 'Advanced']
    assert rows[1].recall_score == 1
    assert set(details) == {'Baseline', 'Advanced'}


def test_config_environment(tmp_path, monkeypatch):
    for key in ['LLM_PROVIDER', 'LLM_MODEL', 'LLM_API_KEY', 'GEMINI_API_KEY', 'JUDGE_PROVIDER', 'JUDGE_MODEL',
                'COMPACT_THRESHOLD_TOKENS', 'COMPACT_KEEP_MESSAGES', 'PROFILE_CONFIDENCE_THRESHOLD', 'SUMMARY_MAX_CHARS', 'LAB_OFFLINE']:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv('LLM_PROVIDER', 'google')
    monkeypatch.setenv('GEMINI_API_KEY', 'dummy')
    monkeypatch.setenv('COMPACT_THRESHOLD_TOKENS', '222')
    config = load_config(tmp_path)
    assert config.model.provider == config.judge_model.provider == 'gemini'
    assert config.model.api_key == 'dummy'
    assert config.compact_threshold_tokens == 222
    assert config.state_dir.exists() and config.offline
    monkeypatch.setenv('COMPACT_KEEP_MESSAGES', '0')
    with pytest.raises(ValueError):
        load_config(tmp_path)

@pytest.mark.parametrize('provider,module', [
    ('openai','langchain_openai'), ('custom','langchain_openai'),
    ('gemini','langchain_google_genai'), ('anthropic','langchain_anthropic'),
    ('ollama','langchain_ollama'), ('openrouter','langchain_openrouter'),
])
def test_real_sdk_constructor_without_api_calls(provider, module):
    pytest.importorskip(module)
    model = build_chat_model(ProviderConfig(provider, 'test-model', api_key='dummy',
                                            base_url='http://localhost/v1' if provider == 'custom' else None))
    assert callable(model.invoke)


def test_provider_selection_does_not_reuse_other_provider_credentials(monkeypatch):
    from config import provider_from_env
    monkeypatch.setenv('LLM_PROVIDER', 'openai')
    monkeypatch.setenv('LLM_MODEL', 'openai-model')
    monkeypatch.setenv('LLM_API_KEY', 'openai-dummy')
    monkeypatch.setenv('OPENROUTER_API_KEY', 'router-dummy')
    monkeypatch.delenv('OPENROUTER_MODEL', raising=False)
    router = provider_from_env('openrouter', explicit_selection=True)
    assert router.api_key == 'router-dummy'
    assert router.model_name == 'openai/gpt-4o-mini'
    ollama = provider_from_env('ollama', explicit_selection=True)
    assert ollama.api_key is None


def test_openai_store_and_metadata_are_sent_only_when_enabled(monkeypatch):
    import model_provider
    captured = {}
    class FakeModel:
        def __init__(self, **kwargs):
            captured.update(kwargs)
    monkeypatch.setattr(model_provider, 'import_module', lambda _: SimpleNamespace(ChatOpenAI=FakeModel))
    build_chat_model(ProviderConfig('openai', api_key='dummy', store=True))
    assert captured['store'] is True
    assert captured['metadata']['lab'] == 'day17-memory'


@pytest.mark.parametrize('metadata,usage', [
    ({}, {'input_tokens':10,'output_tokens':3,'total_tokens':13}),
    ({'token_usage':{'prompt_tokens':10,'completion_tokens':3,'total_tokens':13}}, None),
    ({'prompt_eval_count':10,'eval_count':3}, None),
])
def test_usage_ledger_normalization_and_jsonl(tmp_path, metadata, usage):
    from response_engine import UsageLedger, live_response
    result = SimpleNamespace(content='OK', response_metadata=metadata, usage_metadata=usage, id='lc-test')
    model = SimpleNamespace(invoke=lambda messages: result)
    path = tmp_path / 'api-calls.jsonl'
    ledger = UsageLedger(path)
    for _ in range(2):
        assert live_response(model, [{'role':'user','content':'test'}], ledger, {'provider':'test'}) == 'OK'
    totals = ledger.totals()
    assert totals == {'calls':2,'calls_with_missing_usage':0,'input_tokens':20,'output_tokens':6,'total_tokens':26}
    records = [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines()]
    assert len(records) == 2 and records[0]['actual_usage']['total_tokens'] == 13


def test_missing_usage_is_not_claimed_as_zero(tmp_path):
    from response_engine import UsageLedger
    ledger = UsageLedger()
    ledger.record(SimpleNamespace(response_metadata={}), [], 'OK', {})
    assert ledger.calls[0]['actual_usage']['total_tokens'] is None
    assert ledger.totals()['calls_with_missing_usage'] == 1


def test_default_cli_has_exactly_two_rows_per_suite(tmp_path, monkeypatch, capsys):
    from benchmark import main
    import sys
    monkeypatch.setattr(sys, 'argv', ['benchmark.py', '--output-dir', str(tmp_path)])
    main()
    report = json.loads((tmp_path / 'benchmark.json').read_text(encoding='utf-8'))
    assert len(report['suites']) == 2
    assert all([row['agent_name'] for row in suite['rows']] == ['Baseline','Advanced'] for suite in report['suites'].values())
    assert report['recall_method'].startswith('0 =')
