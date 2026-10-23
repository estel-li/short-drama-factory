"""Read-only execution planning. No engine startup, upload, download or model calls.

Cache observations deliberately do not promise a cache hit: the renderer signs
its materialized graph, input pixels, model versions and continuity source clip.
The planner never invokes the mutating graph/reference preparation path.
"""
from __future__ import annotations

import copy
import hashlib
from pathlib import Path

from .contracts import ContractError
from .continuity import enabled
from .execution_policy import validate_external_story
from .quality import render_contract_matches
from .storage import digest, read_json
from .workflow_checks import workflow_report


def file_evidence(path, root=None):
    """Hash actual bytes, not a possibly stale manifest checksum."""
    path = Path(path)
    if root is not None and not path.resolve().is_relative_to(Path(root).resolve()):
        return {'exists': False, 'error': 'outside_project'}
    if not path.is_file():
        return {'exists': False}
    sha = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            sha.update(block)
    return {'exists': True, 'size': path.stat().st_size, 'sha256': sha.hexdigest()}


def clip_evidence(project, record):
    name = record.get('clip_relative') or record.get('clip')
    if not name:
        return {'exists': False}
    path = Path(name)
    if not path.is_absolute():
        path = project / path
    return file_evidence(path, project)


def _model_observations(renderer, profile, modes):
    """Local file stats only. Missing/remote models require separate preparation."""
    from .rendering import ROLES
    from .video_workflows import LIGHTX2V_8, PDD_FL, PDD_REF, UPSCALER
    modes = set(modes)
    if not modes:
        return []
    names = dict(renderer)
    preset = renderer.get('profiles', {}).get(profile, {})
    workflow = preset.get('workflow', 'native')
    required = {'text_encoder', 'video_vae', 'audio_vae'}
    if 'Ref2VA' in modes:
        required.add('ref_model')
        if workflow == 'native' and preset.get('turbo'):
            required.add('ref_lora')
    if modes - {'Ref2VA'}:
        required.add('fl_model')
        if workflow == 'native' and preset.get('turbo'):
            required.add('fl_lora')
    roles = {role: ROLES[role] for role in required}
    if workflow == 'lightx2v-8':
        roles['workflow_lora'] = 'loras'
        names['workflow_lora'] = preset.get('workflow_lora') or LIGHTX2V_8
    elif workflow.startswith('pdd'):
        if modes - {'Ref2VA'}:
            roles['pdd_fl'] = 'pdd_acc'
        if 'Ref2VA' in modes:
            roles['pdd_ref'] = 'pdd_acc'
        names.update(pdd_fl=preset.get('pdd_fl') or PDD_FL, pdd_ref=preset.get('pdd_ref') or PDD_REF)
        if workflow == 'pdd-upscale':
            roles['upscaler'] = 'latent_upscale_models'
            names['upscaler'] = preset.get('upscale_model') or UPSCALER
    elif workflow == 'h3-canny-control':
        from .h3_advanced import CONTROL_MODEL
        roles['control_model'] = 'model_patches'
        names['control_model'] = preset.get('control_model') or CONTROL_MODEL
    extras = []
    runtime = renderer.get('runtime_root')
    if renderer.get('extra_model_paths_file'):
        extras.append(Path(renderer['extra_model_paths_file']))
    elif runtime:
        extras.append(Path(runtime) / 'extra_model_paths.yaml')
    if runtime:
        extras.append(Path(runtime) / 'data/video-workflow-paths.yaml')
    groups = []
    for extra in extras:
        if extra.is_file():
            import yaml
            value = yaml.safe_load(extra.read_text(encoding='utf-8')) or {}
            if isinstance(value, dict):
                groups.extend(group for group in value.values() if isinstance(group, dict))
    result = []
    for role, category in sorted(roles.items()):
        name = names.get(role)
        if not name:
            continue
        item = {'role': role, 'category': category, 'name': name, 'availability': 'unknown'}
        if renderer.get('mode') != 'remote' and renderer.get('comfy_dir'):
            roots = [Path(renderer['comfy_dir']) / 'models' / category]
            for group in groups:
                for folder in str(group.get(category, '')).splitlines():
                    if folder.strip():
                        root = Path(group.get('base_path', renderer['comfy_dir'])) / folder.strip()
                        roots.insert(0, root) if group.get('is_default') else roots.append(root)
            paths = [folder / name for folder in roots if (folder / name).is_file()]
            if paths:
                stat = paths[0].stat()
                item.update(availability='local', path=str(paths[0].resolve()), size=stat.st_size, mtime_ns=stat.st_mtime_ns)
            else:
                item['availability'] = 'missing'
        result.append(item)
    return result


def _dependencies(story, references, auto_reference):
    """Follow the renderer's first single-character capture ownership rules."""
    shots = story.get('shots', [])
    by_uid = {shot['uid']: shot for shot in shots}
    by_id = {shot['id']: shot['uid'] for shot in shots}
    edges, owners = [], {}
    if auto_reference:
        for cid, reference in references.items():
            if not reference:
                continue
            if not isinstance(reference, dict) or reference.get('shot_id') == 0:
                owners[cid] = None  # Explicit/pinned reference cannot be replaced by capture.
            else:
                owners[cid] = reference.get('shot_uid') or by_id.get(reference.get('shot_id'))
        for shot in shots:
            cast = shot.get('characters', [])
            if len(cast) == 1 and cast[0] not in owners:
                owners[cast[0]] = shot['uid']
    for index, shot in enumerate(shots):
        if enabled(shot) and index:
            edges.append({'source_uid': shots[index - 1]['uid'], 'target_uid': shot['uid'], 'kind': 'previous_last_frame'})
        elif auto_reference:
            for cid in shot.get('characters', []):
                owner = owners.get(cid)
                if owner in by_uid and owner != shot['uid']:
                    # Existing captures can also point forward after a user reorder.
                    # Conservatively include these consumers in dependency closure.
                    edges.append({'source_uid': owner, 'target_uid': shot['uid'],
                                  'kind': 'captured_character_reference', 'character': cid})
    return edges


def build_plan(projects, assets, content, config, pid, request, revision):
    """Return a reproducible plan from current persisted inputs, without writes.

    ``uids`` absent means all shots; an explicit empty selection is invalid.
    Parent execution must compare both revision and input_fingerprint, and enforce
    affected_uids at the renderer boundary before any generation.
    """
    request = {key: copy.deepcopy(value) for key, value in request.items() if value is not None}
    action = request.get('action', 'render')
    policy = request.get('internal_text', 'forbid')
    regenerate = request.get('regenerate', False)
    if action not in ('render', 'finish', 'plan') or policy not in ('forbid', 'allowed') or type(regenerate) is not bool:
        raise ContractError('INVALID_EXECUTION_REQUEST', 'action、internal_text 或 regenerate 无效。')
    if regenerate and action != 'render':
        raise ContractError('INVALID_EXECUTION_REQUEST', '仅 render 支持 regenerate。')
    project = projects.path(pid)
    options = projects.options(project)
    story = read_json(project / '分镜.json', {}) or {}
    state = read_json(project / 'state.json', {})
    references = read_json(project / 'references.json', {})
    manifest = read_json(project / 'assets.json', {})
    renderer = config.renderer_config()
    snapshot = read_json(project / 'renderer_snapshot.json', {})
    shots = story.get('shots', [])
    known = [shot['uid'] for shot in shots]
    requested = request.get('uids', known)
    if not isinstance(requested, list) or any(not isinstance(uid, str) for uid in requested) or ('uids' in request and not requested):
        raise ContractError('INVALID_EXECUTION_REQUEST', 'uids 必须是非空镜头 UID 列表。')
    if set(requested) - set(known):
        raise ContractError('SHOT_NOT_FOUND', '所选镜头 UID 不存在。', status=404,
                            details=[{'field': 'uids', 'missing': sorted(set(requested) - set(known))}])
    requested = [uid for uid in known if uid in requested]
    affected, reasons, blocked, warnings = set(requested), {}, [], []
    for uid in requested:
        reasons[uid] = ['requested_regeneration' if regenerate else 'requested']
    records = state.get('shots_by_uid')
    records = records if records else {shot['uid']: (state.get('shots') or {}).get(str(shot['id']), {}) for shot in shots}
    clips = {uid: clip_evidence(project, records.get(uid, {})) for uid in known}
    current_clips = {shot['uid']: bool(clips[shot['uid']].get('exists')
                                     and records.get(shot['uid'], {}).get('status') == 'done'
                                     and render_contract_matches(records.get(shot['uid'], {}).get('render_contract'), story, shot))
                     for shot in shots}
    for index, shot in enumerate(shots):
        if not enabled(shot):
            continue
        previous_uid = shots[index - 1]['uid'] if index else None
        receipt = records.get(shot['uid'], {}).get('first_frame', {})
        current_clips[shot['uid']] = bool(current_clips[shot['uid']] and previous_uid
            and current_clips.get(previous_uid) and receipt.get('source_shot_uid') == previous_uid
            and receipt.get('source_clip_sha256') == clips[previous_uid].get('sha256'))
    dependencies = _dependencies(story, references, options.auto_reference) if action == 'render' else []
    if action == 'render':
        changed = True
        while changed:
            changed = False
            for edge in dependencies:
                source, target = edge['source_uid'], edge['target_uid']
                if source in affected and target not in affected:
                    affected.add(target)
                    reasons.setdefault(target, []).append(edge['kind'] + ':' + source)
                    changed = True
                if target in affected and source not in affected and not current_clips[source]:
                    affected.add(source)
                    reasons.setdefault(source, []).append('missing_or_stale_dependency_clip:' + target)
                    changed = True
    if options.reference_images.enabled and action == 'plan':
        # This existing pipeline stage is project-wide and may rewrite bindings.
        for uid in known:
            if uid not in affected:
                affected.add(uid)
                reasons.setdefault(uid, []).append('project_reference_image_preparation')
        if policy == 'forbid':
            blocked.append({'code': 'REFERENCE_PREPARATION_REQUIRES_EXPLICIT_CONTENT',
                            'field': 'settings.reference_images.enabled',
                            'message': '自动参考图阶段可能生成图片、优化提示词并改写绑定。请先显式生成/采用参考图，并关闭 reference_images.enabled 后重新计划。'})
    elif options.reference_images.enabled and action == 'render':
        warnings.append({'code': 'REFERENCE_PREPARATION_SKIPPED',
                         'field': 'settings.reference_images.enabled',
                         'message': '本次严格 render 跳过自动参考图准备，仅采用现有绑定。需要新参考图时，请先显式完成图片阶段，再重新计划。'})
    affected_uids = [uid for uid in known if uid in affected]
    from .director_styles import style_check
    director = style_check(projects, pid)
    if director['selected']:
        blocked.extend(director['issues'])
        warnings.append({'code': 'DIRECTOR_CONTENT_NOT_VERIFIED', 'message': director.get('note', '导演风格内容尚未验收。')})
        if director.get('timing') and not director['timing']['relative_rhythm_matches']:
            warnings.append({'code': 'DIRECTOR_TIMING_ADAPTATION', 'message': '计划中的相对镜头时长偏离参考结构；先生成原片，再明确选择 edit_ranges 或调整镜长，最终对照实际成片验收。'})
    if not shots and (action != 'plan' or policy == 'forbid'):
        blocked.append({'code': 'EXTERNAL_CONTENT_REQUIRED', 'field': 'story', 'message': '请先提供分镜，或使用允许内部文字调用的 plan 阶段。'})

    resolved = {}
    positions = {shot['uid']: index for index, shot in enumerate(shots)}
    character_names = {character['id']: character.get('name', character['id']) for character in story.get('characters', [])}
    for shot in shots:
        if shot['uid'] not in affected or action == 'finish':
            continue
        try:
            bindings = assets.resolve(project, shot, story, inspect_media=True)
            if options.auto_reference and not enabled(shot) and not any(bindings.values()):
                # Model the same fallback as Worker.resolve without calling the
                # mutating Runner.references/capture_reference/upload helpers.
                auto_images = []
                for cid in shot.get('characters', []):
                    ref = references.get(cid)
                    edge = next((edge for edge in dependencies if edge['target_uid'] == shot['uid']
                                 and edge.get('character') == cid), None)
                    source = edge['source_uid'] if edge else None
                    if isinstance(ref, dict) and (ref.get('shot_uid') == shot['uid'] or
                            not ref.get('shot_uid') and ref.get('shot_id', 0) >= shot['id']):
                        continue
                    file = None
                    if isinstance(ref, dict) and ref.get('local_file'):
                        file = (project / ref['local_file'], project)
                    elif ref and renderer.get('comfy_dir'):
                        root = Path(renderer['comfy_dir']) / 'input'
                        name = ref.get('image') if isinstance(ref, dict) else ref
                        if name:
                            file = (root / name, root)
                    observed = file_evidence(*file) if file else {}
                    planned_capture = source is not None and positions[source] < positions[shot['uid']]
                    if observed.get('exists') or planned_capture:
                        auto_images.append({'id': 'auto-' + str(len(auto_images) + 1), 'type': 'image',
                                            'name': character_names.get(cid, cid), 'character': cid,
                                            'source_shot_uid': source, 'sha256': observed.get('sha256')})
                if auto_images:
                    bindings['images'] = auto_images[:2]
            resolved[shot['uid']] = bindings
        except (ValueError, OSError) as exc:
            blocked.append({'code': 'INVALID_BINDINGS', 'uid': shot['uid'], 'message': str(exc)})
    resolver = lambda shot, unused_story: copy.deepcopy(resolved.get(shot['uid'], {}))
    check = {'ready': True, 'issues': []}
    if shots and action != 'finish':
        scoped_story = {**story, 'shots': [shot for shot in shots if shot['uid'] in affected]}
        check = workflow_report(scoped_story, options, renderer, resolver, content.mode)
        blocked.extend({'code': 'WORKFLOW_BLOCKED', **issue} for issue in check['issues'] if issue.get('severity') == 'error')
        warnings.extend(issue for issue in check['issues'] if issue.get('severity') != 'error')
        if action == 'render' or policy == 'forbid':
            try:
                validate_external_story(story, options, resolver, content.mode, uids=affected_uids)
            except ContractError as exc:
                blocked.append({'code': exc.code, 'message': str(exc), 'details': exc.details})
    asset_files = {aid: file_evidence(project / item['file'], project) for aid, item in manifest.items() if item.get('file')}
    reference_files = {}
    for cid, ref in references.items():
        name = ref.get('local_file') if isinstance(ref, dict) else None
        image = ref.get('image') if isinstance(ref, dict) else ref
        if name:
            reference_files[cid] = file_evidence(project / name, project)
        elif image and renderer.get('comfy_dir'):
            root = Path(renderer['comfy_dir']) / 'input'
            reference_files[cid] = file_evidence(root / image, root)
    selected_modes = set()
    for shot in shots:
        if shot['uid'] in affected and shot['uid'] in resolved:
            try:
                selected_modes.add(content.mode(shot, options, resolved[shot['uid']]))
            except ValueError:
                pass  # Already reported by workflow/external-content validation.
    models = _model_observations(renderer, options.profile, selected_modes) if action == 'render' else []
    if any(item['availability'] == 'missing' for item in models):
        blocked.append({'code': 'MODEL_FILES_MISSING', 'field': 'environment.models',
                        'message': '本地缺少所选模型。请单独准备环境后重新计划；本计划不授权下载模型。'})
    if any(item['availability'] == 'unknown' for item in models):
        warnings.append({'code': 'MODEL_AVAILABILITY_UNKNOWN', 'message': '远程模型状态未联网核验；不能保证模型可用或缓存命中。'})

    rows = []
    from pipeline import FPS, frames, output_canvas
    preset = renderer.get('profiles', {}).get(options.profile, {})
    for shot in shots:
        uid, record = shot['uid'], records.get(shot['uid'], {})
        cache = 'missing'
        contract_matches = bool(record.get('render_contract') and render_contract_matches(record['render_contract'], story, shot))
        render_option_keys = ('profile', 'ratio', 'seed', 'h3_mode', 'auto_reference', 'reference_images',
                              'dialogue_language', 'narration', 'music', 'missing_reference')
        current_options = options.model_dump()
        snapshot_matches = bool(snapshot and all(snapshot.get('settings', {}).get(key) == current_options.get(key)
                                                 for key in render_option_keys)
                                and snapshot.get('environment', {}).get('profiles', {}).get(options.profile) == preset
                                and snapshot.get('environment', {}).get('attention') == renderer.get('attention'))
        if record.get('status') == 'done' and clips[uid].get('exists'):
            cache = 'candidate_reuse' if contract_matches and snapshot_matches else 'unknown'
        if regenerate and uid in affected:
            cache = 'regenerate'
        if uid in affected and shot.get('locked') and (regenerate or any(r != 'requested' for r in reasons.get(uid, []))):
            blocked.append({'code': 'DEPENDENCY_LOCKED', 'uid': uid, 'message': '执行范围包含锁定镜头，请解锁后重新计划。'})
        if action == 'finish' and not current_clips[uid]:
            blocked.append({'code': 'FINISH_INPUT_NOT_READY', 'uid': uid, 'message': '后期需要每镜已完成且与当前分镜匹配的视频。'})
        if action == 'render' and uid not in affected and not current_clips[uid]:
            warnings.append({'code': 'OUTSIDE_SCOPE_CLIP_NOT_READY', 'uid': uid,
                             'message': '范围外镜头尚未有匹配的已完成视频；本次仅交付所选镜头，不会合成完整项目或标记项目完成。'})
        elif action == 'render' and uid not in affected:
            warnings.append({'code': 'OUTSIDE_SCOPE_CLIP_UNVERIFIED', 'uid': uid,
                             'message': '范围外镜头可作为已有内容来源，但本次不校验其完整渲染参数和媒体规格；仅交付所选镜头，不自动合片。'})
        count = frames(shot['duration'])
        if shot.get('edit_ranges') is not None:
            try:
                from .editplan import edit_plan
                validation_shot = copy.deepcopy(shot)
                # Speech detection happens during finishing; retain authored
                # timings when available and otherwise validate only the ranges.
                if not shot.get('dialogue_timings'):
                    validation_shot['dialogue'] = []
                index = positions[uid]
                edit_plan(validation_shot, count, {}, 'original', preserve_start=enabled(shot),
                          preserve_end=index + 1 < len(shots) and enabled(shots[index + 1]))
            except (ValueError, RuntimeError, TypeError, KeyError) as exc:
                blocked.append({'code': 'EDIT_RANGE_INVALID', 'uid': uid, 'field': 'edit_ranges', 'message': str(exc)})
        rows.append({'uid': uid, 'affected': uid in affected, 'reasons': reasons.get(uid, []), 'cache': cache,
                     'cache_guaranteed': False, 'has_clip': clips[uid].get('exists', False),
                     'source_valid': current_clips[uid], 'assembly_ready': False,
                     'assembly_verification': 'required_at_execution' if uid in affected else 'outside_scope_unverified',
                     'contract_matches': contract_matches, 'renderer_snapshot_matches': snapshot_matches,
                     'requested_seconds': shot['duration'], 'aligned_frames': count, 'aligned_seconds': count / FPS})

    effects = [{'kind': 'cpu', 'action': 'validate_and_fingerprint', 'certainty': 'required'}]
    # Proper subsets are always pilot/scoped work. Even a matching authored
    # contract does not prove outside clips use today's ratio/profile/models.
    can_assemble = action != 'render' or affected == set(known)
    finishing_settings = {**options.model_dump(), **(read_json(project / 'finishing-settings.json', {}) or {})}
    needs_speech = any(shot.get('dialogue') for shot in shots) and (
        finishing_settings.get('edit_preset', 'original') != 'original'
        or finishing_settings.get('subtitle_alignment', 'approximate') == 'speech'
        or any(shot.get('edit_ranges') and shot.get('dialogue') and not shot.get('dialogue_timings') for shot in shots))
    if (action == 'finish' or action == 'render' and can_assemble) and needs_speech:
        runtime = Path(renderer.get('runtime_root') or getattr(config, 'root', Path(__file__).resolve().parents[1]))
        manifest_path = runtime / 'manifests/quality.json'
        if not manifest_path.is_file():
            manifest_path = Path(__file__).resolve().parents[1] / 'manifests/quality.json'
        speech_model = read_json(manifest_path)['model']
        speech_path = runtime / 'data/quality' / speech_model['filename']
        evidence = file_evidence(speech_path)
        verified = evidence.get('size') == speech_model['size'] and evidence.get('sha256') == speech_model['sha256']
        models.append({'role': 'speech_model', 'category': 'quality', 'name': speech_model['filename'],
                       'availability': 'local' if verified else 'missing', 'path': str(speech_path),
                       'expected_size': speech_model['size'], 'expected_sha256': speech_model['sha256'],
                       'observed': evidence})
        effects.append({'kind': 'cpu', 'action': 'speech_activity_detection', 'certainty': 'required'})
        if not verified:
            blocked.append({'code': 'SPEECH_MODEL_MISSING', 'field': 'environment.speech_model',
                            'message': '合片/后期需要已校验的 CPU 语音检测模型，请显式准备该资源后重新计划。',
                            'size': speech_model['size'], 'filename': speech_model['filename']})
    if action == 'finish' or action == 'render' and can_assemble:
        effects.append({'kind': 'cpu', 'action': 'assemble_subtitles_and_review', 'certainty': 'required'})
    if action == 'render':
        effects.append({'kind': 'gpu', 'action': 'video_generation', 'uids': affected_uids,
                        'certainty': 'possible', 'maximum_shots': len(affected_uids), 'minimum_shots': 0})
        if dependencies:
            effects.append({'kind': 'cpu', 'action': 'extract_and_upload_reference_frames', 'certainty': 'possible'})
    if action == 'plan' and options.reference_images.enabled:
        effects.append({'kind': 'gpu', 'action': 'reference_image_generation', 'certainty': 'possible', 'scope': 'project'})
        if options.reference_images.optimize:
            effects.append({'kind': 'text', 'action': 'reference_image_prompt_optimization', 'certainty': 'possible'})
    if policy == 'allowed' and action == 'plan':
        scoped_text = bool(affected_uids) and affected != set(known)
        effects.append({'kind': 'text',
                        'action': 'compile_selected_prompts' if scoped_text else 'fill_or_compile_story_and_prompts',
                        'certainty': 'possible', 'scope': 'selected_shots' if scoped_text else 'project',
                        'uids': affected_uids})
    effects.append({'kind': 'download', 'action': 'none_authorized', 'certainty': 'required',
                    'missing_models': [item['name'] for item in models if item['availability'] == 'missing'],
                    'requirements': [{'name': item['name'], 'bytes': item.get('expected_size')}
                                     for item in models if item['availability'] == 'missing']})
    # Whitelist renderer settings: credentials and arbitrary provider extras never enter the plan.
    render_settings = {key: renderer.get(key) for key in ('mode', 'attention', 'profiles', 'fl_model', 'ref_model',
        'text_encoder', 'video_vae', 'audio_vae', 'fl_lora', 'ref_lora', 'comfy_dir', 'comfy_url')}
    environment_fingerprint = digest({'renderer': render_settings, 'model_files': models})
    inputs = {'story': story, 'settings': options.model_dump(), 'finishing': read_json(project / 'finishing-settings.json'),
              'director_style': director,
              'assets': manifest, 'asset_files': asset_files, 'references': references, 'reference_files': reference_files,
              'clips': clips, 'renderer': render_settings, 'renderer_snapshot': snapshot, 'model_files': models,
              'records': {uid: {key: records.get(uid, {}).get(key) for key in ('status', 'signature', 'render_contract', 'model_versions', 'first_frame')}
                          for uid in known},
              'outline': file_evidence(project / '大纲.txt'), 'outline_result': file_evidence(project / 'outline.json')}
    fingerprint = digest(inputs)
    plan = {'version': 1, 'project_id': pid, 'revision': revision, 'action': action, 'internal_text': policy,
            'strict': action == 'render', 'effective_internal_text': 'forbid' if action == 'render' else policy,
            'regenerate': regenerate, 'requested_uids': requested, 'affected_uids': affected_uids,
            'reasons': reasons, 'dependencies': dependencies, 'blocked': blocked, 'warnings': warnings,
            'ready': not blocked, 'input_fingerprint': fingerprint, 'shots': rows, 'models': models,
            'modes': sorted(selected_modes),
            'environment_fingerprint': environment_fingerprint,
            'effects': effects, 'workflow': check.get('workflow', preset.get('workflow', 'native')),
            'director_style': director,
            'expected': {'fps': FPS, 'aligned_seconds': sum(row['aligned_seconds'] for row in rows),
                         'delivery_scope': 'project' if can_assemble else 'selected_shots',
                         'output_size': list(output_canvas(preset, options.ratio)) if preset else None},
            'estimates': {'wall_seconds': None, 'cost': None, 'reason': '未执行生成；缺少足够可比历史数据。'},
            'limits': ['缓存仅为候选，执行时依据完整图、真实像素与模型版本再次校验。',
                       'source_valid 仅核对内容契约与依赖收据，不代替媒体解码或当前渲染参数验收。',
                       '计划不检查运行中的 GPU，不联网查询模型，不授权下载。']}
    plan['plan_id'] = digest(plan)
    return plan
