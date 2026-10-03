from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
from config import LabConfig, load_config
from memory_store import estimate_tokens, extract_profile_updates, merge_facts
from model_provider import build_chat_model
from response_engine import SYSTEM_PROMPT, UsageLedger, live_response, offline_response, prompt_tokens

@dataclass
class SessionState:
    messages: list[dict[str, str]] = field(default_factory=list)
    token_usage: int = 0
    prompt_tokens_processed: int = 0

class BaselineAgent:
    """Short-term only. User and thread form the isolation boundary."""
    def __init__(self, config: LabConfig | None = None, force_offline: bool = False):
        self.config = config or load_config()
        self.force_offline = force_offline
        self.sessions = {}
        self.thread_owners = {}
        self.usage_ledger = UsageLedger(self.config.api_log_path)
        self.langchain_agent = self._maybe_build_langchain_agent()

    def _claim_thread(self, user_id, thread_id):
        owner = self.thread_owners.setdefault(thread_id, user_id)
        if owner != user_id:
            raise ValueError('A thread cannot be shared across users')

    def reply(self, user_id: str, thread_id: str, message: str) -> dict[str, Any]:
        self._claim_thread(user_id, thread_id)
        return self._reply_offline(thread_id, message)

    def _reply_offline(self, thread_id: str, message: str) -> dict[str, Any]:
        session = self.sessions.setdefault(thread_id, SessionState())
        session.messages.append({'role': 'user', 'content': message})
        prompt = [{'role': 'system', 'content': SYSTEM_PROMPT}] + session.messages
        load = prompt_tokens(prompt)
        facts = {}
        for item in session.messages:
            if item['role'] == 'user':
                merge_facts(facts, extract_profile_updates(item['content']))
        tags = {'agent': 'Baseline', 'provider': self.config.model.provider, 'model': self.config.model.model_name,
                'thread_id': thread_id, 'user_id': self.thread_owners.get(thread_id)}
        answer = live_response(self.langchain_agent, prompt, self.usage_ledger, tags) if self.langchain_agent else offline_response(facts, message)
        output_tokens = estimate_tokens(answer)
        session.messages.append({'role': 'assistant', 'content': answer})
        session.token_usage += output_tokens
        session.prompt_tokens_processed += load
        return {'response': answer, 'agent_tokens': output_tokens, 'prompt_tokens': load,
                'mode': 'live' if self.langchain_agent else 'offline', 'token_method': 'chars/4 estimate'}

    def token_usage(self, thread_id: str) -> int:
        return self.sessions.get(thread_id, SessionState()).token_usage

    def prompt_token_usage(self, thread_id: str) -> int:
        return self.sessions.get(thread_id, SessionState()).prompt_tokens_processed

    def compaction_count(self, thread_id: str) -> int:
        return 0

    def _maybe_build_langchain_agent(self):
        return None if self.force_offline or self.config.offline else build_chat_model(self.config.model)
