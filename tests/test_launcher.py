import tempfile
import unittest
import json
import os
import subprocess
import venv
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import Mock, patch

from launcher import start
from launcher.build_portable import copy_windows_batch


class LauncherTests(unittest.TestCase):
    def test_health_accepts_slow_engine_probe_when_workbench_is_ready(self):
        expected = {'version': '3.0.1', 'application_root': 'workbench', 'comfy': False}
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                time.sleep(2.2)
                body = json.dumps(expected).encode('utf-8')
                self.send_response(200); self.send_header('Content-Length', str(len(body)))
                self.end_headers(); self.wfile.write(body)
            def log_message(self, *args): pass
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            self.assertEqual(start.health(f'http://127.0.0.1:{server.server_port}'), expected)
        finally:
            server.shutdown(); server.server_close(); thread.join(timeout=2)

    @unittest.skipUnless(os.name == 'nt', 'Runs the actual Windows CMD interpreter')
    def test_batch_entrypoint_calls_python_in_chinese_path_and_keeps_failure_code(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / '中文 工厂 & !'
            root.mkdir()
            venv.EnvBuilder(with_pip=False).create(root / '.venv')
            (root / 'launcher').mkdir()
            (root / 'launcher/start.py').write_text(
                'import json,os,sys\nfrom pathlib import Path\n'
                'Path("called.json").write_text(json.dumps(sys.argv[1:]),encoding="utf-8")\n'
                'print("launcher reached",flush=True)\nsys.exit(int(os.environ["FACTORY_STUB_EXIT"]))\n', encoding='utf-8')
            # Reproduce packaging from an LF-only edited checkout, then execute its result.
            source = Path(__file__).resolve().parent.parent / '启动短剧工厂.cmd'
            edited = root / 'edited.cmd'
            edited.write_bytes(source.read_bytes().replace(b'\r\n', b'\n'))
            target = root / source.name
            copy_windows_batch(edited, target)
            for expected in (0, 7):
                result = subprocess.run([os.environ.get('COMSPEC', 'cmd.exe'), '/d', '/c', 'call', target.name, '--no-browser'],
                                        cwd=root, env={**os.environ, 'FACTORY_STUB_EXIT': str(expected)},
                                        input='\n', capture_output=True, encoding='utf-8', errors='replace', timeout=30)
                self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
                self.assertIn('launcher reached', result.stdout)
                self.assertEqual(json.loads((root / 'called.json').read_text(encoding='utf-8')), ['--no-browser'])
            # Explorer starts CMD with an absolute batch path and an unrelated working directory.
            for command in (f'""{target}" --no-browser"', f'chcp 936 >nul & call "{target}" --no-browser'):
                result = subprocess.run(f'"{os.environ.get("COMSPEC", "cmd.exe")}" /d /s /c {command}',
                                        cwd=directory, env={**os.environ, 'FACTORY_STUB_EXIT': '0'},
                                        input='\n', capture_output=True, encoding='utf-8', errors='replace', timeout=30)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn('launcher reached', result.stdout)
            # A source-only folder reports the exact inspected location instead of failing silently.
            missing = Path(directory) / '未安装'; missing.mkdir()
            copy_windows_batch(edited, missing / target.name)
            result = subprocess.run(f'"{os.environ.get("COMSPEC", "cmd.exe")}" /d /s /c ""{missing / target.name}""',
                                    cwd=directory, input='\n', capture_output=True, encoding='utf-8', errors='replace', timeout=30)
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn(str(missing), result.stdout)

    def test_running_panel_is_reused_without_spawning(self):
        with tempfile.TemporaryDirectory() as directory:
            for version in ('2.4.1', '3.0.0'):
                value={'version':version,'application_root':directory}
                with patch.object(start,'health',return_value=value),patch.object(start.subprocess,'Popen') as spawn,patch.object(start.webbrowser,'open') as browser:
                    self.assertEqual(start.launch(directory,no_browser=True),value)
                    spawn.assert_not_called();browser.assert_not_called()

    def test_other_directory_or_service_is_not_reused(self):
        with tempfile.TemporaryDirectory() as directory:
            for value in ({'version':'2.4.1','application_root':str(Path(directory)/'other')},{'version':'2.4.1'},{'version':'1.0','application_root':directory}):
                with patch.object(start,'health',return_value=value),patch.object(start.subprocess,'Popen') as spawn:
                    with self.assertRaises(RuntimeError):start.launch(directory,no_browser=True)
                    spawn.assert_not_called()

    def test_occupied_non_http_port_is_not_started(self):
        with patch.object(start,'health',return_value=None),patch.object(start.socket,'socket') as sock,patch.object(start.subprocess,'Popen') as spawn:
            sock.return_value.__enter__.return_value.connect_ex.return_value=0
            with self.assertRaisesRegex(RuntimeError,'占用'):start.launch(no_browser=True)
            spawn.assert_not_called()

    def test_fresh_start_uses_own_runtime_logs_and_temporary_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory).resolve();python=root/'runtime/python.exe';python.parent.mkdir();python.touch()
            value={'version':'3.0.0','application_root':str(root)}
            process=Mock();process.poll.return_value=None
            with patch.object(start,'health',side_effect=[None,value]),patch.object(start.socket,'socket') as sock,patch.object(start.subprocess,'Popen',return_value=process) as spawn,patch.object(start.webbrowser,'open') as browser:
                sock.return_value.__enter__.return_value.connect_ex.return_value=1
                self.assertEqual(start.launch(root,port=8779),value)
            args=spawn.call_args.args[0];options=spawn.call_args.kwargs
            self.assertEqual(Path(args[0]),python)
            self.assertEqual(options['env']['FACTORY_PORT'],'8779')
            self.assertEqual(Path(options['env']['TEMP']),root/'data/panel-temp')
            self.assertEqual(options['cwd'],root)
            self.assertTrue((root/'logs/panel.stderr.log').is_file())
            browser.assert_called_once_with('http://127.0.0.1:8779')

    def test_invalid_port_and_missing_runtime_have_actionable_errors(self):
        with self.assertRaises(ValueError):start.launch(port=0)
        with tempfile.TemporaryDirectory() as directory,patch.object(start,'health',return_value=None),patch.object(start.socket,'socket') as sock:
            sock.return_value.__enter__.return_value.connect_ex.return_value=1
            with self.assertRaisesRegex(RuntimeError,'Python'):start.launch(directory,no_browser=True)


if __name__=='__main__':unittest.main()
