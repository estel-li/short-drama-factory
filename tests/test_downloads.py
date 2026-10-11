import hashlib
import threading
import tempfile
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from app.downloads import Downloader


class DownloadTests(unittest.TestCase):
    def test_interrupted_download_resumes_and_is_verified(self):
        content = b'0123456789ABCDEF' * 100000
        checksum = hashlib.sha256(content).hexdigest()
        seen = []
        class Handler(BaseHTTPRequestHandler):
            fail_once = True
            def do_GET(self):
                start = int(self.headers.get('Range', 'bytes=0-')[6:-1])
                seen.append(start)
                self.send_response(206 if start else 200)
                self.send_header('Content-Length', str(len(content) - start))
                self.send_header('Content-Range', f'bytes {start}-{len(content)-1}/{len(content)}')
                self.end_headers()
                if Handler.fail_once:
                    Handler.fail_once = False
                    self.wfile.write(content[start:start + 700000])
                    self.wfile.flush()
                    self.close_connection = True
                else:
                    self.wfile.write(content[start:])
            def log_message(self, *args):
                pass
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory() as folder:
                path = Path(folder) / 'model.safetensors'
                url = 'http://127.0.0.1:' + str(server.server_port) + '/file'
                downloader = Downloader(retries=0)
                with self.assertRaises(RuntimeError):
                    downloader.fetch(url, path, len(content), checksum)
                self.assertFalse(path.exists())
                self.assertTrue(path.with_name(path.name + '.part').is_file())
                downloader.fetch(url, path, len(content), checksum)
                self.assertGreater(seen[-1], 0)
                self.assertEqual(path.read_bytes(), content)
                self.assertTrue(downloader.verified(path, len(content), checksum))
                before = len(seen)
                downloader.fetch(url, path, len(content), checksum)
                self.assertEqual(len(seen), before)
                path.write_bytes(b'X' * len(content))
                self.assertFalse(downloader.verified(path, len(content), checksum))
        finally:
            server.shutdown()
            server.server_close()


if __name__ == '__main__':
    unittest.main()
