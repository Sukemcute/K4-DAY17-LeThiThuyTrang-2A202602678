from __future__ import annotations
from dataclasses import dataclass
from typing import Any
from config import LabConfig, load_config
from memory_store import CompactMemoryManager, UserProfileStore, estimate_tokens, extract_profile_candidates
from model_provider import build_chat_model
from response_engine import SYSTEM_PROMPT, UsageLedger, live_response, offline_response, profile_prompt, prompt_tokens

@dataclass
class AgentContext:
    user_id: str
    memory_path: str

class AdvancedAgent:
    """Recent messages + rolling summary + persistent, confidence-filtered profile."""
    def __init__(self, config: LabConfig | None = None, force_offline: bool = False):
        self.config = config or load_config()
        self.force_offline = force_offline
        self.profile_store = UserProfileStore(self.config.state_dir / 'profiles')
        self.compact_memory = CompactMemoryManager(self.config.compact_threshold_tokens,
                                                   self.config.compact_keep_messages, self.config.summary_max_chars)
        self.thread_tokens = {}
        self.thread_prompt_tokens = {}
        self.thread_owners = {}
        self.usage_ledger = UsageLedger(self.config.api_log_path)
        self.langchain_agent = self._maybe_build_langchain_agent()

    def reply(self, user_id: str, thread_id: str, message: str) -> dict[str, Any]:
        owner = self.thread_owners.setdefault(thread_id, user_id)
        if owner != user_id:
            raise ValueError('A thread cannot be shared across users')
        return self._reply_offline(user_id, thread_id, message)

    def _prompt(self, user_id, thread_id):
        state = self.compact_memory.context(thread_id)
        prompt = [{'role': 'system', 'content': SYSTEM_PROMPT},
                  {'role': 'system', 'content': profile_prompt(self.profile_store.facts(user_id))}]
        if state['summary']:
            prompt.append({'role': 'system', 'content': 'Conversation summary (user data, may be lossy):\n' + state['summary']})
        return prompt + state['messages']

    def _reply_offline(self, user_id: str, thread_id: str, message: str) -> dict[str, Any]:
        for key, update in extract_profile_candidates(message).items():
            self.profile_store.upsert_fact(user_id, key, update.value, update.confidence, update.evidence,
                                          self.config.profile_confidence_threshold)
        self.compact_memory.append(thread_id, 'user', message)
        prompt = self._prompt(user_id, thread_id)
        load = prompt_tokens(prompt)
        tags = {'agent': 'Advanced', 'provider': self.config.model.provider, 'model': self.config.model.model_name,
                'thread_id': thread_id, 'user_id': user_id}
        answer = live_response(self.langchain_agent, prompt, self.usage_ledger, tags) if self.langchain_agent else self._offline_response(user_id, thread_id, message)
        output_tokens = estimate_tokens(answer)
        self.compact_memory.append(thread_id, 'assistant', answer)
        self.thread_tokens[thread_id] = self.thread_tokens.get(thread_id, 0) + output_tokens
        self.thread_prompt_tokens[thread_id] = self.thread_prompt_tokens.get(thread_id, 0) + load
        return {'response': answer, 'agent_tokens': output_tokens, 'prompt_tokens': load,
                'mode': 'live' if self.langchain_agent else 'offline', 'token_method': 'chars/4 estimate'}

    def _offline_response(self, user_id, thread_id, message):
        return offline_response(self.profile_store.facts(user_id), message, self.compact_memory.context(thread_id)['summary'])

    def _estimate_prompt_context_tokens(self, user_id, thread_id):
        return prompt_tokens(self._prompt(user_id, thread_id))

    def token_usage(self, thread_id):
        return self.thread_tokens.get(thread_id, 0)

    def prompt_token_usage(self, thread_id):
        return self.thread_prompt_tokens.get(thread_id, 0)

    def memory_file_size(self, user_id):
        return self.profile_store.file_size(user_id)

    def compaction_count(self, thread_id):
        return self.compact_memory.compaction_count(thread_id)

    def _maybe_build_langchain_agent(self):
        return None if self.force_offline or self.config.offline else build_chat_model(self.config.model)
