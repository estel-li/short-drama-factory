"""Authored director rules are separate from mechanically measured evidence."""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)


class TimeRange(StrictModel):
    start: float = Field(ge=0)
    end: float = Field(gt=0)

    @model_validator(mode='after')
    def ordered(self):
        if self.end <= self.start:
            raise ValueError('end 必须大于 start；时间使用原片绝对秒数。')
        return self


class PrepareReference(StrictModel):
    source_path: str = Field(min_length=1, max_length=2000)
    source_sha256: str = Field(pattern=r'^[a-f0-9]{64}$')
    start: float = Field(default=0, ge=0)
    end: float | None = Field(default=None, gt=0)
    sample_seconds: float = Field(default=3, ge=.25, le=60)
    cut_threshold: float = Field(default=.25, ge=.05, le=.9)
    max_frames: int = Field(default=240, ge=8, le=1200)
    max_clips: int = Field(default=8, ge=0, le=24)

    @model_validator(mode='after')
    def ordered(self):
        if self.end is not None and self.end <= self.start:
            raise ValueError('end 必须大于 start。')
        return self


class EvidenceClip(TimeRange):
    @model_validator(mode='after')
    def bounded(self):
        if self.end - self.start > 60:
            raise ValueError('单个补充片段最多 60 秒；长段请分次提取。')
        return self


class Coverage(StrictModel):
    frames: list[TimeRange] = Field(default_factory=list, max_length=500)
    motion: list[TimeRange] = Field(default_factory=list, max_length=500)
    audio: list[TimeRange] = Field(default_factory=list, max_length=500)


class DirectorRule(StrictModel):
    id: str = Field(pattern=r'^[a-z][a-z0-9-]{0,59}$')
    dimension: Literal['visual', 'composition', 'camera', 'editing', 'action', 'effects', 'sound']
    observation: str = Field(min_length=1, max_length=2000)
    guidance: str = Field(min_length=1, max_length=2000)
    when: str = Field(default='适用场景', max_length=500)
    avoid: list[str] = Field(default_factory=list, max_length=12)
    basis: Literal['frames', 'motion', 'audio']
    confidence: Literal['high', 'medium', 'low'] = 'medium'
    evidence: list[TimeRange] = Field(min_length=1, max_length=30)


class ShotPattern(TimeRange):
    id: str = Field(pattern=r'^[a-zA-Z0-9_-]{1,60}$')
    purpose: str = Field(min_length=1, max_length=1000)
    framing: str = Field(default='', max_length=1000)
    movement: str = Field(default='', max_length=1000)
    action: str = Field(default='', max_length=1500)
    transition: str = Field(default='', max_length=500)
    sound: str = Field(default='', max_length=1000)
    rules: list[str] = Field(default_factory=list, max_length=100)


class ScenePattern(StrictModel):
    name: str = Field(min_length=1, max_length=100)
    when: str = Field(min_length=1, max_length=1000)
    rules: list[str] = Field(min_length=1, max_length=100)


class PublishDirectorStyle(StrictModel):
    style_id: str = Field(pattern=r'^[a-z][a-z0-9-]{0,39}$')
    expected_version: str | None = Field(default=None, pattern=r'^[a-f0-9]{20}$')
    analysis_id: str = Field(pattern=r'^[a-zA-Z0-9_-]{1,80}$')
    name: str = Field(min_length=1, max_length=100)
    summary: str = Field(min_length=1, max_length=3000)
    coverage: Coverage
    rules: list[DirectorRule] = Field(min_length=1, max_length=100)
    scene_patterns: list[ScenePattern] = Field(default_factory=list, max_length=30)
    shot_structure: list[ShotPattern] = Field(default_factory=list, max_length=150)
    limitations: list[str] = Field(min_length=1, max_length=30)

    @model_validator(mode='after')
    def identifiers(self):
        ids = {rule.id for rule in self.rules}
        if len(ids) != len(self.rules):
            raise ValueError('规则 id 不可重复。')
        if len({shot.id for shot in self.shot_structure}) != len(self.shot_structure):
            raise ValueError('参考镜头 id 不可重复。')
        for pattern in [*self.scene_patterns, *self.shot_structure]:
            if set(pattern.rules) - ids:
                raise ValueError('场景或镜头引用了不存在的规则。')
        if any(b.start < a.end for a, b in zip(self.shot_structure, self.shot_structure[1:])):
            raise ValueError('参考镜头结构须按原片时间顺序排列且不可重叠。')
        return self


class BindDirectorStyle(StrictModel):
    expected_revision: str = Field(min_length=1)
    style_id: str = Field(pattern=r'^[a-z][a-z0-9-]{0,39}$')
    version: str = Field(pattern=r'^[a-f0-9]{20}$')
    mode: Literal['inspired', 'remake'] = 'inspired'


class StyleAssessment(StrictModel):
    rule_id: str = Field(min_length=1, max_length=60)
    status: Literal['passed', 'failed', 'not_checked']
    note: str = Field(min_length=1, max_length=2000)
    evidence: list[TimeRange] = Field(default_factory=list, max_length=30)


class DirectorReview(StrictModel):
    expected_revision: str = Field(min_length=1)
    final_sha256: str = Field(pattern=r'^[a-f0-9]{64}$')
    assessments: list[StyleAssessment] = Field(min_length=1, max_length=100)


class InstallDirectorStyle(StrictModel):
    target_directory: str = Field(min_length=1, max_length=2000)


class ImportDirectorStyle(StrictModel):
    package_directory: str = Field(min_length=1, max_length=2000)
    manifest_sha256: str = Field(pattern=r'^[a-f0-9]{64}$')
    style_id: str = Field(pattern=r'^[a-z][a-z0-9-]{0,39}$')
    version: str = Field(pattern=r'^[a-f0-9]{20}$')
    expected_version: str | None = Field(default=None, pattern=r'^[a-f0-9]{20}$')
