import copy
import tempfile
import unittest
from pathlib import Path

import av
import pipeline
from app.storage import read_json, write_json


class MediaTests(unittest.TestCase):
    def test_concat_preserves_frames_order_audio_and_timestamps(self):
        original = copy.deepcopy(pipeline.CONFIG)
        try:
            pipeline.CONFIG['profiles']['test'] = {'megapixels': 0.1, 'steps': 4, 'turbo': True}
            width, height = pipeline.canvas(0.1, '9:16')
            with tempfile.TemporaryDirectory() as folder:
                project = Path(folder)
                write_json(project / 'settings.json', {'profile': 'test'})
                clips = []
                for color, count in [('red', 107), ('blue', 192)]:
                    clip = project / (color + '.mp4')
                    pipeline.ffmpeg(['-f', 'lavfi', '-i', f'color=c={color}:s={width}x{height}:r=24',
                        '-f', 'lavfi', '-i', 'sine=frequency=440:sample_rate=48000', '-c:v', 'libx264', '-bf', '0',
                        '-c:a', 'aac', '-frames:v', str(count), '-t', str(count/24), clip])
                    clips.append(clip)
                story = {'shots': [{'id': 1, 'duration': 4, 'dialogue': [{'text': '第一镜'}]}, {'id': 2, 'duration': 8, 'dialogue': []}]}
                final = pipeline.assemble(project, story, clips, '9:16', subtitles=False)
                info = pipeline.media_info(final, True)
                self.assertEqual(info['frames'], 299)
                self.assertTrue(info['audio'] and info['timestamps_monotonic'])
                self.assertAlmostEqual(info['fps'], 24)
                self.assertAlmostEqual(info['duration'], 299/24, places=3)
                with av.open(str(final)) as media:
                    samples = {i: bytes(frame.reformat(format='rgb24').planes[0])[:3] for i, frame in enumerate(media.decode(video=0)) if i in (0, 107)}
                self.assertGreater(samples[0][0], samples[0][2])
                self.assertGreater(samples[107][2], samples[107][0])
                self.assertEqual(read_json(project / '媒体验收.json')['expected_frames'], 299)
        finally:
            pipeline.CONFIG.clear()
            pipeline.CONFIG.update(original)


if __name__ == '__main__':
    unittest.main()
