import importlib.util
import json
from pathlib import Path
import tempfile
import subprocess
import sys
import unittest
import zipfile


SCRIPT = Path(__file__).resolve().parents[1] / 'agent-skills/short-drama-factory/scripts/install_skill.py'
spec = importlib.util.spec_from_file_location('skill_installer', SCRIPT)
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class SkillInstallTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.source, self.target = self.root / 'source', self.root / 'installed'
        (self.source / 'scripts').mkdir(parents=True)
        (self.source / 'SKILL.md').write_text('---\nname: short-drama-factory\nmetadata:\n  contract_version: 1\n---\nSkill', encoding='utf-8')
        for name in ('sdf.py', 'factory_api.py'):
            (self.source / 'scripts' / name).write_text('original', encoding='utf-8')
        (self.source / '.sdf').mkdir()
        (self.source / '.sdf/connection.json').write_text('local-only', encoding='utf-8')

    def test_local_install_and_update_preserve_personal_data_with_backup(self):
        first = installer.tracked_install(self.source, self.target)
        self.assertTrue(first['installed'])
        self.assertFalse((self.target / '.sdf').exists())
        (self.target / 'personal.txt').write_text('keep', encoding='utf-8')
        (self.source / 'scripts/sdf.py').write_text('updated', encoding='utf-8')
        second = installer.tracked_install(self.source, self.target, update=True)
        self.assertEqual((self.target / 'scripts/sdf.py').read_text(), 'updated')
        self.assertEqual((self.target / 'personal.txt').read_text(), 'keep')
        self.assertEqual((Path(second['backup']) / 'scripts/sdf.py').read_text(), 'original')

    def test_modified_managed_file_and_unknown_target_are_never_overwritten(self):
        installer.tracked_install(self.source, self.target)
        (self.target / 'scripts/sdf.py').write_text('personal edit', encoding='utf-8')
        with self.assertRaises(ValueError):
            installer.tracked_install(self.source, self.target, update=True)
        self.assertEqual((self.target / 'scripts/sdf.py').read_text(), 'personal edit')
        unknown = self.root / 'unknown'
        unknown.mkdir()
        (unknown / 'SKILL.md').write_text('custom', encoding='utf-8')
        with self.assertRaises(ValueError):
            installer.tracked_install(self.source, unknown, update=True)
        self.assertEqual((unknown / 'SKILL.md').read_text(), 'custom')

    def test_contract_validation_portable_zip_and_no_silent_overwrite(self):
        archive = self.root / 'skill.zip'
        result = installer.build_zip(self.source, archive)
        self.assertEqual(len(result['sha256']), 64)
        with zipfile.ZipFile(archive) as value:
            self.assertIn('short-drama-factory/scripts/sdf.py', value.namelist())
            self.assertFalse(any('.sdf/' in name for name in value.namelist()))
        with self.assertRaises(FileExistsError):
            installer.build_zip(self.source, archive)
        (self.source / 'SKILL.md').write_text('---\nname: short-drama-factory\nmetadata:\n  contract_version: 99\n---\n', encoding='utf-8')
        with self.assertRaises(ValueError):
            installer.tracked_install(self.source, self.target)
        self.assertFalse(self.target.exists())

    def test_overlap_and_manifest_traversal_are_rejected(self):
        with self.assertRaises(ValueError):
            installer.tracked_install(self.source, self.source / 'nested')
        installer.tracked_install(self.source, self.target)
        marker = self.target / installer.MARKER
        value = json.loads(marker.read_text())
        value['files']['../outside'] = 'fake'
        marker.write_text(json.dumps(value), encoding='utf-8')
        with self.assertRaises(ValueError):
            installer.tracked_install(self.source, self.target, update=True)

    def test_director_skill_installs_independently_and_keeps_its_package_identity(self):
        app = Path(__file__).resolve().parents[1]
        director = app / 'agent-skills/director-style'
        installed = installer.tracked_install(director, self.target)
        self.assertTrue(installed['installed'])
        archive = self.root / 'director.zip'
        installer.build_zip(director, archive)
        with zipfile.ZipFile(archive) as package:
            self.assertIn('director-style/scripts/director.py', package.namelist())
            self.assertIn('director-style/references/analysis.md', package.namelist())
        result = subprocess.run([sys.executable, '-I', str(self.target / 'scripts/director.py'), '--app', str(app), '--', 'style', '--help'],
                                cwd=self.root, capture_output=True, encoding='utf-8', timeout=15,
                                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('prepare', result.stdout)
        with self.assertRaisesRegex(ValueError, '另一种技能'):
            installer.tracked_install(self.source, self.target, update=True)


if __name__ == '__main__':
    unittest.main()
