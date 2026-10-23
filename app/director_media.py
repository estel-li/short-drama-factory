"""CPU reference evidence. Measurements never pretend to be semantic analysis."""
import hashlib
import math
from pathlib import Path
import subprocess
import time

import av
import numpy as np
from PIL import Image, ImageDraw

from .contracts import ContractError
from .processes import run_process
from .providers import Cancelled
from .storage import read_json, write_json


def sha256(path):
    result = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(block)
    return result.hexdigest()


def source_path(value):
    path = Path(value).expanduser()
    if not path.is_absolute() or path.suffix.lower() not in {'.mp4', '.mov', '.mkv', '.webm', '.avi', '.wav', '.mp3', '.m4a', '.flac', '.ogg'}:
        raise ContractError('INVALID_REFERENCE_SOURCE', '提供本机可读取的音视频文件绝对路径。')
    path = path.resolve()
    if not path.is_file():
        raise ContractError('REFERENCE_NOT_FOUND', '参考音视频文件不存在。', status=404)
    return path


def time_origin(media):
    if media.start_time is not None:
        return float(media.start_time / av.time_base)
    starts = [float(stream.start_time * stream.time_base) for stream in media.streams
              if stream.type in ('video', 'audio') and stream.start_time is not None and stream.time_base]
    return min(starts) if starts else 0.


def probe(path):
    with av.open(str(path), options={'protocol_whitelist': 'file,pipe'}) as media:
        video = next(iter(media.streams.video), None)
        audio = next(iter(media.streams.audio), None)
        primary = video or audio
        duration = (float(primary.duration * primary.time_base) + float((primary.start_time or 0) * primary.time_base) - time_origin(media)
                    if primary and primary.duration is not None else float(media.duration / av.time_base) if media.duration else 0)
        if not primary or not math.isfinite(duration) or not 0 < duration <= 14400:
            raise ContractError('REFERENCE_DURATION_UNSUPPORTED', '参考片必须有可测量的时长，单次最多 4 小时；可先切分长片。')
        return {'duration': duration, 'video': bool(video), 'audio': bool(audio),
                'width': video.width if video else None, 'height': video.height if video else None,
                'fps': float(video.average_rate) if video and video.average_rate else None,
                'audio_channels': audio.codec_context.channels if audio else None,
                'audio_layout': audio.codec_context.layout.name if audio else None,
                'audio_sample_rate': audio.codec_context.sample_rate if audio else None,
                'selected_streams': 'first_video_and_first_audio'}


def ffmpeg(args, cancel):
    import imageio_ffmpeg
    result = run_process([imageio_ffmpeg.get_ffmpeg_exe(), '-nostdin', '-hide_banner', '-loglevel', 'error', '-y',
                          '-protocol_whitelist', 'file,pipe', *map(str, args)], cancel=cancel, capture_output=True,
                         creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    if result.returncode:
        raise ContractError('REFERENCE_EXTRACTION_FAILED', '参考片证据导出失败；请检查文件可解码性与磁盘空间。')


def artifact(folder, relative, kind, **extra):
    path = folder / relative
    return {'path': relative, 'kind': kind, 'size': path.stat().st_size, 'sha256': sha256(path), **extra}


def extract_clip(source, folder, start, end, video, cancel, name, audio=True):
    suffix = '.mp4' if video else '.m4a'
    relative = 'clips/' + name + suffix
    target = folder / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    args = ['-ss', start, '-i', source, '-t', end - start]
    if video:
        args += ['-map', '0:v:0', '-map', '0:a:0?', '-vf', 'scale=480:480:force_original_aspect_ratio=decrease:force_divisible_by=2',
                 '-c:v', 'libx264', '-preset', 'veryfast', '-crf', 25]
    else:
        args += ['-vn', '-map', '0:a:0']
    if audio:
        args += ['-af', f'aresample=async=1:first_pts=0,apad,atrim=duration={end-start:.9f},asetpts=PTS-STARTPTS']
    args += ['-c:a', 'aac', '-b:a', '128k', target]
    ffmpeg(args, cancel)
    items = [artifact(folder, relative, 'motion_clip' if video else 'audio_clip', start=start, end=end,
                      time_mapping='clip time 0 corresponds to original start')]
    if video:
        # Dense time-labelled sheets let image-capable clients inspect motion
        # without claiming that an isolated key frame proves an action sequence.
        page, count, next_sample, times = None, 0, 0., []
        def save_page():
            name = relative.removesuffix('.mp4') + f'_sequence_{(count - 1) // 12:03d}.jpg'
            page.save(folder / name, quality=88)
            items.append(artifact(folder, name, 'motion_sequence', start=times[0], end=times[-1],
                                  sample_fps=6, frame_times=list(times)))
        with av.open(str(target)) as media:
            for frame in media.decode(video=0):
                if cancel():
                    raise Cancelled('连续片段证据提取已暂停。')
                seconds = float(frame.time or 0)
                if seconds + .001 < next_sample:
                    continue
                next_sample = seconds + 1 / 6
                if count % 12 == 0:
                    page = Image.new('RGB', (960, 820), '#202020')
                    times = []
                picture = frame.to_image()
                picture.thumbnail((310, 175))
                x, y = count % 3 * 320, count % 12 // 3 * 205
                page.paste(picture, (x, y))
                timestamp = round(start + seconds, 6)
                ImageDraw.Draw(page).text((x + 4, y + 178), f't={timestamp:.3f}s', fill='white')
                times.append(timestamp)
                count += 1
                if count % 12 == 0:
                    save_page()
            if count % 12:
                save_page()
    return items


def prepare(folder, request, report, cancel):
    source = source_path(request.source_path)
    if sha256(source) != request.source_sha256:
        raise ContractError('REFERENCE_CHANGED', '参考文件与提交时的哈希不同，请重新提交分析。', status=409)
    info = probe(source)
    start, end = request.start, min(request.end or info['duration'], info['duration'])
    if start >= end:
        raise ContractError('INVALID_REFERENCE_RANGE', '所选区间超出参考片时长。')
    if request.end is not None and request.end > info['duration'] + .1:
        raise ContractError('INVALID_REFERENCE_RANGE', 'end 超出参考片时长。')
    artifacts, frames, cuts, motion, audio_levels = [], [], [], [], []
    folder.mkdir(parents=True, exist_ok=True)
    interval = max(request.sample_seconds, (end - start) / max(1, int(request.max_frames * .75)))
    next_sample, last_cut, previous, last_report = start, start, None, 0
    cut_budget = request.max_frames - math.ceil((end - start) / interval)
    (folder / 'frames').mkdir(exist_ok=True)
    if info['video']:
        with av.open(str(source), options={'protocol_whitelist': 'file,pipe'}) as media:
            stream = media.streams.video[0]
            origin = time_origin(media)
            if start:
                media.seek(int((start + origin) / stream.time_base), stream=stream)
            for frame in media.decode(stream):
                if cancel():
                    raise Cancelled('参考片证据提取已暂停。')
                if frame.time is None:
                    continue
                seconds = float(frame.time) - origin
                if seconds < start:
                    continue
                if seconds >= end:
                    break
                gray = np.asarray(frame.reformat(width=64, height=36, format='rgb24').to_ndarray(), dtype=np.float32)
                delta = float(np.abs(gray - previous).mean() / 255) if previous is not None else 0
                previous = gray
                boundary = delta >= request.cut_threshold and seconds - last_cut >= .3
                if boundary:
                    cuts.append({'time': round(seconds, 6), 'score': round(delta, 5), 'kind': 'candidate_cut'})
                    last_cut = seconds
                regular = seconds >= next_sample
                if regular:
                    motion.append({'time': round(seconds, 6), 'frame_difference': round(delta, 5)})
                    next_sample = seconds + interval
                if len(frames) < request.max_frames and (regular or boundary and cut_budget > 0):
                    if not regular:
                        cut_budget -= 1
                    picture = frame.to_image()
                    picture.thumbnail((480, 320))
                    relative = f'frames/frame_{len(frames):04d}.jpg'
                    picture.save(folder / relative, quality=86)
                    row = artifact(folder, relative, 'frame', time=round(seconds, 6), candidate_cut=boundary)
                    artifacts.append(row)
                    frames.append(row)
                if time.monotonic() - last_report > 2:
                    report(f'正在提取参考画面：{seconds:.1f}/{end:.1f} 秒。')
                    last_report = time.monotonic()
        if not frames:
            raise ContractError('REFERENCE_VIDEO_EMPTY', '所选区间没有可解码的视频帧。')
        (folder / 'contact-sheets').mkdir(exist_ok=True)
        for offset in range(0, len(frames), 12):
            page = Image.new('RGB', (960, 4 * 205), '#202020')
            draw = ImageDraw.Draw(page)
            for number, row in enumerate(frames[offset:offset + 12]):
                with Image.open(folder / row['path']) as picture:
                    picture.thumbnail((310, 175))
                    x, y = number % 3 * 320, number // 3 * 205
                    page.paste(picture, (x, y))
                    draw.text((x + 4, y + 178), f"{offset+number:04d}  t={row['time']:.3f}s", fill='white')
            relative = f'contact-sheets/page_{offset // 12:03d}.jpg'
            page.save(folder / relative, quality=88)
            artifacts.append(artifact(folder, relative, 'contact_sheet'))
    if info['audio']:
        report('正在测量音频能量并导出试听音轨。')
        with av.open(str(source), options={'protocol_whitelist': 'file,pipe'}) as media:
            stream = media.streams.audio[0]
            origin = time_origin(media)
            if start:
                media.seek(int((start + origin) / stream.time_base), stream=stream)
            bins = {}
            for frame in media.decode(stream):
                if cancel():
                    raise Cancelled('参考音轨分析已暂停。')
                if frame.time is None:
                    continue
                seconds = float(frame.time) - origin
                if seconds >= end:
                    break
                if seconds + frame.samples / frame.sample_rate <= start:
                    continue
                # Reformat through PyAV to normalized planar floats, not codec-specific integer units.
                resampler = av.AudioResampler(format='fltp', layout='mono', rate=frame.sample_rate)
                values = np.concatenate([f.to_ndarray().reshape(-1) for f in resampler.resample(frame)]).astype(np.float64)
                times = seconds + np.arange(values.size) / frame.sample_rate
                keep = (times >= start) & (times < end)
                for bucket in np.unique(np.floor(times[keep]).astype(int)):
                    selected = values[keep & (np.floor(times) == bucket)]
                    row = bins.setdefault(int(bucket), [0., 0, 0.])
                    row[0] += float(np.square(selected).sum())
                    row[1] += selected.size
                    row[2] = max(row[2], float(np.abs(selected).max()))
            audio_levels = [{'start': max(start, float(second)), 'end': min(end, second + 1.),
                             'rms_dbfs': round(20 * math.log10(max(1e-9, math.sqrt(row[0] / row[1]))), 2),
                             'peak_dbfs': round(20 * math.log10(max(1e-9, row[2])), 2)} for second, row in sorted(bins.items())]
        ffmpeg(['-ss', start, '-i', source, '-t', end - start, '-vn', '-map', '0:a:0',
                '-af', f'aresample=async=1:first_pts=0,apad,atrim=duration={end-start:.9f},asetpts=PTS-STARTPTS',
                '-c:a', 'aac', '-b:a', '128k', folder / 'audio.m4a'], cancel)
        artifacts.append(artifact(folder, 'audio.m4a', 'audio', start=start, end=end))
    if request.max_clips:
        anchors = [row['time'] for row in cuts] or [start + (end - start) * i / request.max_clips for i in range(request.max_clips)]
        chosen = sorted({anchors[round(i * (len(anchors) - 1) / max(1, min(request.max_clips, len(anchors)) - 1))]
                         for i in range(min(request.max_clips, len(anchors)))})
        for index, anchor in enumerate(chosen):
            begin = max(start, min(anchor - 1, end - 6))
            artifacts.extend(extract_clip(source, folder, begin, min(end, begin + 6), info['video'], cancel, f'sample_{index:03d}', info['audio']))
    if sha256(source) != request.source_sha256:
        raise ContractError('REFERENCE_CHANGED', '提取过程中参考片发生变化，证据未发布。', status=409)
    value = {'schema_version': 1, 'status': 'prepared', 'source_sha256': request.source_sha256,
             'source_name': source.name, 'media': info, 'range': {'start': start, 'end': end},
             'sample_seconds': interval, 'candidate_cuts': cuts, 'motion_measurements': motion,
             'audio_levels': audio_levels, 'audio_measurement': 'mono_downmix_rms_and_peak_dbfs', 'artifacts': artifacts,
             'semantic_analysis': 'not_performed', 'coverage': {'decoded_video': bool(frames), 'decoded_audio': bool(audio_levels)},
             'limitations': ['切点和帧差为像素统计候选，运动与闪光也可能触发，需对照连续片段确认。',
                             '抽帧与音频能量不等于已理解动作、运镜、音乐、对白或风格；当前 AI 必须实际查看/试听。',
                             '压缩预览用于分析，生成风格不会自动采用原片人物、剧情或原声。']}
    write_json(folder / 'evidence.json', value)
    return value
