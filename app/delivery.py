"""Read-only delivery inventory and optional CPU verification of current films.

File existence, recorded evidence, fresh decoding and content review are separate
claims. This module never runs ASR/OCR, loads models or repairs source artifacts.
"""
from __future__ import annotations

import hashlib
import math
import mimetypes
from pathlib import Path
from urllib.parse import quote

from .contracts import safe_message
from .quality import render_contract
from .storage import digest, identifier, read_json
from .version import VERSION


ALIASES = {'original': '成片.mp4', 'subtitled': '成片_字幕版.mp4', 'subtitles': '字幕.srt'}
EDIT_FILES = ('成片.mp4', '成片_字幕版.mp4', '字幕.srt', '字幕.ass', 'recipe.json', '媒体验收.json', 'completed.json')
VIDEO_SUFFIXES = {'.mp4', '.webm', '.mov'}
MIME_TYPES = {'.mp4': 'video/mp4', '.webm': 'video/webm', '.mov': 'video/quicktime',
              '.srt': 'application/x-subrip', '.ass': 'text/x-ssa', '.json': 'application/json', '.png': 'image/png'}


def _check(status, message, **details):
    return {'status': status, 'message': message, **details}


def _sha(path):
    value = hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


def _inside(root, name):
    if not isinstance(name, (str, Path)) or not str(name):
        raise ValueError('产物路径无效。')
    candidate = Path(name)
    if not candidate.is_absolute():
        candidate = root / candidate
    path = candidate.resolve()
    if not path.is_relative_to(root) or any(part.startswith('.') for part in candidate.relative_to(root).parts):
        raise ValueError('产物不属于当前项目可交付目录。')
    return path


def inspect_media(path, verify=False):
    """Read container metadata or decode every audio/video packet to completion."""
    try:
        import av
    except ImportError:
        return {'measurement': 'unavailable'}, _check('unavailable', '当前环境缺少 PyAV，未进行媒体检查。')
    try:
        with av.open(str(path), options={'err_detect': 'explode'}) as media:
            streams = [stream for stream in media.streams if stream.type in ('video', 'audio')]
            videos = [stream for stream in streams if stream.type == 'video']
            audios = [stream for stream in streams if stream.type == 'audio']
            if not videos:
                return {}, _check('failed', '视频文件没有视频流。')
            first = videos[0]
            info = {'measurement': 'full_decode' if verify else 'container_header',
                    'width': first.width, 'height': first.height, 'frames': first.frames or None,
                    'fps': float(first.average_rate) if first.average_rate else None,
                    'duration': float(first.duration * first.time_base) if first.duration is not None else
                                float(media.duration / av.time_base) if media.duration is not None else None,
                    'audio': bool(audios), 'video_streams': len(videos), 'audio_streams': len(audios)}
            if not verify:
                return info, _check('not_checked', '仅读取容器头；未完整解码音视频。')
            counts = {stream.index: {'type': stream.type, 'frames': 0, 'samples': 0,
                                     'start': None, 'end': None, 'previous': None, 'timestamps_monotonic': True,
                                     'declared_frames': stream.frames or None} for stream in streams}
            for packet in media.demux(streams):
                record = counts[packet.stream.index]
                for frame in packet.decode():
                    record['frames'] += 1
                    timestamp = float(frame.pts * frame.time_base) if frame.pts is not None and frame.time_base else None
                    if timestamp is None or not math.isfinite(timestamp) or record['previous'] is not None and timestamp <= record['previous']:
                        record['timestamps_monotonic'] = False
                    if timestamp is not None and math.isfinite(timestamp):
                        record['start'] = timestamp if record['start'] is None else record['start']
                        record['previous'] = timestamp
                        if packet.stream.type == 'audio':
                            record['samples'] += frame.samples
                            duration = frame.samples / frame.sample_rate if frame.sample_rate else 0
                        else:
                            duration = (float(frame.duration * frame.time_base) if getattr(frame, 'duration', 0) else
                                        1 / float(packet.stream.average_rate) if packet.stream.average_rate else 0)
                        record['end'] = timestamp + duration
            primary = counts[first.index]
            info.update(frames=primary['frames'], duration=(primary['end'] - primary['start'])
                        if primary['start'] is not None and primary['end'] is not None else None,
                        streams=[{key: value for key, value in record.items() if key != 'previous'}
                                 for record in counts.values()])
            failed = [record for record in counts.values() if not record['frames'] or not record['timestamps_monotonic']
                      or record['type'] == 'video' and record['declared_frames'] and record['declared_frames'] != record['frames']]
            if failed:
                return info, _check('failed', '音视频存在空流、缺帧或缺失/非递增时间戳。')
            if not audios or any(not counts[stream.index]['samples'] for stream in audios):
                return info, _check('failed', '成片缺少可解码音频。')
            tolerance = max(.1, 2 / info['fps']) if info['fps'] else .1
            extents_match = all(abs(counts[stream.index]['start'] - primary['start']) <= tolerance and
                                abs(counts[stream.index]['end'] - primary['end']) <= tolerance for stream in audios)
            info['audio_video_extents_match'] = extents_match
            if not extents_match:
                return info, _check('failed', '音频与视频起止时间差超过容差；不检查语义同步。', tolerance_seconds=tolerance)
            return info, _check('passed', '全部音视频流已解码，帧数与时间戳检查通过；不代表台词或内容正确。')
    except Exception as exc:
        return {}, _check('failed', '媒体读取或解码失败：' + safe_message(exc))


def build_delivery(projects, pid, verify=False):
    if type(verify) is not bool:
        raise ValueError('verify 必须是布尔值。')
    project = projects.path(pid).resolve()
    artifacts, issues, by_path = [], [], {}
    decoded = {}

    def load(name):
        try:
            path = _inside(project, name)
            value = read_json(path, {})
            if not isinstance(value, dict):
                raise ValueError('记录必须是 JSON 对象。')
            return value
        except (OSError, ValueError) as exc:
            issues.append({'code': 'INVALID_RECORD', 'file': str(name), 'message': safe_message(exc)})
            return {}

    def add(name, kind, version_id=None, check_media=False):
        try:
            path = _inside(project, name)
            if not path.is_file():
                return None
            relative = path.relative_to(project).as_posix()
            if relative in by_path:
                return by_path[relative]
            stat = path.stat()
            checksum = _sha(path)
            item = {'relative_path': relative, 'local_path': str(path), 'size': stat.st_size,
                    'sha256': checksum, 'mime': MIME_TYPES.get(path.suffix.lower()) or mimetypes.guess_type(relative)[0] or 'application/octet-stream',
                    'kind': kind, 'version_id': version_id,
                    'api_url': '/api/v2/projects/' + quote(pid, safe='') + '/delivery/files/' + quote(relative, safe='/')}
            if path.suffix.lower() in VIDEO_SUFFIXES:
                cache_key = (checksum, bool(verify and check_media))
                if cache_key not in decoded:
                    decoded[cache_key] = inspect_media(path, verify=cache_key[1])
                info, check = decoded[cache_key]
                item.update(media=info, verification={**check, 'sha256': checksum,
                            'scope': 'all_audio_video_streams' if cache_key[1] else 'header_only'})
            # Do not attach verification to bytes that changed while inspected.
            after = path.stat()
            if (stat.st_size, stat.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
                item['verification'] = _check('failed', '检查期间文件发生变化，请重新读取。')
                issues.append({'code': 'ARTIFACT_CHANGED', 'file': relative})
            by_path[relative] = item
            artifacts.append(item)
            return item
        except (OSError, ValueError) as exc:
            issues.append({'code': 'ARTIFACT_UNAVAILABLE', 'message': safe_message(exc)})
            return None

    state, story = load('state.json'), load('分镜.json')
    current = load('current_edit.json')
    current_id = current.get('id')
    if current_id:
        try:
            identifier(current_id)
        except ValueError:
            issues.append({'code': 'INVALID_CURRENT_EDIT', 'message': '当前版本标识无效。'})
            current_id = None
    aliases = {key: add(name, key, current_id, check_media=True) for key, name in ALIASES.items()}
    add('字幕.ass', 'subtitle_script', current_id)
    root_report = add('媒体验收.json', 'recorded_report', current_id)
    clips = []
    for shot in story.get('shots', []):
        uid = shot.get('uid')
        record = state.get('shots_by_uid', {}).get(uid, state.get('shots', {}).get(str(shot.get('id')), {}))
        name = record.get('clip_relative') or record.get('clip')
        artifact = add(name, 'shot_clip') if name and Path(name).suffix.lower() in VIDEO_SUFFIXES else None
        clips.append({'uid': uid, 'id': shot.get('id'), 'status': record.get('status'), 'artifact': artifact,
                      'selected': uid in state.get('completed_uids', []),
                      'current_contract': bool(record.get('render_contract') == render_contract(story, shot))})
    edits = []
    try:
        edits_root = _inside(project, 'edits')
        folders = sorted(edits_root.iterdir(), key=lambda path: path.name) if edits_root.is_dir() else []
    except (ValueError, OSError) as exc:
        issues.append({'code': 'INVALID_EDIT_DIRECTORY', 'message': safe_message(exc)})
        folders = []
    for folder in folders:
        try:
            identifier(folder.name)
            folder = _inside(project, folder)
        except ValueError:
            issues.append({'code': 'INVALID_EDIT_DIRECTORY'})
            continue
        if not folder.is_dir() or not (folder / 'completed.json').is_file():
            continue
        relative = folder.relative_to(project).as_posix()
        recipe, report, completed = (load(relative + '/' + name) for name in ('recipe.json', '媒体验收.json', 'completed.json'))
        files = {name: add(relative + '/' + name, 'edit_' + name, folder.name) for name in EDIT_FILES}
        expected = completed.get('files', {})
        hashes_valid = isinstance(expected, dict) and {'成片.mp4', '媒体验收.json'} <= set(expected) and all(
            name in files and files[name] and files[name]['sha256'] == checksum for name, checksum in expected.items())
        recipe_valid = bool(recipe and report.get('edit_id') == folder.name and report.get('recipe_hash') and digest(recipe) == report['recipe_hash'])
        source_valid = bool(recipe.get('sources'))
        for source in recipe.get('sources', []):
            try:
                path = _inside(project, source.get('file', ''))
                source_valid = source_valid and path.suffix.lower() in VIDEO_SUFFIXES and path.is_file() and _sha(path) == source.get('sha256')
            except (OSError, ValueError):
                source_valid = False
        story_valid = [shot.get('uid') for shot in recipe.get('story', {}).get('shots', [])] == [shot.get('uid') for shot in story.get('shots', [])]
        if story_valid:
            story_valid = all(render_contract(recipe['story'], old) == render_contract(story, new)
                              for old, new in zip(recipe.get('story', {}).get('shots', []), story.get('shots', [])))
        linked = bool(hashes_valid and recipe_valid and source_valid)
        provenance = _check('passed' if linked else 'failed', '既有报告来源及文件哈希匹配。' if linked else '既有报告、配方或源文件的来源证据不完整或不匹配。',
                            evidence='recorded_finishing_report', recipe_hash_matches=recipe_valid,
                            completed_file_hashes_match=hashes_valid, source_hashes_match=source_valid,
                            current_story_matches=story_valid)
        index_artifact = add(relative + '/review/index.json', 'review_index', folder.name)
        index = load(relative + '/review/index.json') if index_artifact else {}
        pages = []
        for page in index.get('pages', []):
            try:
                name = Path(page.get('file', ''))
                if name.is_absolute() or name.parent.as_posix() != 'review' or name.suffix.lower() != '.png':
                    raise ValueError('审核页路径必须位于本版本 review 目录。')
                artifact = add(relative + '/' + name.as_posix(), 'review_page', folder.name)
                if artifact:
                    pages.append({'kind': page.get('kind'), 'artifact': artifact,
                                  'hash_matches': artifact['sha256'] == page.get('sha256')})
            except ValueError as exc:
                issues.append({'code': 'INVALID_REVIEW_PAGE', 'message': str(exc)})
        edits.append({'id': folder.name, 'current': folder.name == current_id, 'files': files,
                      'recorded_evidence': provenance, 'review_index': index_artifact, 'review_pages': pages,
                      'expected_frames': report.get('expected_frames'),
                      'recorded_spec': {'width': recipe.get('width'), 'height': recipe.get('height')}})
    selected = next((edit for edit in edits if edit['id'] == current_id), None)
    prior = _check('unavailable', '没有可关联的既有后期验收记录。')
    if selected:
        matching = all(artifact is None or selected['files'].get(ALIASES[key]) and
                       artifact['sha256'] == selected['files'][ALIASES[key]]['sha256'] for key, artifact in aliases.items())
        if root_report:
            matching = matching and bool(selected['files'].get('媒体验收.json') and
                                         root_report['sha256'] == selected['files']['媒体验收.json']['sha256'])
        current_evidence = selected['recorded_evidence']
        valid = matching and current_evidence['status'] == 'passed' and current_evidence['current_story_matches']
        prior = _check('passed' if valid else 'failed', '当前文件与已记录版本匹配。' if valid else '当前文件、分镜或版本记录已不一致。',
                       evidence='recorded_finishing_report', edit_id=current_id, aliases_match=bool(matching))
    elif current.get('id'):
        prior = _check('failed', '当前版本指针没有对应的完整后期版本。')
    finals = [aliases[key] for key in ('original', 'subtitled') if aliases[key]]
    verified = bool(aliases['original'] and verify and all(item.get('verification', {}).get('status') == 'passed' for item in finals))
    spec_check = _check('unavailable', '没有可核对的版本规格。')
    if verify and selected and selected['expected_frames'] is not None:
        spec_matches = all(item.get('media', {}).get('frames') == selected['expected_frames'] and
                           all(item.get('media', {}).get(key) == value for key, value in selected['recorded_spec'].items() if value is not None)
                           for item in finals)
        spec_check = _check('passed' if finals and spec_matches else 'failed', '新解码结果与版本帧数、尺寸对照。')
        verified = verified and bool(finals) and spec_matches
    busy = projects.db.busy(pid)
    complete = state.get('status') == 'complete' and not state.get('scope_complete')
    statuses = [item.get('verification', {}).get('status') for item in finals]
    media_status = ('passed' if verified else 'failed' if 'failed' in statuses else 'unavailable'
                    if not finals or 'unavailable' in statuses else 'failed' if verify else 'not_checked')
    checks = {'project_complete': _check('passed' if complete else 'failed', '项目状态是否为完整成片完成。'),
              'idle': _check('failed' if busy else 'passed', '项目是否没有排队或运行任务。'),
              'media': _check(media_status, '仅针对当前原版及存在的字幕版成片。',
                              files=[{'file': item['relative_path'], 'sha256': item['sha256']} for item in finals]),
              'recorded_provenance': prior, 'version_specification': spec_check,
              'visual_content': _check('not_checked', '尚未人工或视觉核对动作、构图和遮罩。'),
              'dialogue_content': _check('not_checked', '未试听或逐字转录；音频可解码不代表台词正确。'),
              'subtitle_content': _check('not_checked', '未核对字幕文字、时间与实际发音。')}
    result = {'schema_version': 1, 'application_version': VERSION, 'project_id': pid,
              'revision': projects.revision(pid), 'state': state.get('status'), 'busy': busy,
              'scope': 'project' if complete else 'selected_shots' if state.get('scope_complete') else 'partial',
              'version_id': current_id, 'artifacts': artifacts, 'aliases': aliases, 'shot_clips': clips,
              'current_edit': selected, 'edits': edits, 'checks': checks, 'issues': issues,
              'media_verified': verified, 'verification_scope': 'current_final_videos',
              'delivery_scope': 'technical_integrity_only', 'content_review_complete': False,
              'ready_for_delivery': bool(complete and not busy and verified and prior['status'] != 'failed')}
    result['fingerprint'] = digest(result)
    return result
