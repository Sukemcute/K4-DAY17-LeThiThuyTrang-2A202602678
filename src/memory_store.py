"""Deterministic Vietnamese extraction, auditable profiles and bounded compaction."""
from __future__ import annotations
import copy
import hashlib
import json
import math
import re
import tempfile
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

def estimate_tokens(text: str) -> int:
    """Character heuristic, NOT billable provider tokens."""
    return math.ceil(len(text.strip()) / 4)

@dataclass(frozen=True)
class ProfileUpdate:
    value: str
    confidence: float
    evidence: str

def extract_profile_candidates(message: str) -> dict[str, ProfileUpdate]:
    """Explicit self-statements only. Rule scores are not calibrated probabilities."""
    result = {}
    def put(key, value, sentence, confidence=.95):
        value = value.strip(' \t,.:;"\'')
        if value and len(value) <= 180:
            result[key] = ProfileUpdate(value, confidence, sentence[:240])
    for sentence in re.findall(r'[^.!?\n]+[.!?]?', unicodedata.normalize('NFC', message)):
        if sentence.rstrip().endswith('?'):
            continue
        sentence = sentence.strip().rstrip('.!')
        low = sentence.lower()
        if not sentence or re.search(r'\b(nếu|giả sử|có thể|câu đùa|mình đùa|đừng|không phải|nhắc lại|nhớ lại|tạm thời|trong phiên này|trong cuộc chat này|trích dẫn|nói rằng)\b', low):
            continue
        assertion = re.split(r'\b(?:chứ không|dù trước|nhưng trước)\b', sentence, flags=re.I)[0]
        name = re.search(r'(?:mình|tôi)(?:\s+tên|\s+có tên)(?:\s+là)?\s+([^,;:]+)', assertion, re.I)
        if name and not re.search(r'\b(gì|như thế nào)\b', name[1], re.I):
            put('name', re.split(r'\s+(?:và|hiện|đang)\b', name[1], flags=re.I)[0], sentence)
        location = re.search(r'(?:mình|tôi)\s+(?:(?:hiện tại|hiện|giờ|vẫn|đang|hiện đang)\s+)*(?:sống ở|ở|sống tại|đang làm việc ở|làm việc ở)\s+([^,;]+)', assertion, re.I)
        if not location:
            location = re.search(r'(?:hiện(?: tại)? ở|nơi ở hiện tại là)\s+([^,;]+)', assertion, re.I)
        if location:
            value = re.split(r'\s+(?:và|trong|vài|để|chưa|mỗi|chứ)\b', location[1], flags=re.I)[0]
            if not re.search(r'\b(đâu|gì|như|cũ|đã|thay đổi|cập nhật)\b', value, re.I):
                transient = re.search(r'hôm nay|sáng nay|chiều nay|quán |họp|bay ra|ghé thăm|du lịch', low)
                put('location', value, sentence, .60 if transient else .95)
        job = re.search(r'(?:chuyển sang|(?:mình|tôi)\s+(?:(?:hiện tại|hiện|vẫn|đang)\s+)*làm|nghề(?: nghiệp)?(?: hiện tại)?(?: vẫn)?(?: là)?|đang làm)\s+([\w -]+?(?:engineer|developer|manager|designer|giáo viên|bác sĩ|kỹ sư))\b', assertion, re.I)
        if job and (re.search(r'\b(mình|tôi)\b', assertion, re.I) or re.search(r'^nghề', assertion, re.I)):
            put('profession', job[1], sentence)
        for key, pattern in {
            'favorite_drink': r'đồ uống yêu thích(?: của (?:mình|tôi))?\s+là\s+([^,;]+)',
            'favorite_food': r'món ăn yêu thích(?: của (?:mình|tôi))?\s+là\s+([^,;]+)',
            'pet': r'(?:mình|tôi)\s+nuôi\s+([^,;]+)',
        }.items():
            match = re.search(pattern, assertion, re.I)
            if match:
                put(key, match[1], sentence)
        interest = re.search(r'(?:mình|tôi)\s+(?:vẫn\s+)?(?:thích|đang quan tâm(?: nhiều)? đến)\s+(.+)', assertion, re.I)
        if interest and re.search(r'\b(Python|AI|MLOps|RAG|Java|Rust|SQL)\b', interest[1], re.I):
            put('interests', interest[1][:180], sentence, .90)
        explicit_style = re.search(r'(?:mình|tôi).*(?:muốn|thích|style)|hãy trả lời|style trả lời.*giữ', low)
        if explicit_style and re.search(r'trả lời|giải thích|trình bày', low) and re.search(r'ngắn|bullet|ví dụ|trade-off', low):
            pieces = ['ngắn gọn'] if 'ngắn' in low else []
            if '3 bullet' in low:
                pieces.append('3 bullet')
            elif 'bullet' in low:
                pieces.append('bullet')
            if 'ví dụ' in low:
                pieces.append('có ví dụ thực chiến' if 'thực chiến' in low else 'có ví dụ thực tế')
            if 'trade-off' in low:
                pieces.append('so sánh trade-off')
            if pieces:
                put('response_style', ', '.join(pieces), sentence, .90)
    return result

def extract_profile_updates(message: str) -> dict[str, str]:
    return {k: v.value for k, v in extract_profile_candidates(message).items() if v.confidence >= .85}

def merge_style(previous: str, update: str) -> str:
    """Update mentioned preference facets without discarding unrelated preferences."""
    old = [part.strip() for part in previous.split(',') if part.strip()]
    for part in update.split(','):
        part = part.strip()
        if 'bullet' in part:
            old = [item for item in old if 'bullet' not in item]
        if 'ví dụ' in part:
            old = [item for item in old if 'ví dụ' not in item]
        if part not in old:
            old.append(part)
    return ', '.join(old)

def merge_facts(facts: dict[str, str], updates: dict[str, str]) -> None:
    for key, value in updates.items():
        facts[key] = merge_style(facts.get(key, ''), value) if key == 'response_style' else value

@dataclass
class UserProfileStore:
    root_dir: Path

    def path_for(self, user_id: str) -> Path:
        if not user_id.strip():
            raise ValueError('user_id must not be empty')
        slug = re.sub(r'[^a-zA-Z0-9_-]', '_', user_id)[:40] or 'user'
        digest = hashlib.sha256(user_id.encode('utf-8')).hexdigest()[:16]
        return Path(self.root_dir) / f'{slug}-{digest}' / 'User.md'

    def read_text(self, user_id: str) -> str:
        path = self.path_for(user_id)
        return path.read_text(encoding='utf-8') if path.exists() else ''

    def write_text(self, user_id: str, content: str) -> Path:
        path = self.path_for(user_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', newline='\n', dir=path.parent, delete=False, suffix='.tmp') as stream:
            stream.write(content)
            temporary = Path(stream.name)
        try:
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)
        return path

    def edit_text(self, user_id: str, search_text: str, replacement: str) -> bool:
        if not search_text:
            raise ValueError('search_text must not be empty')
        text = self.read_text(user_id)
        if search_text not in text:
            return False
        self.write_text(user_id, text.replace(search_text, replacement, 1))
        return True

    def file_size(self, user_id: str) -> int:
        path = self.path_for(user_id)
        return path.stat().st_size if path.exists() else 0

    def records(self, user_id: str) -> dict:
        records = {}
        for key, payload in re.findall(r'^- \*\*(\w+)\*\*: (.+)$', self.read_text(user_id), re.M):
            record = json.loads(payload)
            if not isinstance(record, dict) or not isinstance(record.get('value'), str):
                raise ValueError(f'Invalid profile record: {key}')
            records[key] = record
        return records

    def facts(self, user_id: str) -> dict[str, str]:
        return {key: record['value'] for key, record in self.records(user_id).items()}

    def upsert_fact(self, user_id: str, key: str, value: str, confidence: float = .95,
                    evidence: str = 'explicit update', threshold: float = .85) -> bool:
        if not 0 <= confidence <= 1 or not 0 <= threshold <= 1:
            raise ValueError('Confidence and threshold must be finite values in [0, 1]')
        if confidence < threshold:
            return False
        if key not in {'name', 'location', 'profession', 'interests', 'favorite_drink', 'favorite_food', 'pet', 'response_style'}:
            raise ValueError(f'Unsupported profile field: {key}')
        if not value.strip() or len(value) > 180:
            raise ValueError('Fact value must contain 1..180 characters')
        records = self.records(user_id)
        old = records.get(key)
        if key == 'response_style' and old:
            value = merge_style(old['value'], value)
        if old and old['value'] == value:
            return False
        records[key] = {'value': value, 'confidence': confidence, 'evidence': evidence[:240],
                        'revision': old.get('revision', 0) + 1 if old else 1}
        text = '# User profile\n\nLatest accepted value per field; rule confidence and source evidence.\n\n'
        text += '\n'.join(f'- **{k}**: {json.dumps(v, ensure_ascii=False, sort_keys=True)}' for k, v in sorted(records.items())) + '\n'
        self.write_text(user_id, text)
        return True

def summarize_messages(messages: list[dict[str, str]], max_items: int = 6) -> str:
    snippets = []
    for message in messages:
        if message['role'] != 'user':
            continue
        text = message['content']
        facts = extract_profile_updates(text)
        if facts:
            snippets.append('Facts: ' + json.dumps(facts, ensure_ascii=False))
        sentences = [s.strip() for s in re.split(r'[.!?\n]+', text) if s.strip()]
        if sentences:
            chosen = next((s for s in sentences if re.search(r'tin |chủ đề|mục tiêu|bài học|quyết định', s, re.I)), sentences[0])
            snippets.append('User: ' + chosen[:220])
    return '\n'.join(dict.fromkeys(snippets[-max_items:]))

@dataclass
class CompactMemoryManager:
    threshold_tokens: int
    keep_messages: int
    summary_max_chars: int = 1600
    state: dict[str, dict[str, object]] = field(default_factory=dict)

    def __post_init__(self):
        if self.threshold_tokens < 1 or self.keep_messages < 1 or self.summary_max_chars < 100:
            raise ValueError('Invalid compaction settings')

    def _state(self, thread_id: str) -> dict:
        return self.state.setdefault(thread_id, {'messages': [], 'summary': '', 'compactions': 0, 'summary_chars_processed': 0})

    def append(self, thread_id: str, role: str, content: str) -> None:
        state = self._state(thread_id)
        state['messages'].append({'role': role, 'content': content})
        messages = state['messages']
        load = estimate_tokens(state['summary']) + sum(estimate_tokens(m['content']) + 4 for m in messages)
        if load <= self.threshold_tokens or len(messages) <= self.keep_messages:
            return
        older = messages[:-self.keep_messages]
        addition = summarize_messages(older)
        combined = state['summary'] + ('\n' if state['summary'] and addition else '') + addition
        cap = min(self.summary_max_chars, max(100, self.threshold_tokens))
        selected, size = [], 0
        for note in reversed(list(dict.fromkeys(combined.splitlines()))):
            note = note[:cap]
            if size + len(note) + 1 <= cap:
                selected.append(note)
                size += len(note) + 1
        state['summary'] = '\n'.join(reversed(selected))
        state['summary_chars_processed'] += len(combined)
        state['messages'] = messages[-self.keep_messages:]
        state['compactions'] += 1

    def context(self, thread_id: str) -> dict[str, object]:
        return copy.deepcopy(self._state(thread_id))

    def compaction_count(self, thread_id: str) -> int:
        return int(self._state(thread_id)['compactions'])
