"""Image generation contracts; no model runtime dependencies in the workbench."""
from __future__ import annotations

from typing import Annotated, Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def valid_image_model(value):
    from .image_models import model_spec
    model_spec(value)
    return value


class ImageModels(BaseModel):
    model_config = ConfigDict(extra='forbid')
    diffusion_models: str = Field(default='', max_length=500)
    text_encoders: str = Field(default='', max_length=500)
    vae: str = Field(default='', max_length=500)
    checkpoints: str = Field(default='', max_length=500)

    @field_validator('*')
    @classmethod
    def relative_model(cls, value):
        value = value.strip().replace('\\', '/')
        if value and (value.startswith('/') or ':' in value or any(p in ('', '.', '..') for p in value.split('/')) or not value.endswith('.safetensors')):
            raise ValueError('请选择模型目录内的 safetensors 文件，不接受绝对路径或上级目录。')
        return value


class ImageSampling(BaseModel):
    """Portable subset of ComfyUI sampling options; null follows the model preset."""
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)
    steps: int | None = Field(default=None, ge=1, le=100)
    cfg: float = Field(default=1, ge=1, le=20)
    sampler: Literal['euler', 'euler_ancestral', 'heun', 'dpmpp_2m', 'dpmpp_2m_sde', 'dpmpp_sde', 'uni_pc'] = 'euler'
    scheduler: Literal['auto', 'simple', 'normal', 'karras', 'exponential', 'sgm_uniform', 'beta'] = 'auto'
    denoise: float = Field(default=1, ge=0.05, le=1)
    negative_prompt: str = Field(default='', max_length=4000)


class ImageSettings(BaseModel):
    model_config = ConfigDict(extra='forbid')
    engine: Literal['auto', 'shared', 'managed'] = 'auto'
    comfy_url: str = ''
    models_dir: str = ''
    library_models_dir: str = ''
    image_model: str = 'qwen-image-2.1'
    managed_port: int = Field(default=8190, ge=1024, le=65535)
    variant: Literal['auto', 'turbo-int8', 'turbo-bf16', 'quality-int8'] = 'auto'
    provider: str = 'deepseek'
    model: str = ''
    skill: str = 'image-qwen-general'
    auto_download: bool = False  # Legacy setting; downloads still require per-plan confirmation.
    models: ImageModels = Field(default_factory=ImageModels)
    sampling: ImageSampling = Field(default_factory=ImageSampling)
    timeout: int = Field(default=1800, ge=60, le=7200)

    _image_model_valid = field_validator('image_model')(valid_image_model)

    @field_validator('comfy_url')
    @classmethod
    def url(cls, value):
        if not value:
            return ''
        parsed = urlsplit(value)
        if parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError('图片服务地址须为不含认证信息、查询参数或片段的 HTTP(S) URL。')
        return value.rstrip('/')


class ReferenceImageOptions(BaseModel):
    model_config = ConfigDict(extra='forbid')
    enabled: bool = False
    characters: bool = True
    scenes: bool = True
    props: bool = False
    optimize: bool = True
    variant: Literal['auto', 'turbo-int8', 'turbo-bf16', 'quality-int8'] = 'auto'
    resolution: Literal['auto', '512', '768', '1024', '1536', '2048'] = 'auto'
    provider: str = ''
    model: str = ''
    image_model: str = 'qwen-image-2.1'

    _image_model_valid = field_validator('image_model')(valid_image_model)


class ReferenceSourceSelection(BaseModel):
    model_config = ConfigDict(extra='forbid')
    asset_ids: list[Annotated[str, Field(pattern=r'^[a-zA-Z0-9_-]{1,80}$')]] = Field(default_factory=list, max_length=10)
    reference_mode: Literal['reference', 'edit'] = 'reference'
    sampling: ImageSampling | None = None  # None inherits the workbench defaults.

    @model_validator(mode='after')
    def sampling_valid(self):
        if self.sampling and self.sampling.denoise < 1 and (self.reference_mode != 'edit' or not self.asset_ids):
            raise ValueError('重绘强度小于 1 时，请添加原图并选择编辑原图。')
        return self


class ImageRequest(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    prompt: str = Field(min_length=1, max_length=12000)
    image_model: str = 'qwen-image-2.1'
    optimize: bool = True
    optimized_prompt: str = Field(default='', max_length=20000)
    provider: str = Field(default='', max_length=80)
    model: str = Field(default='', max_length=200)
    skill: str = Field(default='', max_length=80)
    style: str = Field(default='', max_length=3000)
    purpose: Literal['general', 'character', 'scene', 'prop'] = 'general'
    ratio: str = '1:1'
    resolution: Literal['auto', '512', '768', '1024', '1536', '2048'] = 'auto'
    variant: Literal['auto', 'turbo-int8', 'turbo-bf16', 'quality-int8'] = 'auto'
    models: ImageModels | None = None
    seed: int | None = Field(default=None, ge=0, le=2**53 - 1)
    transparent: bool = False
    reference_images: list[Annotated[str, Field(pattern=r'^[0-9a-f]{64}$')]] = Field(default_factory=list, max_length=10)
    reference_mode: Literal['reference', 'edit'] = 'reference'
    sampling: ImageSampling = Field(default_factory=ImageSampling)

    _image_model_valid = field_validator('image_model')(valid_image_model)

    @model_validator(mode='after')
    def references_valid(self):
        if self.reference_mode == 'edit' and not self.reference_images:
            raise ValueError('编辑原图需要至少一张参考图，第一张作为原图。')
        if len(set(self.reference_images)) != len(self.reference_images):
            raise ValueError('请勿重复添加同一张参考图。')
        if self.sampling.denoise < 1 and (self.reference_mode != 'edit' or not self.reference_images):
            raise ValueError('重绘强度小于 1 时，请添加原图并选择编辑原图。')
        return self

    @field_validator('ratio')
    @classmethod
    def ratio_valid(cls, value):
        try:
            a, b = map(int, value.split(':'))
            if not 1 <= a <= 100 or not 1 <= b <= 100 or not .25 <= a / b <= 4:
                raise ValueError()
        except (TypeError, ValueError):
            raise ValueError('画幅填写如 1:1、3:4、16:9，比例须在 1:4 至 4:1 之间。')
        return value
