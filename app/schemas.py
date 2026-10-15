from __future__ import annotations

import math
from typing import Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from .image_schemas import ReferenceImageOptions


class Provider(BaseModel):
    model_config = ConfigDict(extra='forbid')
    id: str = Field(pattern=r'^[a-zA-Z0-9_-]{1,80}$')
    name: str = Field(min_length=1, max_length=80)
    kind: Literal['deepseek', 'ollama', 'lmstudio', 'compatible'] = 'compatible'
    base_url: str
    model: str = Field(default='', max_length=200)
    timeout: int = Field(default=180, ge=10, le=1800)
    retries: int = Field(default=3, ge=0, le=10)
    format_retries: int = Field(default=3, ge=0, le=10)
    max_tokens: int = Field(default=8192, ge=128, le=65536)
    temperature: float = Field(default=0.7, ge=0, le=2)
    stream: bool = True
    structured: Literal['text', 'json', 'schema'] = 'json'
    local: bool = False
    unload_after_use: bool = True
    capabilities: dict = Field(default_factory=dict)
    extra: dict = Field(default_factory=dict)

    @field_validator('id')
    @classmethod
    def provider_id(cls, value):
        if value.lower() in ('hf', 'comfy'):
            raise ValueError('hf 和 comfy 是专用认证名称，不能作为文字提供商 id。')
        return value

    @field_validator('base_url')
    @classmethod
    def url(cls, value):
        parsed = urlsplit(value)
        if parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError('服务地址必须为不含认证、查询或片段的 HTTP(S) URL。')
        return value.rstrip('/')

    @field_validator('extra')
    @classmethod
    def extras(cls, value):
        allowed = {'top_p', 'frequency_penalty', 'presence_penalty', 'seed', 'thinking', 'reasoning_effort'}
        if set(value) - allowed:
            raise ValueError('高级请求参数包含不支持的字段。')
        return value


class StageChoice(BaseModel):
    provider: str = 'deepseek'
    model: str = ''
    skill: str = ''


class Quality(BaseModel):
    model_config = ConfigDict(extra='forbid')
    label: str = Field(min_length=1, max_length=200)
    megapixels: float = Field(ge=0.1, le=4)
    steps: int = Field(ge=1, le=100)
    turbo: bool = False
    sampler: str = 'res_multistep'
    scheduler: str = 'simple'
    denoise: float = Field(default=1, ge=0, le=1)
    lora_strength: float = Field(default=1, ge=-2, le=2)


class Options(BaseModel):
    model_config = ConfigDict(extra='forbid')
    input_mode: Literal['idea', 'outline', 'script', 'storyboard'] = 'outline'
    execution_mode: Literal['auto', 'review'] = 'review'
    review_stages: list[Literal['outline', 'storyboard', 'prompt']] = Field(default_factory=lambda: ['outline', 'storyboard', 'prompt'])
    duration_rule: Literal['total', 'count', 'manual'] = 'total'
    total_seconds: float = Field(default=24, ge=4, le=600)
    shot_seconds: float = Field(default=4, ge=4, le=15)
    allow_long_shots: bool = False
    shot_count: int = Field(default=6, ge=1, le=150)
    manual_durations: list[float] = Field(default_factory=list)
    style: str = Field(default='温暖的二维动漫短剧', min_length=1, max_length=3000)
    genre: str = Field(default='治愈', max_length=1000)
    ratio: str = '9:16'
    profile: str = 'draft'
    seed: int = Field(default=12345, ge=0, le=2**63 - 151)
    auto_reference: bool = True
    reference_images: ReferenceImageOptions = Field(default_factory=ReferenceImageOptions)
    subtitles: bool = True
    render_retries: int = Field(default=1, ge=0, le=2)
    h3_mode: Literal['auto', 'T2VA', 'I2VA', 'FL2VA', 'L2VA', 'Ref2VA'] = 'auto'
    missing_reference: Literal['error', 'text'] = 'error'
    dialogue_language: str = Field(default='Chinese', max_length=60)
    narration: bool = False
    music: str = Field(default='N/A', max_length=500)
    dialogue_timing: Literal['fixed', 'fit'] = 'fit'
    speech_rate: float = Field(default=5.6, ge=1, le=12)
    speech_lead: float = Field(default=0.4, ge=0, le=2)
    speech_gap: float = Field(default=0.3, ge=0, le=2)
    speech_tail: float = Field(default=0.55, ge=0, le=2)
    edit_preset: Literal['original', 'gentle', 'compact'] = 'gentle'
    subtitle_alignment: Literal['speech', 'approximate'] = 'speech'
    review_interval: float = Field(default=0.75, ge=0.1, le=2)
    stages: dict[str, StageChoice] = Field(default_factory=lambda: {
        'outline': StageChoice(skill='outline-hook'),
        'storyboard': StageChoice(skill='storyboard-fast'),
        'prompt': StageChoice(skill='h3-t2va'),
    })

    @field_validator('ratio')
    @classmethod
    def ratio_valid(cls, value):
        try:
            a, b = map(int, value.split(':'))
            if not 1 <= a <= 100 or not 1 <= b <= 100 or not 0.25 <= a / b <= 4:
                raise ValueError()
        except (ValueError, TypeError):
            raise ValueError('画幅填写如 9:16，宽高比须在 1:4 至 4:1 之间。')
        return value

    @model_validator(mode='after')
    def stages_valid(self):
        if set(self.stages) != {'outline', 'storyboard', 'prompt'}:
            raise ValueError('必须配置大纲、分镜和提示词三个阶段。')
        return self


def durations(options: Options):
    maximum = 15 if options.allow_long_shots else 8
    if options.duration_rule == 'total' and options.shot_seconds > maximum:
        raise ValueError('超过 8 秒需开启高级长镜头选项；本机默认验证范围是 4～8 秒。')
    if options.duration_rule == 'manual':
        result = options.manual_durations
        if not 1 <= len(result) <= 150 or any(not math.isfinite(x) or not 4 <= x <= maximum for x in result):
            raise ValueError(f'手动模式需填写 1～150 个镜头时长，每镜头 4～{maximum} 秒。')
        if sum(result) > 600:
            raise ValueError('手动时长合计不能超过 600 秒。')
    elif options.duration_rule == 'count':
        count = options.shot_count
        seconds = max(4.0, min(float(maximum), options.total_seconds / count))
        result = [seconds] * count
        if sum(result) > 600:
            raise ValueError('固定镜头数导致总时长超过 600 秒，请减少镜头数。')
    else:
        count = max(1, math.ceil(options.total_seconds / options.shot_seconds))
        while count > 1 and options.total_seconds / count < 4:
            count -= 1
        result = [options.total_seconds / count] * count
    if any(not 4 <= x <= maximum for x in result):
        raise ValueError(f'无法在 4～{maximum} 秒范围内分配时长。')
    result = [round(x, 4) for x in result]
    frame_counts = [max(5, math.ceil(x * 24)) + (5 - max(5, math.ceil(x * 24)) % 17) % 17 for x in result]
    return {'count': len(result), 'durations': result, 'frames': frame_counts,
            'requested_total': options.total_seconds, 'allocated_total': round(sum(result), 4),
            'aligned_total': round(sum(frame_counts) / 24, 4),
            'warning': 'H3 按 17k+5 帧对齐，实际成片可能略长于请求。' + ('当前包含未在本机容量测试中验证的长镜头。' if any(x > 8 for x in result) else '')}


class Character(BaseModel):
    model_config = ConfigDict(extra='allow')
    id: str = Field(pattern=r'^[a-zA-Z0-9_-]{1,40}$')
    name: str = Field(min_length=1, max_length=100)
    visual_description: str = Field(min_length=1, max_length=4000)
    voice_description: str = ''


class Dialogue(BaseModel):
    speaker: str = ''
    text: str = Field(max_length=2000)


class Shot(BaseModel):
    model_config = ConfigDict(extra='allow')
    id: int = 1
    uid: str = Field(default='', pattern=r'^[a-zA-Z0-9_-]{0,80}$')
    scene: str = ''
    summary: str = ''
    camera: str = ''
    action: str = ''
    duration: float = Field(default=4, ge=4, le=15)
    characters: list[str] = Field(default_factory=list)
    continuity_group: str = ''
    use_previous_last_frame: bool = Field(default=False, strict=True, description='首帧功能：同场景连续镜头使用上一镜头实际末帧，默认关闭，由 AI 分镜人判断。')
    first_frame_reason: str = Field(default='', max_length=1000, description='AI 启用首帧功能的理由。')
    dialogue: list[Dialogue] = Field(default_factory=list)
    prompt: str = Field(default='', max_length=40000)
    locked: bool = False
    mode: str = 'auto'
    bindings: dict = Field(default_factory=dict)
    seed: int | None = Field(default=None, ge=0, le=2**63 - 1)


class Story(BaseModel):
    model_config = ConfigDict(extra='allow')
    title: str = Field(min_length=1, max_length=200)
    style: str = ''
    aspect_ratio: str = '9:16'
    characters: list[Character] = Field(default_factory=list)
    scenes: list[dict] = Field(default_factory=list)
    props: list[dict] = Field(default_factory=list)
    shots: list[Shot] = Field(min_length=1, max_length=150)

    @model_validator(mode='after')
    def cast_valid(self):
        ids = [c.id for c in self.characters]
        if len(set(ids)) != len(ids):
            raise ValueError('角色 id 重复。')
        uids = [s.uid for s in self.shots if s.uid]
        if len(set(uids)) != len(uids):
            raise ValueError('镜头 uid 重复。')
        for s in self.shots:
            if set(s.characters) - set(ids):
                raise ValueError('镜头引用了未定义角色。')
        return self


class Outline(BaseModel):
    title: str = Field(min_length=1)
    premise: str = Field(min_length=1)
    beats: list[dict] = Field(min_length=1)
    ending: str = ''


class EpisodePlan(Outline):
    number: int = Field(ge=1, le=100)
    hook: str = ''
    characters: list[str] = Field(default_factory=list)


class SeriesPlan(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    premise: str = Field(min_length=1, max_length=10000)
    characters: list[Character] = Field(default_factory=list, max_length=30)
    scenes: list[dict] = Field(default_factory=list)
    props: list[dict] = Field(default_factory=list)
    episodes: list[EpisodePlan] = Field(min_length=1, max_length=100)

    @model_validator(mode='after')
    def references_valid(self):
        ids = [c.id for c in self.characters]
        if len(ids) != len(set(ids)) or len({e.number for e in self.episodes}) != len(self.episodes):
            raise ValueError('分集计划的角色 id 或集数重复。')
        if any(set(e.characters) - set(ids) for e in self.episodes):
            raise ValueError('分集计划引用了未定义的共享角色。')
        return self
