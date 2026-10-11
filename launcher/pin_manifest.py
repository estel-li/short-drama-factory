"""从上游元数据固定安装版本；不下载模型权重。"""
import json
import sys
from pathlib import Path

import requests
from huggingface_hub import HfApi

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.storage import ROOT, write_json

release = requests.get('https://api.github.com/repos/Comfy-Org/ComfyUI/releases/tags/v0.36.0', timeout=30)
release.raise_for_status()
release = release.json()
assets = [{'name': a['name'], 'url': a['browser_download_url'], 'size': a['size'], 'digest': a.get('digest')}
          for a in release['assets'] if 'nvidia' in a['name'].lower()]
print('portable:', json.dumps(assets), flush=True)
files = {
    'Comfy-Org/MiniMax-H3': {
        'text_encoder': 'text_encoders/qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors',
        'video_vae': 'vae/minimax_h3_video_vae_fp16.safetensors',
        'audio_vae': 'vae/minimax_h3_audio_vae_fp32.safetensors'},
    'starsfriday/MiniMax-H3-w4a8': {
        'fl_model': 'minimax_h3_fl2va_pruned_w4a8_mixed.safetensors',
        'ref_model': 'minimax_h3_ref2va_pruned_w4a8_mixed.safetensors'},
    'lightx2v/Minimax-h3-Turbo': {
        'fl_lora': 'minimax_h3_fl2v_turbo_4step_v1.0_768p_comfyui_bf16.safetensors',
        'ref_lora': 'minimax_h3_ref2v_turbo_4step_v0.1_comfyui_bf16.safetensors'},
}
api = HfApi()
models = []
for repo, wanted in files.items():
    info = api.model_info(repo, files_metadata=True)
    siblings = {s.rfilename: s for s in info.siblings}
    print(repo, info.sha, 'license:', info.card_data.get('license') if info.card_data else None, flush=True)
    for role, filename in wanted.items():
        found = [name for name in siblings if name == filename or name.endswith('/' + filename)]
        if len(found) != 1:
            print('Not uniquely found:', filename, 'Candidates:', [name for name in siblings if role.split('_')[0] in name][:20], flush=True)
            continue
        filename = found[0]
        file = siblings[filename]
        category = 'text_encoders' if role == 'text_encoder' else 'vae' if role.endswith('vae') else 'loras' if role.endswith('lora') else 'diffusion_models'
        models.append({'role': role, 'repo': repo, 'revision': info.sha, 'filename': filename, 'name': Path(filename).name,
                       'category': category, 'size': file.size, 'sha256': file.lfs.sha256 if file.lfs else None,
                       'license': info.card_data.get('license') if info.card_data else None})
manifest = {'id': 'h3-5060ti-16g', 'name': 'H3 W4A8 · RTX 5060 Ti 16GB', 'version': 1,
            'comfyui': {'repo': 'Comfy-Org/ComfyUI', 'tag': 'v0.36.0', 'portable_assets': assets},
            'hardware': {'tested_gpu': 'RTX 5060 Ti', 'tested_vram_gb': 16, 'tested_driver': '616.92', 'tested_torch': '2.9.1+cu130'},
            'models': models, 'nodes': [{'name': 'ComfyUI-DramaFactory', 'source': 'bundled'}]}
write_json(ROOT / 'manifests' / 'h3-5060ti-16g.json', manifest)
print('manifest roles:', [m['role'] for m in models], flush=True)
