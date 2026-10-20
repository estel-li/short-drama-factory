"""Advanced H3 recipes with native graphs and explicit staged-cache boundaries."""
from __future__ import annotations
import copy

LIGHTX2V_8 = 'minimax_h3_fl2v_turbo_8step_v1.0_768p_comfyui_bf16.safetensors'
PDD_FL = 'minimax_h3_fl2va_pdd_acc_8step_comfyui.safetensors'
PDD_REF = 'minimax_h3_ref2va_pdd_acc_8step_comfyui.safetensors'
UPSCALER = 'minimax_h3_latent_upscaler_3d_fp16.safetensors'

BUILTIN_PROFILES = {
    'lightx2v-8': {'label': 'LightX2V 8步 · 稳定动作 / 0.4MP', 'workflow': 'lightx2v-8', 'megapixels': 0.4, 'steps': 8, 'turbo': True, 'sampler': 'res_multistep'},
    'pdd-8': {'label': 'PDD Acc 8步 · 音画加速 / 0.4MP', 'workflow': 'pdd-8', 'megapixels': 0.4, 'steps': 8, 'turbo': False, 'sampler': 'euler'},
    'pdd-upscale': {'label': 'PDD 神经放大 · 3D放大 + 轻精修', 'workflow': 'pdd-upscale', 'megapixels': 0.4, 'steps': 8, 'turbo': False, 'sampler': 'euler', 'upscale_by': 1.25, 'refine_denoise': 0.125},
}


def subgraph(graph, roots, stop=()):
    """Select actual dependencies, including nodes outside the old 1–20 ID range."""
    selected, visiting = set(), set()
    def visit(nid):
        if nid in visiting:
            raise ValueError('工作流节点存在循环依赖。')
        if nid in selected:
            return
        if nid not in graph:
            raise ValueError('工作流引用了缺失节点：' + nid)
        visiting.add(nid)
        if nid not in stop:
            for value in graph[nid]['inputs'].values():
                if isinstance(value, list) and len(value)==2 and isinstance(value[0],str) and isinstance(value[1],int):
                    visit(value[0])
        visiting.remove(nid)
        selected.add(nid)
    for nid in roots:
        visit(nid)
    return {nid:copy.deepcopy(node) for nid,node in graph.items() if nid in selected}


def replace_link(graph, old, new):
    for node in graph.values():
        for key,value in node['inputs'].items():
            if value == old:
                node['inputs'][key] = list(new)


def apply_workflow(graph, preset, is_reference):
    workflow=preset.get('workflow','native')
    if workflow=='native':
        return graph
    def node(nid,kind,**inputs):
        graph[str(nid)]={'class_type':kind,'inputs':inputs}
    if workflow=='lightx2v-8':
        if is_reference:
            raise ValueError('LightX2V 8步方案用于文字、首帧或首尾帧生成；多参考素材请选择 PDD 或原生方案。')
        node(5,'LoraLoaderModelOnly',model=['1',0],lora_name=preset.get('workflow_lora') or LIGHTX2V_8,strength_model=preset.get('lora_strength',1))
        if '6' in graph:graph['6']['inputs']['model']=['5',0]
        else:graph['9']['inputs']['model']=['5',0]
        return graph
    if workflow not in ('pdd-8','pdd-upscale'):
        raise ValueError('视频工作流不存在。')
    steps=preset['steps']
    if steps not in (4,6,8):
        raise ValueError('PDD 加速必须使用训练网格中的 4、6 或 8 步。')
    node(18,'MiniMaxH3SigmaShift',model=['1',0],shift_video=12,shift_audio=3)
    node(5,'MiniMaxH3PDDAccApply',model=['18',0],pdd_file=preset.get('pdd_ref' if is_reference else 'pdd_fl') or (PDD_REF if is_reference else PDD_FL),
         nfe=str(steps),lora_strength=preset.get('lora_strength',1),head_strength=preset.get('head_strength',1),on_off_grid='error')
    if '6' in graph:graph['6']['inputs']['model']=['5',0]
    else:graph['9']['inputs']['model']=['5',0]
    graph['10']['inputs']['sampler_name']='euler'
    node(11,'MiniMaxH3PDDAccScheduler',nfe=str(steps),denoise=1.0)
    if workflow=='pdd-upscale':
        if steps!=8 or preset.get('refine_denoise',0.125) not in (0,0.125):
            raise ValueError('神经放大首遍使用 8 步，精修强度选择 0 或 0.125。')
        graph['19']=graph.pop('12')
        node(20,'LTXVSeparateAVLatent',av_latent=['19',0])
        node(35,'MinimaxH3LatentUpscaler3D',latent=['20',0],model_name=preset.get('upscale_model') or UPSCALER,
             mode='scale by multiplier',**{'mode.scale':preset.get('upscale_by',1.25)},align=32,
             enable_temporal_chunking=True,force_unload=True,device='cuda',precision='fp16')
        node(36,'LTXVConcatAVLatent',video_latent=['35',0],audio_latent=['20',1])
        refine=preset.get('refine_denoise',0.125)
        if refine:
            node(33,'MiniMaxH3PDDAccScheduler',nfe=str(steps),denoise=refine)
            inputs=copy.deepcopy(graph['19']['inputs']);inputs.update(sigmas=['33',0],latent_image=['36',0])
            node(34,'SamplerCustomAdvanced',**inputs)
            node(12,'DramaPreserveLatentAudio',video=['34',0],original=['19',0])
        else:
            graph['12']=copy.deepcopy(graph['36'])
    return graph


def refined_size(width, height, preset):
    if preset.get('workflow')!='pdd-upscale':
        return width,height
    scale=preset.get('upscale_by',1.25)
    return tuple(max(2,round(size/16*scale/2)*2)*16 for size in (width,height))
