"""H3-specific media recipes; tensor operations live in the ComfyUI node pack."""
from __future__ import annotations

import math

CONTROL_MODEL = 'minimax_h3_fun_controlnet_union_pruned_int8_convrot.safetensors'

RECIPES = {
    'h3-audio-drive': {'label': 'H3 音频驱动数字人 · 保留原声', 'slots': ['source_audio'],
        'description': '将真实音轨锁进主音画潜空间，生成画面后使用原音轨合成；可加首帧控制人物。'},
    'h3-foley': {'label': 'H3 锁画面拟音 · 重新生成声音', 'slots': ['source_video'],
        'description': '锁定源视频潜空间，只生成声音；成片直接采用源画面，避免 VAE 重建改变画面。'},
    'h3-keyframe-guide': {'label': 'H3 中段关键帧导演 · 时间点引导', 'slots': ['guide_image'],
        'description': '把引导图锚定在片段中间的指定位置；可以同时绑定首帧和尾帧。'},
    'h3-motion-context': {'label': 'H3 多帧音画接续 · 延续动作', 'slots': ['source_video'],
        'description': '接收前片末尾的一段连续画面和声音，生成后去掉重复头部，按目标帧数交付。'},
    'h3-canny-control': {'label': 'H3 视频轮廓控制 · 保留动作结构', 'slots': ['source_video'],
        'description': '逐帧提取源片轮廓，通过 H3 Fun ControlNet 保持构图和动作结构，重新生成风格与内容。'},
}

PROFILES = {key: {'label': spec['label'], 'workflow': key, 'megapixels': 0.4,
                 'steps': 12, 'turbo': False, 'sampler': 'euler'} for key, spec in RECIPES.items()}


def validate_inputs(workflow, shot, bindings, mode):
    spec = RECIPES[workflow]
    for slot in spec['slots']:
        if not bindings.get(slot):
            names = {'source_audio': '驱动原声', 'source_video': '工作流源视频', 'guide_image': '中段引导图'}
            raise ValueError(f"{spec['label']}需要绑定“{names[slot]}”。")
    if shot.get('use_previous_last_frame'):
        raise ValueError('高级媒体工作流请关闭旧的“首帧接续”，在工作流素材中指定来源。')
    if workflow == 'h3-foley' and mode != 'T2VA':
        raise ValueError('锁画面拟音使用文字模式，画面由工作流源视频提供；请将 H3 模式设为 T2VA。')
    if workflow == 'h3-canny-control' and mode == 'Ref2VA':
        raise ValueError('视频轮廓控制使用 FL2VA 主干，请使用文字或关键帧模式。')
    if workflow == 'h3-motion-context' and (mode not in ('T2VA','Ref2VA') or bindings.get('first_frame') or bindings.get('last_frame')):
        raise ValueError('多帧接续从源片末尾开始，请移除独立首尾帧并选择 T2VA 或 Ref2VA；避免覆盖接续开场或裁掉尾帧目标。')


def build(graph, preset, shot, bindings, mode):
    """Compose actual media-conditioned graphs, retaining staged-cache boundaries."""
    from .video_workflows import replace_link
    workflow = preset['workflow']
    validate_inputs(workflow, shot, bindings, mode)
    base = graph['7']['inputs']
    width, height, target = (base[k] for k in ('width', 'height', 'length'))
    offset = preset.get('source_start_seconds', 0)

    def node(nid, kind, **inputs):
        graph[str(nid)] = {'class_type': kind, 'inputs': inputs}

    def file(slot):
        value = bindings[slot].get('comfy_file')
        if not value:raise ValueError('工作流素材尚未上传到 ComfyUI。')
        return value

    def audio_input(nid):
        node(nid, 'LoadAudio', audio=file('source_audio'))
        node(nid+1, 'DramaH3AudioInput', audio=[str(nid), 0], start_seconds=offset, frames=target, fps=24)
        return [str(nid+1), 0]

    def video_input(nid, count=target, tail=False):
        node(nid, 'LoadVideo', file=file('source_video'))
        node(nid+1, 'GetVideoComponents', video=[str(nid), 0])
        node(nid+2, 'DramaH3VideoInput', images=[str(nid+1), 0], audio=[str(nid+1), 1],
             fps=[str(nid+1), 2], width=width, height=height, frames=count,
             start_seconds=offset, tail=tail)
        return [str(nid+2), 0], [str(nid+2), 1]

    if workflow == 'h3-canny-control':
        images, _ = video_input(60)
        node(63, 'Canny', image=images, low_threshold=preset.get('canny_low', 0.2), high_threshold=preset.get('canny_high', 0.5))
        node(64, 'ModelPatchLoader', name=preset.get('control_model') or CONTROL_MODEL)
        node(65, 'MiniMaxH3FunControlNetApply', model=graph['9']['inputs']['model'], model_patch=['64', 0],
             vae=['3', 0], control_video=['63', 0], strength=preset.get('control_strength', 0.7),
             start_percent=preset.get('control_start', 0), end_percent=preset.get('control_end', 0.9))
        graph['9']['inputs']['model'] = ['65', 0]
        return graph

    # Keep the stock H3 encoder intact, then cache the prepared conditioning AND
    # masked AV latent. Replacing this with an empty latent would silently unlock
    # source audio/video on the sampling stage.
    graph['69'] = graph.pop('7')
    replace_link(graph, ['7', 0], ['69', 0])
    replace_link(graph, ['7', 1], ['69', 1])
    positive, latent = ['69', 0], ['69', 1]
    if workflow == 'h3-audio-drive':
        audio = audio_input(60)
        node(63, 'DramaH3AudioDrive', latent=latent, audio=audio, audio_vae=['4', 0])
        latent = ['63', 0]
        graph['15']['inputs']['audio'] = audio_input(90)
    elif workflow == 'h3-foley':
        images, _ = video_input(60)
        node(63, 'DramaH3FoleyLatent', latent=latent, images=images, vae=['3', 0])
        latent = ['63', 0]
        graph['15']['inputs']['images'] = video_input(90)[0]
    elif workflow == 'h3-keyframe-guide':
        node(60, 'LoadImage', image=file('guide_image'))
        node(61, 'MiniMaxH3AddGuide', positive=positive, latent=latent, vae=['3', 0],
             image=['60', 0], frame_idx=round((target-1)*preset.get('guide_position', 0.5)))
        positive = ['61', 0]
    elif workflow == 'h3-motion-context':
        context = preset.get('context_frames', 22)
        generation = target + math.ceil(context/17)*17
        if generation > 362:raise ValueError('接续上下文与目标时长合计超过 H3 帧数限制，请缩短镜头。')
        graph['69']['inputs']['length'] = generation
        images, audio = video_input(60, context, True)
        node(63, 'MiniMaxH3MotionContext', conditioning=positive, latent=latent, vae=['3', 0],
             context_length=str(context), audio_context_length=preset.get('audio_context_frames', 18),
             context_frames=images, context_audio=audio, audio_vae=['4', 0])
        positive = ['63', 0]
        node(90, 'MiniMaxH3MotionContextTrim', images=['13', 0], audio=['14', 0], trim_frames=context,
             fps=24, match_tail=True)
        node(91, 'DramaH3TrimAV', images=['90', 0], audio=['90', 1], frames=target, fps=24)
        graph['15']['inputs'].update(images=['91', 0], audio=['91', 1])
    node(7, 'DramaH3StageInputs', conditioning=positive, latent=latent,
         width=width, height=height, length=graph['69']['inputs']['length'])
    graph['9']['inputs']['conditioning'] = ['7', 0]
    graph['12']['inputs']['latent_image'] = ['7', 1]
    return graph
