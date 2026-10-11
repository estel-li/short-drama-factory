from __future__ import annotations

import hashlib
import uuid
from pathlib import Path

import av
import requests

from .storage import contained, read_json, write_json


FIRST_FRAME_RULES = '''首帧功能由 AI 分镜人逐镜决定：use_previous_last_frame 为 JSON 布尔值，默认 false。
仅当当前镜头与紧邻的上一镜头属于同一场景、同一连续段，而且画面应从上一镜头的结束状态继续时，才设为 true，并在 first_frame_reason 简述理由。
第一镜、换场、时间跳跃、闪回、蒙太奇、需要硬切/正反打或完全不同起始构图的镜头设为 false。不要为了人物相同或风格一致而启用。
场景使用稳定的 scene_id 或完全一致的 scene；同一连续段使用相同 continuity_group，时间或动作中断时换组。
跨批次第一镜也要参考 previous_shots 的最后一镜。启用后由程序强制 I2VA，并以当前顺序上一条视频的实际最后一帧为首帧；无需填写绑定或上传图片。
新镜头动作必须接续上一镜头末态，禁止重新演上一镜头已完成的动作。未启用时原有模式、素材和规则照常。'''


def enabled(shot):
    return shot.get('use_previous_last_frame', False) is True


def same_scene(previous, shot):
    def text(item, key):
        return str(item.get(key) or '').strip()
    old_group, group = text(previous, 'continuity_group'), text(shot, 'continuity_group')
    if old_group and group and old_group != group:
        return False
    for key in ('scene_id', 'scene'):
        left, right = text(previous, key), text(shot, key)
        if left and right:
            return left == right
    return bool(old_group and group and old_group == group)


def validate_links(shots, previous=None):
    for index, shot in enumerate(shots, 1):
        if not isinstance(shot.get('use_previous_last_frame', False), bool):
            raise ValueError('首帧功能 use_previous_last_frame 必须为 true 或 false。')
        if enabled(shot):
            label = shot.get('id', index)
            if previous is None:
                raise ValueError(f'镜头 {label} 是第一镜，不能启用首帧功能。')
            if not same_scene(previous, shot):
                raise ValueError(f'镜头 {label} 的首帧功能要求与紧邻上一镜头同场景、同连续段，请关闭首帧功能或修正场景。')
        previous = shot


def predecessor(shot, story):
    shots = story['shots']
    for index, candidate in enumerate(shots):
        if candidate is shot or (shot.get('uid') and candidate.get('uid') == shot['uid']) or (not shot.get('uid') and candidate.get('id') == shot.get('id')):
            previous = shots[index - 1] if index else None
            validate_links([shot], previous)
            return previous
    raise ValueError('首帧功能找不到当前镜头。')


def planned_frame(shot, previous):
    return {'id': 'prev-tail-' + str(shot.get('uid') or shot['id']), 'type': 'image',
            'name': '上一分镜的实际末帧', 'source': 'previous_last_frame',
            'source_shot_uid': previous.get('uid') or str(previous['id'])}


def extract_last_frame(project, shot, previous, clip, cancel=None):
    """Decode to EOF: the last displayed frame, without a guessed -ss timestamp."""
    project, clip = Path(project), Path(clip)
    if not clip.resolve().is_relative_to(project.resolve()) or not clip.is_file():
        raise ValueError('首帧功能需要当前项目上一分镜已完成的视频。')
    sha = hashlib.sha256()
    with clip.open('rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            sha.update(block)
    source_hash = sha.hexdigest()
    asset = planned_frame(shot, previous)
    manifest_path = project / 'assets' / 'first_frames.json'
    manifest = read_json(manifest_path, {})
    cached = manifest.get(asset['id'], {})
    if cached.get('source_clip_sha256') == source_hash and cached.get('source_shot_uid') == asset['source_shot_uid']:
        path = contained(project, cached['file'])
        if path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == cached.get('sha256'):
            return cached
    last, count, previous_pts = None, 0, None
    try:
        with av.open(str(clip)) as media:
            if not media.streams.video:
                raise ValueError('上一分镜视频没有视频流，无法提取末帧。')
            for frame in media.decode(video=0):
                if cancel and cancel():
                    from .providers import Cancelled
                    raise Cancelled('末帧提取已停止，已完成视频保留。')
                if frame.pts is None or previous_pts is not None and frame.pts <= previous_pts:
                    raise ValueError('上一分镜视频时间戳异常，无法可靠提取末帧。')
                last, previous_pts = frame, frame.pts
                count += 1
    except av.FFmpegError as exc:
        raise ValueError('上一分镜视频无法完整解码，首帧提取失败。') from exc
    if last is None:
        raise ValueError('上一分镜视频没有可解码帧，首帧提取失败。')
    token = hashlib.sha256((asset['id'] + asset['source_shot_uid'] + source_hash).encode()).hexdigest()[:28]
    relative = 'assets/first_frame_' + token + '.png'
    target = contained(project, relative)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(target.name + '.' + uuid.uuid4().hex + '.tmp')
    try:
        last.to_image().save(temporary, format='PNG')
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)
    asset.update(file=relative, sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
                 source_clip_sha256=source_hash, source_clip_relative=clip.relative_to(project).as_posix(),
                 frame_index=count - 1, pts=last.pts, time_base=str(last.time_base),
                 width=last.width, height=last.height)
    manifest[asset['id']] = asset
    write_json(manifest_path, manifest)
    return asset


def materialize_frame(project, asset, config):
    """Also support the standalone pipeline and remote ComfyUI."""
    import shutil
    path = contained(project, asset['file'])
    subfolder = 'drama_assets/' + Path(project).name
    name = asset['sha256'][:20] + '.png'
    value = dict(asset)
    if config.get('mode') == 'remote':
        headers = {'Authorization': 'Bearer ' + config['comfy_auth_token']} if config.get('comfy_auth_token') else {}
        with path.open('rb') as source:
            response = requests.post(config['comfy_url'] + '/upload/image', files={'image': (name, source)},
                                     data={'subfolder': subfolder, 'type': 'input', 'overwrite': 'true'}, headers=headers, timeout=60)
        response.raise_for_status()
        uploaded = response.json()
        value['comfy_file'] = uploaded.get('subfolder', '') + '/' + uploaded['name']
    else:
        target = contained(Path(config['comfy_dir']) / 'input', subfolder + '/' + name)
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.is_file() or hashlib.sha256(target.read_bytes()).hexdigest() != asset['sha256']:
            shutil.copy2(path, target)
        value['comfy_file'] = subfolder + '/' + name
    return value
