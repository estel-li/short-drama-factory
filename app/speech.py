"""CPU speech detection and independent, threshold-sensitive energy diagnostics."""
from __future__ import annotations

import functools
import math
import os
import subprocess

import imageio_ffmpeg

from .downloads import Downloader
from .providers import Cancelled
from .storage import ROOT, read_json

SAMPLE_RATE = 16000


def ensure_model(status=lambda message: None, cancel=None, proxy='', download=True):
    model = read_json(ROOT / 'manifests/quality.json')['model']
    target = ROOT / 'data/quality' / model['filename']
    loader = Downloader(proxy=proxy)
    if loader.verified(target, model['size'], model['sha256'], cancel):
        return target
    if not download:
        return None
    from .execution_policy import enforce_download
    enforce_download('speech_detection/' + model['filename'])
    status('准备 CPU 语音检测模型（约 2.3 MB），固定版本并核对 SHA256。')
    return loader.fetch(model['url'], target, model['size'], model['sha256'],
                        lambda value: status('语音模型：' + value['status']), cancel)


@functools.lru_cache(maxsize=2)
def model_session(path, mtime_ns):
    import onnxruntime as ort
    settings = ort.SessionOptions()
    settings.intra_op_num_threads = settings.inter_op_num_threads = 1
    return ort.InferenceSession(path, sess_options=settings, providers=['CPUExecutionProvider'])


def pcm_audio(path, duration, cancel=None):
    import numpy as np
    from .processes import run_process
    result = run_process([imageio_ffmpeg.get_ffmpeg_exe(), '-hide_banner', '-loglevel', 'error',
        '-i', str(path), '-map', '0:a:0', '-vn', '-af', f'aresample={SAMPLE_RATE}:async=1:first_pts=0,atrim=duration={duration:.9f}',
        '-ac', '1', '-ar', str(SAMPLE_RATE), '-f', 'f32le', 'pipe:1'], capture_output=True,cancel=cancel,
        creationflags=0x08000000 if os.name == 'nt' else 0)
    if result.returncode:
        raise RuntimeError('无法解码音频用于质检：' + result.stderr.decode('utf-8', 'replace')[-800:])
    return np.frombuffer(result.stdout, dtype='<f4').copy()


def speech_probabilities(samples, model, cancel=None):
    import numpy as np
    session = model_session(str(model), model.stat().st_mtime_ns)
    state = np.zeros((2, 1, 128), dtype=np.float32)
    context = np.zeros((1, 64), dtype=np.float32)
    values = []
    for start in range(0, len(samples), 512):
        if cancel and cancel():
            raise Cancelled('语音检测已停止，原片已保留。')
        chunk = np.zeros((1, 512), dtype=np.float32)
        part = samples[start:start + 512]
        chunk[0, :len(part)] = part
        input_audio = np.concatenate((context, chunk), axis=1)
        probability, state = session.run(None, {'input': input_audio, 'state': state, 'sr': np.array(SAMPLE_RATE, dtype=np.int64)})
        values.append(float(probability.reshape(-1)[0]))
        context = input_audio[:, -64:].copy()
    return values


def intervals(values, step, duration, high=0.5, low=0.35, min_silence=0.16, min_active=0.12, pad=0.08):
    result, start, quiet = [], None, None
    for index, probability in enumerate(values):
        time = index * step
        if start is None:
            if probability >= high:
                start, quiet = time, None
        elif probability < low:
            if quiet is None:
                quiet = time
            if time - quiet >= min_silence:
                if quiet - start >= min_active:
                    result.append([max(0, start - pad), min(duration, quiet + pad)])
                start, quiet = None, None
        else:
            quiet = None
    if start is not None:
        end = quiet if quiet is not None else duration
        if end - start >= min_active:
            result.append([max(0, start - pad), min(duration, end + pad)])
    merged = []
    for a, b in result:
        if b <= a:
            continue
        if merged and a <= merged[-1][1]:
            merged[-1][1] = max(b, merged[-1][1])
        else:
            merged.append([a, b])
    return [[round(a, 5), round(b, 5)] for a, b in merged]


def rms_diagnostics(samples, duration):
    import numpy as np
    step, size = .02, 320
    count = math.ceil(len(samples) / size)
    values = []
    for index in range(count):
        part = samples[index*size:(index+1)*size]
        values.append(float(np.sqrt(np.mean(part.astype(np.float64)**2))) if len(part) else 0)
    noise = float(np.quantile(values, .2)) if values else 0
    strict_threshold, relaxed_threshold = max(.003, noise * 2.2), max(.0012, noise * 1.4)
    strict = intervals([float(v >= strict_threshold) for v in values], step, duration, min_silence=.30)
    relaxed = intervals([float(v >= relaxed_threshold) for v in values], step, duration, min_silence=.12)
    occupancy = lambda spans: round(sum(b-a for a,b in spans) / duration, 4) if duration else 0
    return {'method': 'relative_noise_floor_rms', 'noise_floor': noise, 'window_seconds': step,
            'strict_threshold': strict_threshold, 'relaxed_threshold': relaxed_threshold,
            'strict_intervals': strict, 'relaxed_intervals': relaxed,
            'strict_activity_density': occupancy(strict), 'relaxed_activity_density': occupancy(relaxed),
            'interpretation': '能量活动不等于人声；阈值复查用于诊断，自动裁剪由语音检测和保护区间决定。'}


def analyze_audio(samples, duration, model=None, cancel=None):
    energy = rms_diagnostics(samples, duration)
    if model is None:
        return {'method': 'rms_only', 'speech_intervals': [], 'relaxed_speech_intervals': [],
                'speech_density': None, 'safe_for_auto_edit': False, 'energy': energy,
                'warnings': ['未启用语音检测，能量诊断不能证明人声完整，保留原片，不自动裁剪。']}
    probabilities = speech_probabilities(samples, model, cancel)
    speech = intervals(probabilities, 512/SAMPLE_RATE, duration)
    relaxed = intervals(probabilities, 512/SAMPLE_RATE, duration, high=.35, low=.2, min_silence=.10)
    density = sum(b-a for a,b in speech) / duration if duration else 0
    return {'method': 'silero_vad_6.2.1_cpu', 'speech_intervals': speech, 'relaxed_speech_intervals': relaxed,
            'speech_density': round(density, 4), 'safe_for_auto_edit': bool(speech), 'energy': energy,
            'warnings': [], 'resolution_seconds': 512/SAMPLE_RATE,
            'measurement': '语音活动检测；不是语音识别或逐字强制对齐，台词内容仍需试听核对。'}
