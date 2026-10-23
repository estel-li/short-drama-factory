"""Delivery inventory and narrowly scoped artifact downloads."""
from pathlib import Path, PurePosixPath

from fastapi import APIRouter
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field

from .contracts import ContractError
from .delivery import ALIASES, EDIT_FILES, VIDEO_SUFFIXES, build_delivery
from .project_locks import project_lock
from .storage import contained, identifier, read_json


class ArtifactView(BaseModel):
    model_config = ConfigDict(extra='allow')
    relative_path: str
    local_path: str
    size: int = Field(ge=0)
    sha256: str
    mime: str
    kind: str
    version_id: str | None = None
    api_url: str
    media: dict | None = None
    verification: dict | None = None


class DeliveryView(BaseModel):
    model_config = ConfigDict(extra='allow')
    schema_version: int
    project_id: str
    revision: str
    state: str | None = None
    busy: bool
    scope: str
    version_id: str | None = None
    artifacts: list[ArtifactView]
    aliases: dict[str, ArtifactView | None]
    checks: dict
    ready_for_delivery: bool
    media_verified: bool
    delivery_scope: str
    content_review_complete: bool
    fingerprint: str


def artifact_path(projects, pid, relative):
    """Membership lookup avoids hashing/decoding all films for each download."""
    root = projects.path(pid).resolve()
    name = PurePosixPath(relative)
    if (name.is_absolute() or '\\' in relative or ':' in relative
            or any(part in ('', '.', '..') or part.startswith('.') for part in name.parts)):
        raise ContractError('ARTIFACT_NOT_FOUND', '文件不在可交付产物清单中。', status=404)
    allowed = set(ALIASES.values()) | {'字幕.ass', '媒体验收.json'}
    state = read_json(root / 'state.json', {})
    records = list((state.get('shots_by_uid') or state.get('shots') or {}).values())
    for record in records:
        raw = record.get('clip_relative') or record.get('clip')
        if raw and Path(raw).suffix.lower() in VIDEO_SUFFIXES:
            path = Path(raw)
            if path.is_absolute():
                try:
                    raw = path.resolve().relative_to(root).as_posix()
                except ValueError:
                    continue
            allowed.add(str(raw).replace('\\', '/'))
    if len(name.parts) >= 3 and name.parts[0] == 'edits':
        try:
            identifier(name.parts[1])
            folder = contained(root, '/'.join(name.parts[:2]))
            if (folder / 'completed.json').is_file():
                allowed.update('/'.join((*name.parts[:2], file)) for file in EDIT_FILES)
                index_relative = '/'.join((*name.parts[:2], 'review/index.json'))
                allowed.add(index_relative)
                index = read_json(contained(root, index_relative), {})
                for page in index.get('pages', []):
                    page_name = PurePosixPath(page.get('file', ''))
                    if page_name.parent.as_posix() == 'review' and page_name.suffix.lower() == '.png':
                        allowed.add('/'.join((*name.parts[:2], page_name.as_posix())))
        except (ValueError, OSError, TypeError):
            pass
    try:
        path = contained(root, relative)
    except ValueError:
        raise ContractError('ARTIFACT_NOT_FOUND', '文件不在当前项目目录中。', status=404) from None
    if relative not in allowed or not path.is_file():
        raise ContractError('ARTIFACT_NOT_FOUND', '文件不在可交付产物清单中。', status=404)
    return path


def install_delivery_routes(app, services):
    router = APIRouter(prefix='/api/v2')

    @router.get('/projects/{pid}/delivery', response_model=DeliveryView, response_model_exclude_unset=True)
    def delivery(pid: str, verify: bool = False):
        s = services()
        with project_lock(s.db, pid):
            return build_delivery(s.projects, pid, verify)

    @router.get('/projects/{pid}/delivery/files/{relative:path}', response_class=FileResponse,
                responses={200: {'content': {'application/octet-stream': {'schema': {'type': 'string', 'format': 'binary'}}}}})
    def download(pid: str, relative: str):
        s = services()
        with project_lock(s.db, pid):
            path = artifact_path(s.projects, pid, relative)
        return FileResponse(path, filename=path.name)

    app.include_router(router)
