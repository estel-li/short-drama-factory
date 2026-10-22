"""Per-execution text-provider policy and pure external-content validation.

The legacy surface permits internal text generation unless its caller installs a
policy. Agent execution installs ``forbid`` by default. Context-local policy
avoids leaking one job's choice into unrelated requests, including after failure.
"""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Literal

from .contracts import ContractError


InternalTextPolicy = Literal['allowed', 'forbid']


@dataclass(frozen=True)
class ExecutionPolicy:
    internal_text: InternalTextPolicy = 'allowed'
    scope: str = ''
    allow_downloads: bool = True


_policy = ContextVar('factory_execution_policy', default=ExecutionPolicy())


def current_policy() -> ExecutionPolicy:
    return _policy.get()


def internal_text_allowed() -> bool:
    return current_policy().internal_text == 'allowed'


@contextmanager
def execution_policy(internal_text: InternalTextPolicy = 'forbid', *, scope: str = '', allow_downloads: bool = True):
    """Install a job policy; nested calls cannot relax an enclosing prohibition."""
    if internal_text not in ('allowed', 'forbid'):
        raise ValueError('internal_text 必须为 allowed 或 forbid。')
    if type(allow_downloads) is not bool:
        raise ValueError('allow_downloads 必须为布尔值。')
    previous = current_policy()
    effective = 'forbid' if 'forbid' in (internal_text, previous.internal_text) else 'allowed'
    token = _policy.set(ExecutionPolicy(effective, scope or previous.scope,
                                      previous.allow_downloads and allow_downloads))
    try:
        yield current_policy()
    finally:
        _policy.reset(token)


def enforce_provider_call(stage: str = '') -> None:
    """Call before any internal text generation or associated model preparation."""
    policy = current_policy()
    if policy.internal_text == 'forbid':
        details = [{'field': 'internal_text', 'policy': 'forbid'}]
        if stage:
            details[0]['stage'] = stage
        if policy.scope:
            details[0]['scope'] = policy.scope
        raise ContractError(
            'TEXT_GENERATION_FORBIDDEN',
            '当前执行禁止内部文字模型调用。请由外部 AI 补齐或修正内容后重新生成执行计划。',
            status=409, details=details,
            next_actions=['supply_external_content', 'create_execution_plan'],
        )


def enforce_download(resource: str = '') -> None:
    """Missing resources require a separate explicitly authorized preparation."""
    policy = current_policy()
    if not policy.allow_downloads:
        raise ContractError(
            'IMPLICIT_DOWNLOAD_FORBIDDEN',
            '执行计划不允许隐式下载。请先显式准备所需资源，再重新生成执行计划。',
            status=409, details=[{'resource': resource, 'scope': policy.scope}],
            next_actions=['prepare_resources', 'create_execution_plan'],
        )


def validate_external_shot(story, shot, options, bindings, mode):
    """Validate an already-authored H3 prompt without changing the story.

    Bindings must come from the same resolver as rendering. This checks prompt
    structure, real reference labels, exact dialogue and cast identity; it does
    not promise a render cache hit or approve workflow/environment readiness.
    """
    from .content import prompt_valid
    from .continuity import enabled
    from .quality import prompt_cast_valid
    from pipeline import FPS, frames

    prompt = shot.get('prompt')
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError('缺少外部 AI 编写的完整 H3 提示词。')
    prompt_valid(prompt, mode, bindings, shot.get('dialogue', []),
                 strict_keyframes=enabled(shot), seconds=frames(shot['duration']) / FPS)
    prompt_cast_valid(prompt, story, shot, bindings, mode)
    return prompt


def validate_external_story(story, options, resolve_bindings, mode_resolver, *, uids=None):
    """Fail fast for incomplete external content; no provider or write is used.

    The caller supplies a normalized story and read-only binding/mode resolvers.
    An empty selection is intentionally distinct from all shots.
    """
    if not isinstance(story, dict) or not story.get('shots'):
        raise ContractError(
            'EXTERNAL_CONTENT_REQUIRED', '请先提供完整分镜和每镜 H3 提示词。', status=409,
            details=[{'field': 'story', 'message': '缺少分镜。'}],
            next_actions=['supply_external_content', 'create_execution_plan'],
        )
    selected = None if uids is None else set(uids)
    available = {shot.get('uid') for shot in story['shots']}
    if selected is not None and selected - available:
        raise ContractError(
            'SHOT_NOT_FOUND', '所选镜头 UID 不存在。', status=404,
            details=[{'field': 'uids', 'missing': sorted(selected - available)}],
            next_actions=['inspect_project'],
        )
    issues = []
    for index, shot in enumerate(story['shots']):
        if selected is not None and shot.get('uid') not in selected:
            continue
        try:
            bindings = resolve_bindings(shot, story)
            mode = mode_resolver(shot, options, bindings)
            validate_external_shot(story, shot, options, bindings, mode)
        except ValueError as exc:
            issues.append({'field': f'story.shots.{index}.prompt',
                           'uid': shot.get('uid'), 'message': str(exc)})
    if issues:
        raise ContractError(
            'EXTERNAL_CONTENT_REQUIRED', '外部内容尚未通过校验；未调用文字模型。',
            status=409, details=issues,
            next_actions=['supply_external_content', 'create_execution_plan'],
        )
