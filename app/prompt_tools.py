"""Deterministic H3 formatting for externally authored sections; never generation."""
from __future__ import annotations

from typing import Annotated, Literal
from pathlib import Path

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field

from .content import BASE_FIELDS, REF_FIELDS, assemble_prompt, prompt_valid, reference_labels
from .continuity import enabled
from .contracts import ContractError
from .downloads import Downloader
from .execution_policy import execution_policy
from .project_locks import project_lock
from .quality import prompt_cast_valid
from .storage import contained, read_json
from .video_workflows import validate_workflow


class CompilePromptRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    sections: dict[str, Annotated[str, Field(max_length=40000)]]


class CompiledPrompt(BaseModel):
    uid: str
    revision: str
    mode: Literal['T2VA', 'I2VA', 'L2VA', 'FL2VA', 'Ref2VA']
    aligned_seconds: float
    reference_labels: list[dict]
    prompt: str


def resolved_bindings(services, project, story, shot, options):
    """Match existing captured-reference fallback without migrating or uploading."""
    bindings = services.assets.resolve(project, shot, story, inspect_media=True)
    if any(bindings.values()) or not options.auto_reference or enabled(shot):
        return bindings
    references = read_json(project / 'references.json', {})
    renderer = services.config.renderer_config()
    names = {character['id']: character['name'] for character in story.get('characters', [])}
    images = []
    for cid in shot.get('characters', []):
        source = references.get(cid)
        if not source:
            continue
        entry = source if isinstance(source, dict) else {'image': source}
        origin_uid, origin = entry.get('shot_uid'), entry.get('shot_id', 0)
        if (origin_uid and origin_uid == shot.get('uid')) or (not origin_uid and origin >= shot['id']):
            continue
        image_name = entry.get('image')
        if not image_name:
            continue
        local = entry.get('local_file')
        path = contained(project, local) if local else contained(Path(renderer['comfy_dir']) / 'input', image_name)
        if path.is_file():
            images.append({'id': 'auto-' + str(len(images) + 1), 'type': 'image',
                           'name': names.get(cid, cid), 'character': cid,
                           'sha256': Downloader.checksum(path)})
    return {'images': images[:2]} if images else bindings


def compile_shot_prompt(services, pid, uid, sections):
    from pipeline import FPS, frames

    with project_lock(services.db, pid), execution_policy('forbid', allow_downloads=False):
        project = services.projects.path(pid)
        story = services.projects.get(pid)['story']
        if not story:
            raise ContractError('STORY_REQUIRED', '请先保存分镜，再编译外部提示词段落。', status=409)
        shot = next((item for item in story['shots'] if item['uid'] == uid), None)
        if shot is None:
            raise ContractError('SHOT_NOT_FOUND', '镜头 UID 不存在。', status=404)
        options = services.projects.options(project)
        try:
            bindings = resolved_bindings(services, project, story, shot, options)
            mode = services.content.mode(shot, options, bindings)
            preset = services.config.renderer_config().get('profiles', {}).get(options.profile)
            if not preset:
                raise ValueError('所选视频工作流不存在。')
            validate_workflow(preset, shot, bindings, mode)
        except (ValueError, OSError) as exc:
            raise ContractError('PROMPT_BINDINGS_INVALID', str(exc), status=422,
                                details=[{'uid': uid, 'field': 'bindings'}],
                                next_actions=['inspect_project', 'correct_bindings']) from exc
        fields = REF_FIELDS if mode == 'Ref2VA' else BASE_FIELDS
        missing = [name for name in fields if name not in sections]
        unknown = sorted(set(sections) - set(fields))
        empty = [name for name in fields if name in sections and not sections[name].strip()]
        if missing or unknown or empty:
            raise ContractError('PROMPT_SECTIONS_INVALID', '请按当前模式提供准确且非空的 H3 段落。', status=422,
                                details=[{'uid': uid, 'mode': mode, 'required': fields,
                                          'missing': missing, 'unknown': unknown, 'empty': empty}],
                                next_actions=['correct_prompt_sections'])
        seconds = frames(shot['duration']) / FPS
        try:
            prompt = assemble_prompt(sections, mode, seconds)
            prompt_valid(prompt, mode, bindings, shot.get('dialogue', []),
                         strict_keyframes=True, seconds=seconds)
            prompt_cast_valid(prompt, story, shot, bindings, mode)
        except ValueError as exc:
            raise ContractError('PROMPT_INVALID', str(exc), status=422,
                                details=[{'uid': uid, 'field': 'sections'}],
                                next_actions=['correct_prompt_sections']) from exc
        return {'uid': uid, 'revision': services.projects.revision(pid), 'mode': mode,
                'aligned_seconds': seconds, 'reference_labels': reference_labels(mode, bindings),
                'prompt': prompt}


def install_prompt_routes(app, services):
    router = APIRouter(prefix='/api/v2')

    @router.post('/projects/{pid}/shots/{uid}/compile', response_model=CompiledPrompt)
    def compile_prompt(pid: str, uid: str, body: CompilePromptRequest):
        return compile_shot_prompt(services(), pid, uid, body.sections)

    app.include_router(router)
