import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from launcher import start


class LauncherTests(unittest.TestCase):
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
