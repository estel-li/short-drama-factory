"""Typed public inputs and safe, machine-readable failures.

Legacy endpoints retain their existing defaults. Agent endpoints may use stricter
defaults without silently changing old projects or browser behavior.
"""
from __future__ import annotations

import re
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .schemas import Options, Story


class ContractError(ValueError):
    def __init__(self, code, message, *, status=400, retryable=False, details=None, next_actions=None):
        super().__init__(message)
        self.code, self.status, self.retryable = code, status, retryable
        self.details, self.next_actions = details or [], next_actions or []


def safe_message(message):
    value = str(message)[:2000]
    value = re.sub(r'(?i)(bearer\s+)[^\s,;]+', r'\1[redacted]', value)
    value = re.sub(r'(?i)((?:api[_-]?key|token|password|secret)\s*[=:]\s*)[^\s,;]+', r'\1[redacted]', value)
    value = re.sub(r'\bsk-[A-Za-z0-9_-]{8,}', '[redacted]', value)
    return value


def error_body(code, message, *, retryable=False, details=None, next_actions=None):
    message = safe_message(message)
    return {'error': message, 'code': code, 'message': message, 'retryable': retryable,
            'details': details or [], 'next_actions': next_actions or []}


class CreateProjectRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    input: str = Field(default='', max_length=50000)
    options: Options = Field(default_factory=Options)
    storyboard: Story | None = None
    start: bool = True


class ErrorView(BaseModel):
    error: str
    code: str
    message: str
    retryable: bool = False
    details: list[dict] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)


class SaveStoryRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    id: str = Field(pattern=r'^[a-zA-Z0-9_-]{1,80}$')
    story: Story


class ValidateStoryRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    story: Story


class StageRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    force: bool | None = None
    limit: int | None = Field(default=None, ge=1, le=150, strict=True)
    execution_mode: Literal['auto', 'review'] | None = None
    uids: list[str] | None = None


class JobView(BaseModel):
    id: str
    project_id: str
    kind: str
    status: str
    message: str
    created_at: str
    updated_at: str
    attempts: int
    cancel_requested: bool
    terminal: bool
    outcome: str
    next_actions: list[str]
    failure: dict | None = None


def job_view(row):
    status = row['status']
    actions = {'queued': ['watch', 'stop'], 'running': ['watch', 'stop'],
               'review': ['inspect', 'resume'], 'paused': ['inspect', 'resume'],
               'error': ['diagnose', 'resume'], 'done': ['inspect_artifacts']}
    value = {key: row[key] for key in ('id', 'project_id', 'kind', 'status', 'created_at', 'updated_at', 'attempts')}
    value.update(message=safe_message(row.get('message', '')), cancel_requested=bool(row.get('cancel_requested')),
                 terminal=status not in ('queued', 'running'),
                 outcome='stage_completed' if status == 'done' else status,
                 next_actions=actions.get(status, ['inspect']))
    try:
        failure = json.loads(row.get('failure') or '{}')
    except (ValueError, TypeError):
        failure = {}
    if failure and status in ('error', 'paused'):
        value['failure'] = failure
        value['next_actions'] = failure.get('next_actions') or value['next_actions']
    return value
