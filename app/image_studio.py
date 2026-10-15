"""Durable, serial image generation and versioned project reference images."""
from __future__ import annotations

import base64
import copy
import io
import json
from pathlib import Path
import secrets
import time
import threading
import uuid

import httpx
from PIL import Image

from .comfyio import download_file
from .content import json_text
from .image_environment import ImageEnvironment, image_size
from .image_schemas import ImageRequest
from .providers import Cancelled, LLMClient
from .storage import contained, digest, identifier, now, read_json, write_json


def image_graph(request, prompt, plan, manifest, prefix):
    models = {m['category']: m['comfy_name'] or m['name'] for m in plan['models']}
    resolution = plan['recommendation']['resolution'] if request.resolution == 'auto' else int(request.resolution)
    width, height = image_size(request.ratio, resolution)
    if request.transparent:
        prompt = 'This is an RGBA format image with transparency. ' + prompt + '\nThe image has an alpha channel and a transparent background.'
    graph = {
        '1': {'class_type': 'UNETLoader', 'inputs': {'unet_name': models['diffusion_models'], 'weight_dtype': 'default'}},
        '2': {'class_type': 'CLIPLoader', 'inputs': {'clip_name': models['text_encoders'], 'type': 'qwen_image', 'device': 'default'}},
        '3': {'class_type': 'TextEncodeQwenImage21', 'inputs': {'clip': ['2', 0], 'prompt': prompt, 'negative_prompt': '', 'resolution': resolution}},
        '4': {'class_type': 'EmptyLatentImage', 'inputs': {'width': width, 'height': height, 'batch_size': 1}},
        '5': {'class_type': 'VAELoader', 'inputs': {'vae_name': models['vae']}},
        '8': {'class_type': 'VAEDecode', 'inputs': {'samples': ['7', 0], 'vae': ['5', 0]}},
        '9': {'class_type': 'SaveImage', 'inputs': {'images': ['8', 0], 'filename_prefix': prefix}},
    }
    if plan['variant'].startswith('turbo'):
        graph.update({
            '10': {'class_type': 'ManualSigmas', 'inputs': {'sigmas': manifest['turbo_sigmas']}},
            '11': {'class_type': 'KSamplerSelect', 'inputs': {'sampler_name': 'euler'}},
            '12': {'class_type': 'RandomNoise', 'inputs': {'noise_seed': request.seed}},
            '13': {'class_type': 'BasicGuider', 'inputs': {'model': ['1', 0], 'conditioning': ['3', 0]}},
            '7': {'class_type': 'SamplerCustomAdvanced', 'inputs': {'noise': ['12', 0], 'guider': ['13', 0], 'sampler': ['11', 0], 'sigmas': ['10', 0], 'latent_image': ['4', 0]}},
        })
    else:
        graph['7'] = {'class_type': 'KSampler', 'inputs': {'model': ['1', 0], 'seed': request.seed, 'steps': 40, 'cfg': 1,
                       'sampler_name': 'euler', 'scheduler': 'simple', 'positive': ['3', 0], 'negative': ['3', 1], 'latent_image': ['4', 0], 'denoise': 1}}
    return graph, width, height


class ImageStudio:
    def __init__(self, config, db, projects, assets, skills):
        self.config, self.db, self.projects, self.assets, self.skills = config, db, projects, assets, skills
        self.root = config.root / 'data/image-studio'
        self.lock = threading.RLock()
        self.environment = ImageEnvironment(config)

    def path(self, iid):
        path = self.root / identifier(iid)
        if not (path / 'image.json').is_file():
            raise ValueError('图片任务不存在。')
        return path

    def get(self, iid):
        value = read_json(self.path(iid) / 'image.json')
        with self.db.connect() as database:
            active = [dict(row) for row in database.execute("SELECT kind,payload FROM jobs WHERE project_id=? AND status IN ('queued','running')", (value['owner'],))]
        value['project_busy'] = bool(value['project_id'] and active)
        value['busy'] = any(json.loads(job['payload']).get('image_id') == iid for job in active)
        if active and value['project_id'] and value.get('status') not in ('complete', 'error', 'paused'):
            state = read_json(self.projects.path(value['project_id']) / 'state.json', {})
            value['busy'] |= state.get('current_stage') == 'reference_images' and state.get('image_id') == iid
        value['file_available'] = bool(value.get('file') and contained(self.path(iid), value['file']).is_file())
        if value['file_available']:
            value['url'] = '/api/images/' + iid + '/file'
        elif value.get('file'):
            value['message'] = '生成记录已保留，但原图片文件缺失。请恢复文件或重新生成。'
        return value

    def listing(self, project_id=None):
        records = [read_json(p) for p in self.root.glob('*/image.json')]
        records = [r for r in records if r and (project_id is None or r.get('project_id') == project_id)]
        return [self.get(r['id']) for r in sorted(records, key=lambda r: r['created_at'], reverse=True)[:200]]

    def update(self, iid, **changes):
        with self.lock:
            path = self.path(iid) / 'image.json'
            value = read_json(path)
            value.update(changes, updated_at=now())
            write_json(path, value)
            return value

    def create(self, raw, project_id='', target='', parent_id=''):
        request = ImageRequest.model_validate(raw)
        if project_id:
            self.projects.path(project_id)
        if parent_id:
            self.path(parent_id)
        iid = uuid.uuid4().hex[:24]
        if request.seed is None:
            request.seed = secrets.randbelow(2**53)
        value = {'id': iid, 'owner': project_id or '__image_' + iid, 'project_id': project_id,
                 'target': target, 'parent_id': parent_id, 'request': request.model_dump(),
                 'status': 'new', 'message': '图片任务已创建。', 'created_at': now(), 'updated_at': now()}
        write_json(self.root / iid / 'image.json', value)
        return value

    def request(self, url, path, body=None):
        try:
            with httpx.Client(timeout=30, trust_env=False) as client:
                result = client.get(url + path, headers=self.environment.headers()) if body is None else client.post(url + path, headers=self.environment.headers(), json=body)
                if not result.is_success:
                    raise RuntimeError(f'图片引擎请求失败（HTTP {result.status_code}），请检查节点、模型和服务日志。')
                return result.json() if result.content else {}
        except (httpx.HTTPError, ValueError) as exc:
            raise RuntimeError('图片引擎连接中断；任务标识已保留，继续时会先核对原任务。') from exc

    def release_idle(self, url, required=False):
        if not self.environment.probe(url)['connected']:
            return
        queue = self.request(url, '/queue')
        if queue.get('queue_running') or queue.get('queue_pending'):
            if required:
                raise RuntimeError('生成引擎还有其他任务，请等待完成再切换本地文字模型或图片模型。')
            return
        self.request(url, '/free', {'unload_models': True, 'free_memory': True})

    def optimize(self, iid, report, cancel):
        value = self.get(iid)
        request = ImageRequest.model_validate(value['request'])
        if request.optimized_prompt:
            return request.optimized_prompt
        if value.get('optimized_prompt'):
            return value['optimized_prompt']
        if not request.optimize:
            return request.prompt
        settings = self.environment.settings()
        provider = self.config.provider(request.provider or settings.provider)
        model = request.model or settings.model or provider.model
        sid = request.skill or (settings.skill if request.purpose == 'general' else 'image-qwen-' + request.purpose)
        skill, snapshot = self.skills.render(sid, 'image_prompt', {'style': request.style, 'purpose': request.purpose, 'ratio': request.ratio})
        schema = {'type': 'object', 'properties': {'prompt': {'type': 'string'}, 'summary': {'type': 'string'}}, 'required': ['prompt', 'summary'], 'additionalProperties': False}
        messages = [{'role': 'system', 'content': skill + '\n输出 JSON，字段为 prompt（生图提示词）和 summary（中文优化说明）。'},
                    {'role': 'user', 'content': json.dumps({'prompt': request.prompt, 'style': request.style,
                     'purpose': request.purpose, 'ratio': request.ratio, 'transparent': request.transparent}, ensure_ascii=False)}]
        if provider.local:
            for url in {self.config.renderer_config().get('comfy_url'), f'http://127.0.0.1:{settings.managed_port}', settings.comfy_url} - {None, ''}:
                self.release_idle(url, required=True)
        client = LLMClient(provider, self.config.key(provider.id), self.config.get().get('proxy', ''))
        self.update(iid, status='optimizing', message='正在优化图片提示词。')
        report('正在优化图片提示词。')
        try:
            for attempt in range(provider.format_retries + 1):
                result = client.generate(messages, schema, model, report, cancel)
                try:
                    data = json_text(result['text'])
                    prompt = data['prompt']
                    if not isinstance(prompt, str) or not 1 <= len(prompt.strip()) <= 20000:
                        raise ValueError('提示词为空或超过 20000 字。')
                    self.update(iid, optimized_prompt=prompt.strip(), optimization_summary=str(data.get('summary', ''))[:2000],
                                optimization={'provider': provider.id, 'model': model, 'skill': snapshot, 'usage': result.get('usage')})
                    return prompt.strip()
                except (ValueError, KeyError, TypeError) as exc:
                    if attempt >= provider.format_retries:
                        raise ValueError('图片提示词优化结果不符合格式；请编辑提示词、换模型或关闭优化后重试。') from exc
                    messages.append({'role': 'user', 'content': '请仅返回含非空字符串 prompt 和 summary 的 JSON 对象。'})
        finally:
            if provider.local and provider.unload_after_use:
                client.unload(model)

    def interrupt(self, iid):
        value = self.get(iid)
        prompt_id, url = value.get('prompt_id'), value.get('comfy_url')
        if not prompt_id or not url:
            return
        queue = self.request(url, '/queue')
        if any(row[1] == prompt_id for row in queue.get('queue_pending', [])):
            self.request(url, '/queue', {'delete': [prompt_id]})
        if any(row[1] == prompt_id for row in queue.get('queue_running', [])):
            self.request(url, '/interrupt', {'prompt_id': prompt_id})

    def generate(self, iid, report, cancel, optimize_only=False):
        value = self.get(iid)
        if value.get('file') and contained(self.path(iid), value['file']).is_file():
            return value
        prompt = self.optimize(iid, report, cancel)
        if optimize_only:
            return self.update(iid, status='ready', message='提示词已优化，可编辑后生成。', optimized_prompt=prompt)
        if cancel():
            raise Cancelled('图片生成已停止。')
        request = ImageRequest.model_validate(value['request'])
        self.update(iid, status='preparing', message='正在检查图片环境。', effective_prompt=prompt)
        plan = value.get('model_plan') if value.get('prompt_id') else self.environment.plan(request.variant)
        if not plan:
            raise RuntimeError('原图片任务缺少环境快照，请核对历史后重新生成。')
        if not value.get('prompt_id') and not plan['ready']:
            if not self.environment.settings().auto_download:
                raise RuntimeError('图片环境尚未就绪，请先准备模型或开启自动下载。')
            plan = self.environment.prepare(request.variant, report, cancel)
        shared = self.config.renderer_config().get('comfy_url')
        if shared and shared != plan['comfy_url']:
            self.release_idle(shared, required=True)
        value = self.get(iid)
        url = value.get('comfy_url') or plan['comfy_url']
        prompt_id = value.get('prompt_id')
        history = self.request(url, '/history/' + prompt_id).get(prompt_id) if prompt_id else None
        queue = self.request(url, '/queue')
        queued = {item[1] for key in ('queue_running', 'queue_pending') for item in queue.get(key, [])}
        if not history and prompt_id not in queued:
            if prompt_id:
                raise RuntimeError('上次提交结果未知，服务队列与历史中未找到原任务。请核对引擎记录后选择重新生成，避免重复提交。')
            graph, width, height = image_graph(request, prompt, plan, self.environment.manifest, 'image_studio/' + iid)
            prompt_id = str(uuid.uuid4())
            write_json(self.path(iid) / 'workflow.json', graph)
            self.update(iid, prompt_id=prompt_id, comfy_url=url, submission='intent', width=width, height=height, model_plan=plan)
            submitted = self.request(url, '/prompt', {'prompt': graph, 'prompt_id': prompt_id, 'client_id': 'image-studio-' + iid})
            if submitted.get('prompt_id') != prompt_id:
                raise RuntimeError('图片服务未保留指定任务 ID，请升级兼容服务；提交结果待核对。')
            self.update(iid, submission='submitted')
        self.update(iid, status='rendering', message='Qwen 正在生成图片。')
        report('Qwen 正在生成图片。')
        deadline = time.monotonic() + self.environment.settings().timeout
        while time.monotonic() < deadline:
            if cancel():
                self.interrupt(iid)
                raise Cancelled('图片任务已停止，历史图片保留。')
            history = self.request(url, '/history/' + prompt_id).get(prompt_id)
            if history:
                status = history.get('status', {})
                if status.get('status_str') == 'error' or any(e[0] in ('execution_error', 'execution_interrupted') for e in status.get('messages', [])):
                    self.update(iid, submission='failed')
                    raise RuntimeError('ComfyUI 图片任务失败，请检查显存、模型及引擎日志；可保留提示词重新生成。')
                if status.get('completed'):
                    images = history.get('outputs', {}).get('9', {}).get('images', [])
                    if not images:
                        raise RuntimeError('图片任务完成但没有返回 PNG。')
                    path = self.path(iid) / 'image.png'
                    download_file(images[0], path, url, self.config.key('comfy'), cancel)
                    with Image.open(path) as image:
                        image.load()
                        size = image.size
                        alpha = image.getchannel('A').getextrema() if image.mode == 'RGBA' else None
                    completed = self.update(iid, status='complete', message='图片已生成。', file='image.png',
                                            width=size[0], height=size[1], sha256=__import__('hashlib').sha256(path.read_bytes()).hexdigest(),
                                            has_transparency=bool(alpha and alpha[0] < 255), submission='complete')
                    try:
                        self.release_idle(url)
                    except RuntimeError:
                        self.update(iid, message='图片已生成；引擎释放请求未确认，下次使用前请检查服务。')
                    return completed
            time.sleep(1)
        raise RuntimeError('图片任务超过等待时限，后台可能仍在生成。继续会查询同一个任务，不会重复提交。')

    def candidates(self, pid):
        project = self.projects.get(pid)
        story = project.get('story') or {}
        result = []
        for c in story.get('characters', []):
            result.append({'key': 'character-' + c['id'], 'kind': 'character', 'id': c['id'], 'name': c['name'], 'description': c['visual_description']})
        scenes = {}
        for scene in story.get('scenes', []):
            name = scene.get('name') or scene.get('description') or scene.get('id')
            if name:
                scenes[str(scene.get('id') or name)] = {'id': str(scene.get('id') or name), 'name': str(name),
                                                       'description': str(scene.get('visual_description') or scene.get('description') or name)}
        for shot in story.get('shots', []):
            name = shot.get('scene') or shot.get('scene_id')
            if name:
                if not shot.get('scene_id') and any(s['name'] == name for s in scenes.values()):
                    continue
                sid = str(shot.get('scene_id') or name)
                scenes.setdefault(sid, {'id': sid, 'name': str(name), 'description': str(name)})
        for scene in scenes.values():
            result.append({'key': 'scene-' + digest(scene['id'])[:16], 'kind': 'scene', **scene})
        for prop in story.get('props', []):
            name = prop.get('name') or prop.get('id')
            if name:
                result.append({'key': 'prop-' + digest(prop.get('id') or name)[:16], 'kind': 'prop', 'id': str(prop.get('id') or name),
                               'name': str(name), 'description': str(prop.get('visual_description') or prop.get('description') or name)})
        book = read_json(self.projects.path(pid) / 'reference-images.json', {'items': {}})
        for item in result:
            item['history'] = book['items'].get(item['key'], {}).get('versions', [])
            item['selected_asset'] = book['items'].get(item['key'], {}).get('selected_asset')
        return result

    def reference_request(self, pid, target, overrides=None):
        candidate = next((c for c in self.candidates(pid) if c['key'] == target), None)
        if not candidate:
            raise ValueError('角色或场景已改变，请刷新后选择。')
        self.assert_reference_editable(pid, candidate)
        options = self.projects.options(self.projects.path(pid))
        preferences = options.reference_images
        request = {'prompt': candidate['name'] + '：' + candidate['description'], 'purpose': candidate['kind'],
                   'style': options.style, 'ratio': '3:4' if candidate['kind'] == 'character' else options.ratio,
                   'optimize': preferences.optimize, 'variant': preferences.variant, 'resolution': preferences.resolution,
                   'provider': preferences.provider, 'model': preferences.model}
        request.update(overrides or {})
        return request

    @staticmethod
    def target_matches(kind, target_id, name, shot):
        return ((kind == 'character' and target_id in shot['characters']) or
                (kind == 'scene' and (target_id == str(shot.get('scene_id') or shot.get('scene') or '') or
                                     (not shot.get('scene_id') and name == shot.get('scene')))) or
                (kind == 'prop' and target_id in shot.get('props', [])))

    def assert_reference_editable(self, pid, candidate):
        story = self.projects.get(pid)['story']
        locked = [str(s['id']) for s in story['shots'] if s.get('locked') and
                  self.target_matches(candidate['kind'], candidate['id'], candidate['name'], s)]
        if locked:
            raise ValueError('这些镜头会引用新图片，请先解锁后生成或采用：' + '、'.join(locked))

    def adopt(self, pid, target, iid, generated=False):
        if not generated:
            self.projects.assert_idle(pid)
        candidate = next((c for c in self.candidates(pid) if c['key'] == target), None)
        if not candidate:
            raise ValueError('图片用途对应的角色或场景不存在。')
        self.assert_reference_editable(pid, candidate)
        folder = self.projects.path(pid)
        book = read_json(folder / 'reference-images.json', {'items': {}})
        entry = book['items'].setdefault(target, {'versions': []})
        version = next((v for v in entry['versions'] if v['image_id'] == iid), None)
        assets = self.projects.get(pid)['assets']
        if version is None:
            recovered = next((a for a in assets.values() if a.get('generation', {}).get('id') == iid and a['generation'].get('target') == target and contained(folder, a['file']).is_file()), None)
            if recovered:
                version = {'image_id': iid, 'asset_id': recovered['id'], 'created_at': recovered['created_at']}
                entry['versions'].append(version)
        if version is None:
            image = self.get(iid)
            if image.get('status') != 'complete' or not image.get('file'):
                raise ValueError('请等待图片生成完成后采用。')
            raw = contained(self.path(iid), image['file']).read_bytes()
            resized = False
            if len(raw) > 8_000_000:
                with Image.open(io.BytesIO(raw)) as reference:
                    reference.thumbnail((1024, 1024))
                    buffer = io.BytesIO()
                    reference.save(buffer, format='PNG')
                    raw = buffer.getvalue()
                    resized = True
            asset = self.assets.add_image(pid, base64.b64encode(raw).decode(), candidate['name'],
                                          candidate['id'] if candidate['kind'] == 'character' else '', generated=generated,
                                          generation={'id': iid, 'target': target, 'seed': image['request']['seed'],
                                                      'variant': image.get('model_plan', {}).get('variant'),
                                                      'prompt': image.get('effective_prompt') or image['request']['prompt']})
            version = {'image_id': iid, 'asset_id': asset['id'], 'created_at': now(), 'reference_resized': resized}
            entry['versions'].append(version)
        entry.update(selected_asset=version['asset_id'], kind=candidate['kind'], target_id=candidate['id'], target_name=candidate['name'],
                     source_hash=digest([candidate['description'], self.projects.options(folder).style]))
        project = self.projects.get(pid)
        selected_file = project['assets'].get(version['asset_id'], {}).get('file')
        if not selected_file or not contained(folder, selected_file).is_file():
            raise ValueError('该历史参考图文件缺失，请恢复素材或重新生成。')
        story = copy.deepcopy(project['story'])
        all_managed = {v['asset_id'] for x in book['items'].values() for v in x['versions']}
        for shot in story['shots']:
            selected = []
            for item in book['items'].values():
                matches = self.target_matches(item['kind'], item['target_id'], item.get('target_name'), shot)
                if matches and item.get('selected_asset'):
                    selected.append(item['selected_asset'])
            bindings = copy.deepcopy(shot.get('bindings') or {})
            retained = [a for a in bindings.get('images', []) if a not in all_managed]
            represented = {project['assets'].get(a, {}).get('character') for a in retained + selected}
            if selected:
                for cid in shot['characters']:
                    if cid not in represented:
                        asset = next((a for a in reversed(list(project['assets'].values())) if a.get('character') == cid and a.get('type') == 'image'), None)
                        if asset:
                            retained.append(asset['id'])
            if selected or 'images' in bindings:
                bindings['images'] = list(dict.fromkeys(retained + selected))
                shot['bindings'] = bindings
        self.projects.save_story(pid, story, generated=generated)
        write_json(folder / 'reference-images.json', book)
        return {'asset_id': version['asset_id'], 'image_id': iid, 'target': target}

    def ensure_references(self, pid, report, cancel, targets=None):
        options = self.projects.options(self.projects.path(pid))
        preferences = options.reference_images
        wanted = {'character': preferences.characters, 'scene': preferences.scenes, 'prop': preferences.props}
        for candidate in self.candidates(pid):
            if (targets is not None and candidate['key'] not in targets) or (targets is None and not wanted[candidate['kind']]):
                continue
            if targets is None:
                entry = read_json(self.projects.path(pid) / 'reference-images.json', {'items': {}})['items'].get(candidate['key'], {})
                selected = self.projects.get(pid)['assets'].get(candidate.get('selected_asset'), {})
                if selected.get('file') and contained(self.projects.path(pid), selected['file']).is_file() and entry.get('source_hash') == digest([candidate['description'], options.style]):
                    continue
                # Existing uploaded identity references stay the default unless explicitly regenerated.
                managed = {v['asset_id'] for v in entry.get('versions', [])}
                if candidate['kind'] == 'character' and any(a.get('character') == candidate['id'] and a['id'] not in managed for a in self.projects.get(pid)['assets'].values()):
                    continue
            if cancel():
                raise Cancelled('项目参考图生成已停止。')
            request = self.reference_request(pid, candidate['key'])
            existing = next((x for x in self.listing(pid) if targets is None and x.get('target') == candidate['key'] and x['status'] in ('new', 'queued', 'optimizing', 'preparing', 'rendering', 'paused', 'error', 'complete') and
                             {k:v for k,v in x['request'].items() if k != 'seed'} == {k:v for k,v in ImageRequest.model_validate(request).model_dump().items() if k != 'seed'}), None)
            image = existing or self.create(request, pid, candidate['key'])
            report('正在生成参考图：' + candidate['name'], image_id=image['id'])
            try:
                self.generate(image['id'], lambda text, **extra: report(candidate['name'] + '：' + text, **extra), cancel)
            except Exception as exc:
                self.update(image['id'], status='paused' if isinstance(exc, Cancelled) else 'error', message=str(exc)[:2000])
                raise
            self.adopt(pid, candidate['key'], image['id'], generated=True)
