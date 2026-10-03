from __future__ import annotations
import os
from dataclasses import dataclass
from pathlib import Path
from model_provider import ProviderConfig, normalize_provider

@dataclass
class LabConfig:
    base_dir: Path
    data_dir: Path
    state_dir: Path
    compact_threshold_tokens: int
    compact_keep_messages: int
    model: ProviderConfig
    judge_model: ProviderConfig
    offline: bool = True
    profile_confidence_threshold: float = 0.85
    summary_max_chars: int = 1600
    api_log_path: Path | None = None

    def __post_init__(self):
        if self.compact_threshold_tokens <= 0 or self.compact_keep_messages < 1:
            raise ValueError('Compact threshold must be positive; keep_messages >= 1')
        if self.summary_max_chars < 100 or not 0 <= self.profile_confidence_threshold <= 1:
            raise ValueError('Invalid summary cap or confidence threshold')

def load_config(base_dir: Path | None = None) -> LabConfig:
    root = (base_dir or Path(__file__).resolve().parent.parent).resolve()
    try:
        from dotenv import load_dotenv
    except ImportError:
        pass
    else:
        load_dotenv(root / '.env', override=False)
    def provider_config(prefix, fallback=None):
        provider = normalize_provider(os.getenv(f'{prefix}_PROVIDER', fallback.provider if fallback else 'openai'))
        result = provider_from_env(provider, prefix=prefix)
        if fallback and provider == fallback.provider:
            result.model_name = os.getenv(f'{prefix}_MODEL', fallback.model_name)
            result.api_key = result.api_key or fallback.api_key
        return result
    model = provider_config('LLM')
    state = root / 'state'
    state.mkdir(parents=True, exist_ok=True)
    return LabConfig(root, root / 'data', state, int(os.getenv('COMPACT_THRESHOLD_TOKENS', '1200')),
                     int(os.getenv('COMPACT_KEEP_MESSAGES', '4')), model, provider_config('JUDGE', model),
                     offline=os.getenv('LAB_OFFLINE', 'true').lower() not in {'0', 'false', 'no'},
                     profile_confidence_threshold=float(os.getenv('PROFILE_CONFIDENCE_THRESHOLD', '0.85')),
                     summary_max_chars=int(os.getenv('SUMMARY_MAX_CHARS', '1600')))


def provider_from_env(provider: str, model_name: str | None = None, prefix: str = 'LLM',
                      explicit_selection: bool = False) -> ProviderConfig:
    """CLI provider overrides do not accidentally reuse another provider's model/key."""
    provider = normalize_provider(provider)
    defaults = {'openai': 'gpt-4o-mini', 'custom': 'local-model', 'gemini': 'gemini-2.5-flash',
                'anthropic': 'claude-sonnet-4-5', 'ollama': 'llama3.2', 'openrouter': 'openai/gpt-4o-mini'}
    configured = normalize_provider(os.getenv(f'{prefix}_PROVIDER', 'openai'))
    same = not explicit_selection or configured == provider
    key = (os.getenv(f'{prefix}_API_KEY') if same else None) or os.getenv(f'{provider.upper()}_API_KEY')
    if provider == 'gemini':
        key = key or os.getenv('GOOGLE_API_KEY')
    if provider == 'ollama':
        key = None
    name = model_name or (os.getenv(f'{prefix}_MODEL') if same else None) or os.getenv(f'{provider.upper()}_MODEL') or defaults[provider]
    url = (os.getenv(f'{prefix}_BASE_URL') if same else None) or os.getenv(f'{provider.upper()}_BASE_URL')
    return ProviderConfig(provider, name, float(os.getenv(f'{prefix}_TEMPERATURE', '0')), key, url,
                          store=os.getenv('OPENAI_STORE', 'false').lower() in {'1', 'true', 'yes'})
