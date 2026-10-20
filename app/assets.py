from __future__ import annotations

import base64
import hashlib
import io
import uuid
import shutil
from pathlib import Path

from PIL import Image
import av
import requests

from .storage import contained, identifier, now, read_json, write_json


def media_metadata(path, kind):
    """Read stream headers without decoding the whole input on every preflight."""
    with av.open(str(path)) as media:
        streams = media.streams.video if kind == 'video' else media.streams.audio
        if not streams:
            raise ValueError('素材缺少需要的视频或音频流。')
        stream = streams[0]
        seconds = float(stream.duration * stream.time_base) if stream.duration is not None else (
            media.duration / av.time_base if media.duration else None)
        result = {'duration': seconds, 'include_audio': bool(media.streams.audio)}
        if kind == 'video':
            result.update(width=stream.width, height=stream.height,
                          fps=float(stream.average_rate) if stream.average_rate else None)
            if stream.frames:
                result['frames'] = stream.frames
        return result


class Assets:
    def __init__(self, config, projects):
        self.config, self.projects = config, projects

    def add_image(self, pid, encoded, name='', character='', generated=False, generation=None):
        if not generated:
            self.projects.assert_idle(pid)
        project = self.projects.path(pid)
        raw = base64.b64decode(encoded, validate=True)
        if len(raw) > 8_000_000:
            raise ValueError('图片上限 8MB。')
        with Image.open(io.BytesIO(raw)) as image:
            image.verify()
            ext = {'PNG': '.png', 'JPEG': '.jpg', 'WEBP': '.webp'}.get(image.format)
        if not ext:
            raise ValueError('支持 PNG、JPEG、WebP 图片。')
        aid = uuid.uuid4().hex[:20]
        relative = 'assets/' + aid + ext
        contained(project, relative).parent.mkdir(exist_ok=True)
        contained(project, relative).write_bytes(raw)
        value = {'id': aid, 'type': 'image', 'name': name or aid, 'file': relative,
                 'sha256': hashlib.sha256(raw).hexdigest(), 'source': 'user', 'character': character, 'created_at': now()}
        if generation:
            value.update(source='qwen-image', generation=generation)
        assets = read_json(project / 'assets.json', {})
        assets[aid] = value
        write_json(project / 'assets.json', assets)
        return value

    def add_media(self, pid, encoded, kind, name=''):
        if kind not in ('video', 'audio'):
            raise ValueError('素材类型不正确。')
        self.projects.assert_idle(pid)
        project = self.projects.path(pid)
        raw = base64.b64decode(encoded, validate=True)
        if len(raw) > 8_000_000:
            raise ValueError('参考素材上限 8MB，请使用短视频或短音频。')
        ext = Path(name).suffix.lower()
        allowed = ('.mp4', '.webm', '.mov') if kind == 'video' else ('.wav', '.mp3', '.flac', '.m4a', '.ogg')
        if ext not in allowed:
            raise ValueError('参考素材格式不支持。')
        aid = uuid.uuid4().hex[:20]
        folder = project / 'assets'
        folder.mkdir(exist_ok=True)
        path = folder / (aid + ext)
        path.write_bytes(raw)
        try:
            with av.open(str(path)) as media:
                if (kind == 'video' and not media.streams.video) or (kind == 'audio' and not media.streams.audio):
                    raise ValueError('参考素材没有需要的视频或音频流。')
                duration = media.duration / av.time_base if media.duration else 0
                include_audio = bool(media.streams.audio)
                if not (2 <= duration <= 15 if kind == 'video' else 0 < duration <= 15):
                    raise ValueError('视频参考需 2～15 秒，音频参考最长 15 秒。')
            if kind == 'video':
                import pipeline
                normalized = folder / (aid + '_24fps.mp4')
                pipeline.ffmpeg(['-i', path, '-vf', 'fps=24', '-c:v', 'libx264', '-crf', '20', '-c:a', 'aac', normalized])
                path.unlink()
                path = normalized
            value = {'id': aid, 'type': kind, 'name': name or aid, 'file': str(path.relative_to(project)).replace('\\', '/'),
                     'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'source': 'user', 'duration': duration,
                     'include_audio': include_audio, 'created_at': now()}
            value.update(media_metadata(path, kind))
            assets = read_json(project / 'assets.json', {})
            assets[aid] = value
            write_json(project / 'assets.json', assets)
            return value
        except Exception:
            path.unlink(missing_ok=True)
            raise

    def resolve(self, project, shot, story, inspect_media=False):
        from .continuity import enabled, planned_frame, predecessor
        if enabled(shot):
            return {'first_frame': planned_frame(shot, predecessor(shot, story))}
        assets = read_json(project / 'assets.json', {})
        raw = shot.get('bindings', {})
        result = {}
        for kind in ('images', 'videos', 'audios', 'first_frame', 'last_frame', 'source_video', 'source_audio', 'guide_image'):
            values = raw.get(kind)
            if values is None:
                continue
            multiple = kind in ('images', 'videos', 'audios')
            values = values if multiple else [values]
            if not isinstance(values, list):
                raise ValueError('素材绑定格式不正确。')
            selected = []
            for aid in values:
                asset = assets.get(identifier(aid))
                if not asset or not contained(project, asset['file']).is_file():
                    raise ValueError('已绑定素材不存在：' + aid)
                expected = 'video' if kind in ('videos','source_video') else 'audio' if kind in ('audios','source_audio') else 'image'
                if asset['type'] != expected:
                    raise ValueError('素材类型与绑定槽位不匹配。')
                selected.append({k: asset[k] for k in ('id', 'type', 'name', 'file', 'sha256')})
                if asset.get('character'):
                    selected[-1]['character'] = asset['character']
                if 'include_audio' in asset:
                    selected[-1]['include_audio'] = asset['include_audio']
                for key in ('duration', 'frames', 'fps', 'width', 'height'):
                    if key in asset:
                        selected[-1][key] = asset[key]
                if inspect_media and kind in ('source_video', 'source_audio'):
                    selected[-1].update(media_metadata(contained(project, asset['file']), expected))
                selected[-1]['sha256'] = hashlib.sha256(contained(project, asset['file']).read_bytes()).hexdigest()
            result[kind] = selected if multiple else selected[0] if selected else None
        if not any(result.get(kind) for kind in ('images','videos','audios','first_frame','last_frame')):
            for cid in shot.get('characters', []):
                for asset in reversed(list(assets.values())):
                    if asset.get('character') == cid:
                        result.setdefault('images', []).append({k: asset[k] for k in ('id', 'type', 'name', 'file', 'sha256')})
                        result['images'][-1]['character'] = cid
                        result['images'][-1]['sha256'] = hashlib.sha256(contained(project, asset['file']).read_bytes()).hexdigest()
                        break
        return result

    def materialize(self, project, bindings):
        result = {}
        env = self.config.renderer_config()
        for kind, values in bindings.items():
            multiple = isinstance(values, list)
            items = values if multiple else [values]
            mapped = []
            for asset in items:
                if not asset:
                    continue
                value = dict(asset)
                if value.get('comfy_file') and not value.get('file'):
                    mapped.append(value)
                    continue
                path = contained(project, asset['file'])
                value['sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
                subfolder = 'drama_assets/' + project.name
                name = value['sha256'][:20] + path.suffix
                from .comfyio import upload_file
                value['comfy_file'] = upload_file(path, subfolder, name, env['comfy_url'], self.config.key('comfy'))
                mapped.append(value)
            result[kind] = mapped if multiple else mapped[0] if mapped else None
        return result
