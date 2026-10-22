"""Versioned agent API; all mutations carry a durable request key."""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .schemas import Options, Story


class AgentOptions(Options):
    input_mode: Literal['idea', 'outline', 'script', 'storyboard'] = 'storyboard'
    execution_mode: Literal['auto', 'review'] = 'auto'
    auto_reference: bool = False


class AgentCreate(BaseModel):
    model_config = ConfigDict(extra='forbid')
    input: str = Field(default='', max_length=50000)
    options: AgentOptions = Field(default_factory=AgentOptions)
    storyboard: Story | None = None


class ShotChange(BaseModel):
    model_config = ConfigDict(extra='forbid')
    uid: str = Field(pattern=r'^[a-zA-Z0-9_-]{1,80}$')
    changes: dict


class ProjectChange(BaseModel):
    model_config = ConfigDict(extra='forbid')
    expected_revision: str = Field(min_length=1)
    settings: dict | None = None
    story: Story | None = None
    shots: list[ShotChange] | None = Field(default=None, min_length=1, max_length=150)

    @model_validator(mode='after')
    def one_resource(self):
        if sum(value is not None for value in (self.settings, self.story, self.shots)) != 1:
            raise ValueError('每次提交 settings、story 或 shots 中的一种，分别记录可恢复操作。')
        return self


class PlanRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    action: Literal['render', 'finish', 'plan'] = 'render'
    internal_text: Literal['forbid', 'allowed'] = 'forbid'
    uids: list[str] | None = Field(default=None, min_length=1, max_length=150)
    regenerate: bool = False


class RunRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    plan_id: str = Field(pattern=r'^[a-f0-9]{64}$')


class ResumeRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    expected_revision: str | None = None


class StopRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    immediate: bool = False
