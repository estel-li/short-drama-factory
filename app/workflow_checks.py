"""Cheap, read-only workflow checks before LLM calls, engine startup or GPU work."""
from .quality import story_report
from .video_workflows import validate_workflow, workflow_catalog


def workflow_report(story, options, config, resolve, select_mode):
    import pipeline
    report = story_report(story, options)
    preset = config.get('profiles', {}).get(options.profile)
    if not preset:
        report['issues'].append({'kind': 'workflow', 'severity': 'error', 'message': '所选工作流已不存在，请重新选择。'})
        report['ready'] = False
        return report
    workflow = preset.get('workflow', 'native')
    report['workflow'] = workflow
    for shot, row in zip(story['shots'], report['shots']):
        def issue(message, severity='error'):
            report['issues'].append({'kind': 'workflow', 'severity': severity,
                'uid': shot.get('uid'), 'shot_id': shot['id'], 'message': f"镜头 {shot['id']}：{message}"})
        try:
            # Existing native projects may use references extracted at render time.
            # Keep their legacy readiness semantics; new recipes use strict inputs.
            if workflow == 'native':
                continue
            bindings = resolve(shot, story)
            mode = select_mode(shot, options, bindings)
            if (mode == 'T2VA' and shot.get('characters') and options.auto_reference
                    and shot.get('mode', 'auto') == 'auto' and options.h3_mode == 'auto'
                    and 'Ref2VA' not in workflow_catalog().get(workflow, {}).get('supported_modes', [])):
                raise ValueError('自动角色参考会让后续镜头切换到此工作流不支持的 Ref2VA。请关闭“自动角色参考”、明确选择 T2VA／关键帧模式，或改用 PDD。')
            validate_workflow(preset, shot, bindings, mode)
            count = pipeline.frames(shot['duration'])
            row.update(mode=mode, aligned_frames=count, aligned_seconds=count / 24,
                       output_size=list(pipeline.output_canvas(preset, options.ratio)))
            if workflow == 'h3-audio-drive':
                duration = (bindings.get('source_audio') or {}).get('duration')
                if duration is not None and duration - preset.get('source_start_seconds', 0) < count / 24:
                    issue('原声音轨短于帧对齐后的镜长，尾部将补静音。', 'warning')
            if workflow in ('h3-foley', 'h3-canny-control', 'h3-motion-context'):
                source = bindings.get('source_video') or {}
                if source.get('fps') is not None and abs(source['fps'] - 24) > .01:
                    raise ValueError('源片不是 24fps，请从素材页重新上传以规范帧率。')
                if source.get('frames') is None:
                    issue('源片未提供可靠帧数，执行时会再次检查，不能承诺镜长足够。', 'warning')
                if workflow == 'h3-motion-context' and not source.get('include_audio'):
                    issue('源片没有音轨，接续声音将从静音上下文开始。', 'warning')
            if workflow.startswith('h3-') and shot.get('dialogue') and workflow in ('h3-foley', 'h3-audio-drive'):
                issue('请核对台词与实际原声／拟音要求一致；仅编辑对白文字不会修改锁定的原声。', 'warning')
            if preset.get('megapixels', .4) > .6 or (
                workflow == 'pdd-upscale' and preset.get('upscale_by', 1.25) > 1.25):
                issue('当前分辨率或放大倍数高于 16GB 起步配置，建议先短镜试跑。', 'warning')
        except (ValueError, OSError) as exc:
            issue(str(exc))
    report['ready'] = not any(i['severity'] == 'error' for i in report['issues'])
    return report
