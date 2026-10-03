"""Lazy provider adapters; offline execution does not import SDKs."""
from dataclasses import dataclass, field
from importlib import import_module

@dataclass
class ProviderConfig:
    provider: str = 'openai'
    model_name: str = 'gpt-4o-mini'
    temperature: float = 0.0
    api_key: str | None = field(default=None, repr=False)
    base_url: str | None = None
    store: bool = False

def normalize_provider(value: str) -> str:
    value = value.strip().lower().replace('-', '_')
    value = {'anthorpic': 'anthropic', 'google': 'gemini', 'google_genai': 'gemini', 'openai_compatible': 'custom'}.get(value, value)
    if value not in {'openai', 'custom', 'gemini', 'anthropic', 'ollama', 'openrouter'}:
        raise ValueError(f'Unsupported provider: {value}')
    return value

def build_chat_model(config: ProviderConfig):
    provider = normalize_provider(config.provider)
    if provider != 'ollama' and not config.api_key:
        raise ValueError(f'Missing API key for {provider}; configure .env or use offline mode')
    if provider == 'custom' and not config.base_url:
        raise ValueError('CUSTOM_BASE_URL is required')
    adapters = {'openai': ('langchain_openai', 'ChatOpenAI'), 'custom': ('langchain_openai', 'ChatOpenAI'),
                'gemini': ('langchain_google_genai', 'ChatGoogleGenerativeAI'), 'anthropic': ('langchain_anthropic', 'ChatAnthropic'),
                'ollama': ('langchain_ollama', 'ChatOllama'), 'openrouter': ('langchain_openrouter', 'ChatOpenRouter')}
    module, name = adapters[provider]
    try:
        cls = getattr(import_module(module), name)
    except ImportError as exc:
        raise RuntimeError(f'Install {module.replace("_", "-")} for live mode') from exc
    kwargs = {'model': config.model_name, 'temperature': config.temperature}
    if config.api_key and provider != 'ollama':
        kwargs['api_key'] = config.api_key
    if config.base_url:
        if provider == 'gemini' and 'base_url' not in getattr(cls, 'model_fields', {}):
            kwargs['client_options'] = {'api_endpoint': config.base_url}
        else:
            kwargs['base_url'] = config.base_url
    if provider == 'openai' and config.store:
        kwargs['store'] = True
        kwargs['metadata'] = {'lab': 'day17-memory', 'purpose': 'benchmark'}
    return cls(**kwargs)
