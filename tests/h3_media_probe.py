"""Optional CPU media integration checks using an installed ComfyUI Python.

python tests/h3_media_probe.py --comfy-dir PATH
No model weights, GPU generation, network or user project writes.
"""
import argparse
import importlib.util
import json
import sys
import tempfile
import time
from pathlib import Path
from types import SimpleNamespace

parser = argparse.ArgumentParser()
parser.add_argument('--comfy-dir', required=True)
args = parser.parse_args()
sys.path.insert(0, str(Path(args.comfy_dir).resolve()))
import av
import numpy as np
import torch

spec = importlib.util.spec_from_file_location('h3_media', Path(__file__).resolve().parents[1] / 'nodes/ComfyUI-DramaFactory/h3_media.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def fixture(path, audio=True, rate=24):
    with av.open(str(path), 'w') as container:
        video = container.add_stream('libx264', rate=rate)
        video.width, video.height, video.pix_fmt = 640, 360, 'yuv420p'
        track = container.add_stream('aac', rate=32000) if audio else None
        if track:
            track.layout = 'stereo'
        for i in range(144):
            pixels = np.full((360, 640, 3), i, dtype=np.uint8)
            frame = av.VideoFrame.from_ndarray(pixels, format='rgb24')
            for packet in video.encode(frame):
                container.mux(packet)
        for packet in video.encode():
            container.mux(packet)
        if audio:
            t = np.arange(192000) / 32000
            wave = (.25 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
            frame = av.AudioFrame.from_ndarray(np.stack([wave, wave]), format='fltp', layout='stereo')
            frame.sample_rate = 32000
            for packet in track.encode(frame):
                container.mux(packet)
            for packet in track.encode():
                container.mux(packet)


started = time.monotonic()
checks = []
with tempfile.TemporaryDirectory() as folder:
    folder = Path(folder)
    path = folder / 'source.mp4'
    fixture(path)
    source = SimpleNamespace(get_stream_source=lambda: str(path))
    node = module.DramaH3VideoSource()
    for tail, start, first in ((False, 1, 24), (True, 0, 122)):
        images, audio = node.prepare(source, 64, 32, 22, start, tail)
        assert tuple(images.shape) == (22, 32, 64, 3)
        assert abs(float(images[0].mean()) * 255 - first) < 4
        assert audio['waveform'].shape == (1, 2, round(22 / 24 * 32000))
        assert float(audio['waveform'].square().mean().sqrt()) > .1
        checks.append('tail with sound' if tail else 'offset with sound')
    try:
        node.prepare(source, 64, 32, 107, 2, False)
        raise AssertionError('short source accepted')
    except ValueError:
        checks.append('short source rejected')
    quiet = folder / 'silent.mp4'
    fixture(quiet, audio=False)
    _, audio = node.prepare(SimpleNamespace(get_stream_source=lambda: str(quiet)), 64, 32, 22, 0, True)
    assert audio['waveform'].count_nonzero() == 0
    checks.append('silent input produces exact-length silence')
    wrong = folder / 'wrong-fps.mp4'
    fixture(wrong, audio=False, rate=30)
    try:
        node.prepare(SimpleNamespace(get_stream_source=lambda: str(wrong)), 64, 32, 22, 0, False)
        raise AssertionError('incorrect fps accepted')
    except ValueError:
        checks.append('wrong fps rejected')
    # Audio locking must preserve mono resampling and the video branch.
    import comfy.nested_tensor
    video = torch.zeros(1, 24, 7, 2, 4)
    audio_template = torch.zeros(1, 32, 2, 50)
    latent = {'samples': comfy.nested_tensor.NestedTensor((video, audio_template))}
    observed = []
    vae = SimpleNamespace(audio_sample_rate=32000,
        encode=lambda wave: (observed.append(wave.shape) or torch.ones_like(audio_template)))
    result = module.DramaH3AudioDrive().prepare(latent,
        {'sample_rate': 22050, 'waveform': torch.ones(1, 1, 22050)}, vae)[0]
    assert observed == [torch.Size([1, 32000, 2])]
    video_mask, audio_mask = result['noise_mask'].unbind()
    assert video_mask.min() == 1 and audio_mask.max() == 0
    checks.append('mono resampling and locked audio mask')

print(json.dumps({'passed': len(checks), 'checks': checks, 'seconds': round(time.monotonic() - started, 3)}, ensure_ascii=False))
