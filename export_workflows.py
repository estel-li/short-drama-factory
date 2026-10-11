"""Export the working example as ComfyUI API-format workflow files."""
import copy
from pathlib import Path

import pipeline


def export(project):
    project = Path(project)
    story = pipeline.load_json(project / '分镜.json')
    settings = pipeline.load_json(project / 'settings.json')
    record = pipeline.load_json(project / 'state.json')['shots']['1']
    graph = pipeline.graph_for(story['shots'][0], project.name, settings['profile'], settings['ratio'], seed=settings['seed'] + 1)
    filename = f'drama/{project.name}/shot_001_{record["signature"][:12]}.safetensors'
    encode = {nid: copy.deepcopy(value) for nid, value in graph.items() if nid in ('2', '3', '7')}
    encode['30'] = {'class_type': 'DramaSaveConditioning', 'inputs': {'conditioning': ['7', 0], 'filename': filename}}
    render = pipeline.load_json(project / 'prompts/001_render.json')
    sampling_file = project / 'prompts/001_sample.json'
    target = pipeline.ROOT / 'workflows'
    pipeline.save_json(target / '01_提示词编码_API.json', encode)
    if sampling_file.exists():
        pipeline.save_json(target / '02_H3音画采样_API.json', pipeline.load_json(sampling_file))
        pipeline.save_json(target / '03_VAE解码保存视频_API.json', render)
    else:
        pipeline.save_json(target / '02_H3生成镜头_API.json', render)
    destination = Path(pipeline.CONFIG['comfy_dir']) / 'user/default/workflows/短剧工厂'
    pipeline.save_json(destination / '01_提示词编码_API.json', encode)
    if sampling_file.exists():
        pipeline.save_json(destination / '02_H3音画采样_API.json', pipeline.load_json(sampling_file))
        pipeline.save_json(destination / '03_VAE解码保存视频_API.json', render)
    else:
        pipeline.save_json(destination / '02_H3生成镜头_API.json', render)
    print('Exported staged workflows.')


if __name__ == '__main__':
    capacity = pipeline.ROOT / 'logs/capacity_project.txt'
    export((capacity if capacity.exists() else pipeline.ROOT / 'logs/test_project.txt').read_text(encoding='utf-8').strip())
