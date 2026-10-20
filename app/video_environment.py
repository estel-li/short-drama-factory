"""Pinned optional H3 adapters/plugins, separate from the user's ComfyUI install."""
from __future__ import annotations
from pathlib import Path
import shutil
import zipfile
from urllib.parse import urlsplit

import httpx
import yaml

from .downloads import Downloader
from .storage import ROOT, contained, digest, read_json, write_json

MODEL_FIELDS = {'lightx2v_8': 'workflow_lora', 'pdd_fl': 'pdd_fl', 'pdd_ref': 'pdd_ref',
                'upscaler': 'upscale_model', 'controlnet': 'control_model'}


class WorkflowDownloadRequired(ValueError):
    def __init__(self, plan):
        super().__init__('所选视频工作流缺少资源，请先点击“准备所选工作流”确认下载。')
        self.plan = plan


class VideoWorkflowEnvironment:
    def __init__(self, config):
        self.config = config
        self.root = config.root
        self.manifest = read_json(ROOT/'manifests/video-workflows.json')

    def probe(self):
        env = self.config.renderer_config()
        headers = {'Authorization':'Bearer '+self.config.key('comfy')} if self.config.key('comfy') else {}
        try:
            with httpx.Client(trust_env=False,timeout=5) as client:
                r=client.get(env['comfy_url']+'/object_info',headers=headers);r.raise_for_status()
            return r.json()
        except (httpx.HTTPError,ValueError):
            return {}

    def search_roots(self, category):
        env=self.config.renderer_config()
        roots=[self.root/'models/video-workflows'/category,
               Path(env.get('comfy_dir') or self.root/'engines/ComfyUI')/'models'/category]
        mappings = [Path(env.get('extra_model_paths_file') or self.root/'extra_model_paths.yaml'),
                    self.root/'data/video-workflow-paths.yaml']
        for mapping in mappings:
            if not mapping.is_file():
                continue
            for group in (yaml.safe_load(mapping.read_text(encoding='utf-8')) or {}).values():
                if not isinstance(group, dict):
                    continue
                base = Path(group.get('base_path') or mapping.parent)
                if not base.is_absolute():
                    base = mapping.parent / base
                for folder in str(group.get(category, '')).splitlines():
                    if folder.strip():
                        roots.append(base / folder.strip())
        return list(dict.fromkeys(root.resolve() for root in roots if root.is_dir()))

    def local_status(self, target, file):
        target=Path(target)
        if not target.is_file() or target.stat().st_size!=file['size']:return 'invalid'
        receipt=read_json(self.root/'data/video-model-verification'/(digest(str(target.resolve()))+'.json'),{})
        stat=target.stat()
        if receipt.get('size')==stat.st_size and receipt.get('mtime_ns')==stat.st_mtime_ns:
            return 'verified' if receipt.get('sha256')==file['sha256'] else 'invalid'
        return Downloader.verification_status(target,file['size'],file['sha256'])

    def verify_local(self, file, cancel):
        target=Path(file['target']);before=target.stat()
        actual=Downloader.checksum(target,cancel)
        after=target.stat()
        if (before.st_size,before.st_mtime_ns)!=(after.st_size,after.st_mtime_ns):return False
        # Models may live in a read-only shared directory; receipts belong to the app.
        write_json(self.root/'data/video-model-verification'/(digest(str(target.resolve()))+'.json'),
                   {'size':before.st_size,'mtime_ns':before.st_mtime_ns,'sha256':actual})
        return actual==file['sha256']

    def plan(self, profile):
        env=self.config.renderer_config()
        preset=env.get('profiles',{}).get(profile)
        if preset is None:raise ValueError('视频质量或工作流不存在。')
        workflow=preset.get('workflow','native')
        spec=self.manifest['workflows'].get(workflow)
        if not spec:return {'profile':profile,'workflow':'native','models':[],'plugins':[],'download_bytes':0,'ready':True,'requires_confirmation':False,'restart_required':False}
        nodes=self.probe()
        remote=env.get('mode')=='remote' or urlsplit(env['comfy_url']).hostname not in ('127.0.0.1','localhost','::1')
        rows=[]
        scans = {}
        for role in spec['files']:
            f=self.manifest['models'][role]
            name=preset.get(MODEL_FIELDS[role]) or f['name']
            node,field={'loras':('LoraLoaderModelOnly','lora_name'),'pdd_acc':('MiniMaxH3PDDAccApply','pdd_file'),
                        'latent_upscale_models':('MinimaxH3LatentUpscaler3D','model_name'),
                        'model_patches':('ModelPatchLoader','name')}[f['category']]
            raw=nodes.get(node,{}).get('input',{}).get('required',{}).get(field,[])
            choices=raw[0] if raw and isinstance(raw[0],list) else raw[1].get('options',[]) if len(raw)>1 else []
            normalized = {n.replace('\\', '/'): n for n in choices}
            recognized = normalized.get(name)
            matches = [n for n in choices if n.replace('\\', '/').rsplit('/', 1)[-1] == name]
            if not recognized and len(matches) == 1:
                recognized = matches[0]
            roots = self.search_roots(f['category']) if not remote else []
            found = next((root / candidate for root in roots for candidate in (name, recognized)
                          if candidate and (root / candidate).is_file()
                          and (root / candidate).resolve().is_relative_to(root)), None)
            # Search a category only once per plan, after cheap exact-path checks.
            if not found and '/' not in name:
                for root in roots:
                    if root not in scans:
                        scans[root] = [p for p in root.rglob('*.safetensors') if p.is_file() and p.resolve().is_relative_to(root)]
                    found = next((p for p in scans[root] if p.name == name), None)
                    if found:
                        break
            target=found or contained(self.root/'models/video-workflows',f['category']+'/'+name)
            custom=Path(name).name!=f['name']
            state=self.local_status(target,f) if not custom else 'invalid'
            if not custom and found and state=='invalid':
                target=contained(self.root/'models/video-workflows',f['category']+'/'+name)
                state=self.local_status(target,f)
            action = ('available' if recognized else 'local' if found else 'missing') if custom else (
                'available' if recognized and (remote or not found or state == 'verified') else
                'verified' if state == 'verified' else 'verify' if state == 'unknown' else 'download')
            rows.append({**f,'role':role,'name':name,'comfy_name':recognized,'target':str(target),'custom':custom,'action':action})
        plugins=[]
        required={'MiniMaxH3PDDAccApply','MiniMaxH3PDDAccScheduler'} if workflow.startswith('pdd') else set()
        if workflow=='pdd-upscale':required.update(('MinimaxH3LatentUpscaler3D','LTXVSeparateAVLatent','LTXVConcatAVLatent','DramaPreserveLatentAudio'))
        required.update(spec.get('required_nodes',[]))
        for key in spec['plugins']:
            plugin=self.manifest['plugins'][key]
            target=self.root/'data/comfy-runtime/custom_nodes'/plugin['name']
            local=read_json(target/'factory-source.json',{}).get('revision')==plugin['revision'] and (target/'__init__.py').is_file()
            plugin_nodes = set(plugin.get('required_nodes', required))
            plugins.append({**plugin,'target':str(target),'action':'available' if plugin_nodes<=set(nodes) else 'local' if local else 'download'})
        downloaded=sum(f['size'] for f in [*rows,*plugins] if f['action']=='download')
        missing_nodes = sorted(required-set(nodes))
        ready=bool(nodes) and not missing_nodes and all(f['comfy_name'] and f['action'] not in ('verify','download','missing') for f in rows)
        result={'profile':profile,'workflow':workflow,'preset':preset,'models':rows,'plugins':plugins,'download_bytes':downloaded,
                'requires_confirmation':bool(downloaded),'ready':ready,'remote':remote,
                'connected':bool(nodes), 'missing_nodes':missing_nodes,
                'verify_bytes':sum(f['size'] for f in rows if f['action']=='verify'),
                'restart_required':bool(nodes) and (bool(missing_nodes) or any(not f['comfy_name'] for f in rows)),
                'free_disk_bytes':shutil.disk_usage(self.root).free,
                'supported_modes':spec['supported_modes'], 'required_slots':spec.get('required_slots',[])}
        result['resolved_preset'] = {**preset, **{MODEL_FIELDS[f['role']]: f['comfy_name'] for f in rows if f['comfy_name']}}
        result['confirmation_token']=digest({k:result[k] for k in ('profile','workflow','models','plugins','download_bytes')})
        return result

    def prepare(self, profile, report, cancel, confirmation=''):
        from .providers import Cancelled
        def check_cancel():
            if cancel():
                raise Cancelled('视频工作流准备已暂停。')
        check_cancel()
        plan=self.plan(profile)
        if plan['ready']:return plan
        if plan.get('remote'):raise ValueError('请在远程 ComfyUI 安装该工作流所需节点和模型，再检查环境。')
        if any(f['action']=='missing' for f in plan['models']):raise ValueError('自定义工作流模型文件未找到，请更正文件名或放入模型目录。')
        if plan['requires_confirmation'] and confirmation!=plan['confirmation_token']:raise WorkflowDownloadRequired(plan)
        if plan.get('free_disk_bytes',0)<plan['download_bytes']+256*1024**2:raise ValueError('视频工作流模型目录磁盘空间不足。')
        downloader=Downloader(self.config.get().get('proxy',''))
        for f in plan['models']:
            check_cancel()
            if f['action'] in ('available','local','verified'):continue
            if f['action']=='verify':
                report('正在校验已有工作流模型：'+f['name'],progress={'status':'verifying','file':f['name']})
                if not self.verify_local(f,cancel):raise WorkflowDownloadRequired(self.plan(profile))
            else:
                downloader.fetch(f['url'],f['target'],f['size'],f['sha256'],lambda v:report('视频工作流模型 '+v['status'],progress=v),cancel,self.config.key('hf'))
        for plugin in plan['plugins']:
            check_cancel()
            if plugin['action'] in ('available','local'):continue
            archive=self.root/'data/downloads'/(plugin['name']+'-'+plugin['revision']+'.zip')
            downloader.fetch(plugin['url'],archive,plugin['size'],plugin['sha256'],lambda v:report('正在准备视频工作流节点',progress=v),cancel)
            stage=self.root/'data/video-workflow-sources'/plugin['revision']
            stage.mkdir(parents=True,exist_ok=True)
            with zipfile.ZipFile(archive) as zipped:
                for entry in zipped.infolist():
                    check_cancel()
                    contained(stage,entry.filename)
                    if (entry.external_attr>>16)&0o170000==0o120000:raise ValueError('工作流节点归档包含不支持的符号链接。')
                zipped.extractall(stage)
            source=stage/(plugin['name']+'-'+plugin['revision'])
            if not (source/'__init__.py').is_file():raise ValueError('固定版本节点源码结构不正确。')
            shutil.copytree(source,Path(plugin['target']),dirs_exist_ok=True,ignore=shutil.ignore_patterns('.git','__pycache__','tests','*.pyc'))
            write_json(Path(plugin['target'])/'factory-source.json',{k:plugin[k] for k in ('repo','revision','license','sha256')})
        mapping={}
        for category in ('loras','pdd_acc','latent_upscale_models','model_patches'):
            paths=list(dict.fromkeys(str(Path(f['target']).parents[len(Path(f['name']).parts)-1])
                for f in plan['models'] if f['category']==category and Path(f['target']).is_file()))
            if paths:mapping[category]='\n'.join(paths)
        write=self.root/'data/video-workflow-paths.yaml'
        write.parent.mkdir(parents=True,exist_ok=True)
        # Include every installed optional recipe, so switching profiles keeps their paths.
        previous=yaml.safe_load(write.read_text(encoding='utf-8')) if write.exists() else {}
        groups=previous or {}
        # Do not clear previous mappings when an already-running service exposes
        # a file through a path we cannot resolve locally.
        if mapping:
            groups[plan['workflow']]={'is_default':True,**mapping}
            check_cancel()
            temporary = write.with_suffix('.yaml.tmp')
            temporary.write_text(yaml.safe_dump(groups,allow_unicode=True),encoding='utf-8')
            temporary.replace(write)
        return self.plan(profile)
