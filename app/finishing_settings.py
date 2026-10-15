"""Saved editing choices, validated independently from native video generation."""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .masking import Mask


class Note(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    start: float = Field(strict=True, ge=0, le=1200)
    end: float = Field(strict=True, ge=0, le=1200)
    text: str = Field(min_length=1, max_length=2000)

    @model_validator(mode='after')
    def timing(self):
        if self.start >= self.end:
            raise ValueError('注释开始时间必须小于结束时间。')
        return self


class FinishingSettings(BaseModel):
    model_config = ConfigDict(extra='forbid')
    edit_preset: Literal['original', 'gentle', 'compact'] = 'gentle'
    review_interval: float = Field(default=.75, strict=True, ge=.1, le=2)
    notes: list[Note] = Field(default_factory=list, max_length=100)
    masks: list[Mask] = Field(default_factory=list, max_length=100)

    @model_validator(mode='after')
    def nonoverlapping_notes(self):
        ordered = sorted(self.notes, key=lambda note: note.start)
        if any(a.end > b.start for a, b in zip(ordered, ordered[1:])):
            raise ValueError('注释时间不可重叠，请合并或错开。')
        return self


def validate_settings(body, story):
    value = FinishingSettings.model_validate(body).model_dump()
    uids = {shot['uid'] for shot in (story or {}).get('shots', [])}
    if any(mask['shot_uid'] not in uids for mask in value['masks']):
        raise ValueError('遮罩引用的镜头不存在。')
    return value
