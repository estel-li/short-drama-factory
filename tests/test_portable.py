import tempfile
import unittest
from pathlib import Path

from launcher.build_portable import locked_wheels


class PortableTests(unittest.TestCase):
    def test_only_locked_versions_and_compatible_abi_are_packaged(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);requirements=root/'requirements.txt'
            requirements.write_text('requests==2.34.2\nnumpy==2.5.4\nav==19.0.1\n')
            files=('requests-2.34.2-py3-none-any.whl','requests-2.0.0-py3-none-any.whl',
                   'numpy-2.5.4-cp313-cp313-win_amd64.whl','numpy-2.5.4-cp312-cp312-win_amd64.whl',
                   'numpy-2.5.4-cp313-cp313-manylinux_2_17_x86_64.whl','av-19.0.1-cp312-abi3-win_amd64.whl')
            for name in files:(root/name).touch()
            self.assertEqual({p.name for p in locked_wheels(root,requirements)},
                             {files[0],files[2],files[5]})
            requirements.write_text('requests==9.0.0\n')
            with self.assertRaisesRegex(ValueError,'requests'):locked_wheels(root,requirements)


if __name__=='__main__':unittest.main()
