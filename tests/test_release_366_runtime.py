import ast
import copy
import math
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import requests

import pipeline
from app.environment import Installer


class Release366RuntimeTests(unittest.TestCase):
    def test_fresh_install_checks_and_installs_wheels_in_app_temp_environment(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            portable = root / 'engines/ComfyUI_windows_portable'
            for relative in ('ComfyUI/main.py', 'python_embeded/python.exe'):
                path = portable / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b'fixture')
            wheel = {'package': 'torch', 'version': 'test-version', 'name': 'torch.whl',
                     'url': 'https://invalid.test/torch.whl', 'size': 1, 'sha256': 'a' * 64}
            plan = {'mode': 'fresh', 'hardware': {'os': 'Windows', 'architecture': 'AMD64',
                    'gpu': [{}], 'free_disk_bytes': 100}, 'download_bytes': 1,
                    'install_dir': str(root / 'engines'), 'models_dir': str(root / 'models'),
                    'runtime_wheels': [wheel], 'models': [], 'manifest': 'fixture'}
            config = SimpleNamespace(root=root, renderer_config=lambda: {}, get=lambda: {},
                                     save=Mock(), key=lambda name: '')
            installer = Installer(config)
            child = Mock(returncode=0)
            child.poll.return_value = 0
            with patch.object(installer, 'plan', return_value=plan), \
                    patch.object(installer, 'manifest', return_value={}), \
                    patch('app.environment.Downloader.fetch', return_value=root / 'torch.whl') as fetch, \
                    patch('app.environment.subprocess.run', return_value=subprocess.CompletedProcess([], 0, '{}')) as run, \
                    patch('app.environment.subprocess.Popen', return_value=child) as popen, \
                    patch('pipeline.ensure_comfy'), \
                    patch('app.environment.catalog', return_value={'missing_nodes': [], 'configured_missing': []}), \
                    patch.dict(pipeline.CONFIG, copy.deepcopy(pipeline.CONFIG), clear=True):
                receipt = installer.execute({}, lambda progress: None, lambda: False)
            self.assertEqual(receipt['manifest'], 'fixture')
            self.assertEqual(fetch.call_count, 1)
            for call in (run.call_args, popen.call_args):
                environment = call.kwargs['env']
                for key in ('TEMP', 'TMP', 'TMPDIR'):
                    self.assertEqual(Path(environment[key]), root / 'data/install-temp')
                    self.assertTrue(Path(environment[key]).is_dir())
                self.assertEqual(Path(environment['PIP_CACHE_DIR']), root / 'data/pip-cache')
            config.save.assert_called_once()

    def test_authenticated_remote_engine_is_reused(self):
        secret = 'unit-test-private-token'
        with patch.dict(pipeline.CONFIG, {'comfy_url': 'https://comfy.invalid.test',
                'mode': 'remote', 'comfy_auth_token': secret}), \
                patch('pipeline.requests.get') as get, patch('pipeline.subprocess.Popen') as popen:
            pipeline.ensure_comfy()
        get.assert_called_once_with('https://comfy.invalid.test/system_stats', timeout=3,
                                    headers={'Authorization': 'Bearer ' + secret})
        popen.assert_not_called()

    def test_local_startup_poll_uses_the_same_authentication(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = {'runtime_root': str(root), 'comfy_dir': str(root / 'comfy'),
                      'python': 'unused-python.exe', 'comfy_url': 'http://127.0.0.1:8188',
                      'mode': 'existing', 'comfy_auth_token': 'unit-test-token'}
            child = Mock()
            child.poll.return_value = None
            with patch.dict(pipeline.CONFIG, config), \
                    patch('pipeline.requests.get', side_effect=[requests.ConnectionError('offline'), Mock()]) as get, \
                    patch('pipeline.socket.socket') as socket, \
                    patch('pipeline.subprocess.Popen', return_value=child):
                socket.return_value.__enter__.return_value.connect_ex.return_value = 1
                pipeline.ensure_comfy()
            self.assertEqual([call.kwargs['timeout'] for call in get.call_args_list], [3, 2])
            for call in get.call_args_list:
                self.assertEqual(call.kwargs['headers'], {'Authorization': 'Bearer unit-test-token'})

    def test_missing_stage_caches_resubmit_completed_tasks_and_reuse_active_tasks(self):
        shot = {'id': 1, 'uid': 'test-shot', 'duration': 4,
                'prompt': 'A quiet empty room with warm afternoon light.', 'mode': 'T2VA'}
        graph = pipeline.graph_for(shot, 'runtime-test', 'draft')
        for method, field in (('encode', 'encoding_prompt_id'), ('sample', 'sampling_prompt_id')):
            for stage in ('completed', 'error', 'running', 'pending'):
                with self.subTest(method=method, stage=stage), tempfile.TemporaryDirectory() as directory:
                    runner = pipeline.Runner(directory)
                    runner.state['shots'] = {'1': {field: 'old-task'}}
                    runner.report = Mock()
                    cache_ready = False
                    submitted = []
                    def request(path, data=None):
                        if path == '/queue':
                            return {'queue_running': [[0, 'old-task']] if stage == 'running' else [],
                                    'queue_pending': [[0, 'old-task']] if stage == 'pending' else []}
                        if path == '/history/old-task':
                            return {'old-task': {'status': {'completed': stage == 'completed',
                                'status_str': 'error' if stage == 'error' else 'success'}}} if stage in ('completed', 'error') else {}
                        if path == '/prompt':
                            submitted.append(data)
                            return {'prompt_id': 'new-task'}
                        if path == '/free':
                            return {}
                        raise AssertionError('Unexpected API request: ' + path)
                    def completed(*args, **kwargs):
                        nonlocal cache_ready
                        cache_ready = True
                        return {}
                    with patch('pipeline.api', side_effect=request), \
                            patch('pipeline.cache_exists', side_effect=lambda *args: cache_ready), \
                            patch('pipeline.validate_graph'), patch('pipeline.time.sleep'), \
                            patch.object(runner, 'wait', side_effect=completed) as wait:
                        getattr(runner, method)(copy.deepcopy(graph), shot, 'cache-signature')
                    new_task = stage in ('completed', 'error')
                    self.assertEqual(len(submitted), int(new_task))
                    self.assertEqual(wait.call_args.args[0], 'new-task' if new_task else 'old-task')
                    self.assertEqual(runner.state['shots']['1'][field], 'new-task' if new_task else 'old-task')

    def test_save_nodes_invalidate_missing_files_but_keep_existing_files_cacheable(self):
        source = pipeline.ROOT / 'nodes/ComfyUI-DramaFactory/__init__.py'
        tree = ast.parse(source.read_text(encoding='utf-8'))
        classes = [node for node in tree.body if isinstance(node, ast.ClassDef)
                   and node.name in ('DramaSaveConditioning', 'DramaSaveLatent')]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            scope = {'cache_path': lambda name: root / 'conditioning' / name,
                     'latent_path': lambda name: root / 'latents' / name}
            exec(compile(ast.Module(body=classes, type_ignores=[]), str(source), 'exec'), scope)
            for name, path_function, input_name in (
                    ('DramaSaveConditioning', 'cache_path', 'conditioning'),
                    ('DramaSaveLatent', 'latent_path', 'samples')):
                with self.subTest(node=name):
                    node = scope[name]
                    filename = 'drama/fixture.safetensors'
                    arguments = {'filename': filename, input_name: None}
                    # Before first execution the target is allowed to be absent.
                    self.assertTrue(math.isnan(node.IS_CHANGED(**arguments)))
                    path = scope[path_function](filename)
                    path.parent.mkdir(parents=True)
                    path.write_bytes(b'saved-cache')
                    unchanged = node.IS_CHANGED(**arguments)
                    self.assertEqual(unchanged, node.IS_CHANGED(**arguments))
                    path.unlink()
                    missing = node.IS_CHANGED(**arguments)
                    self.assertNotEqual(unchanged, missing)
                    self.assertNotEqual(missing, node.IS_CHANGED(**arguments))


if __name__ == '__main__':
    unittest.main()
