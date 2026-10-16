"""Immutable, normalized image inputs, independent of generated gallery entries."""
from __future__ import annotations

import base64
import hashlib
import io
from pathlib import Path
import re
import shutil
import uuid

from PIL import Image, ImageOps, UnidentifiedImageError

from .storage import contained, read_json, write_json


class ImageInputs:
    def __init__(self, root):
        self.root = Path(root) / 'data/image-inputs'

    def upload(self, encoded, name=''):
        if not isinstance(encoded, str) or len(encoded) > 11_000_000:
            raise ValueError('参考图上限 8MB，支持 PNG、JPEG、WebP。')
        try:
            raw = base64.b64decode(encoded, validate=True)
        except ValueError:
            raise ValueError('参考图数据无效，请重新选择图片。') from None
        if len(raw) > 8_000_000:
            raise ValueError('参考图上限 8MB。')
        return self.add(raw, name)

    def add(self, raw, name=''):
        try:
            with Image.open(io.BytesIO(raw)) as source:
                if source.format not in ('PNG', 'JPEG', 'WEBP'):
                    raise ValueError('参考图支持 PNG、JPEG、WebP。')
                if source.width * source.height > 32_000_000:
                    raise ValueError('参考图最多 3200 万像素，请缩小后上传。')
                source.load()
                image = ImageOps.exif_transpose(source)
                image = image.convert('RGBA' if 'A' in image.getbands() or 'transparency' in image.info else 'RGB')
                image.info.clear()
                image.thumbnail((4096, 4096))
                while True:
                    buffer = io.BytesIO(); image.save(buffer, format='PNG')
                    data = buffer.getvalue()
                    if len(data) <= 8_000_000:
                        break
                    image.thumbnail((max(1, image.width // 2), max(1, image.height // 2)))
        except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
            raise ValueError('无法读取参考图，请使用完整的 PNG、JPEG 或 WebP 图片。') from None
        rid = hashlib.sha256(data).hexdigest()
        self.root.mkdir(parents=True, exist_ok=True)
        path = self.root / (rid + '.png')
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != rid:
            temporary = self.root / (rid + '.' + uuid.uuid4().hex + '.tmp')
            try:
                temporary.write_bytes(data)
                temporary.replace(path)
            finally:
                temporary.unlink(missing_ok=True)
        metadata = {'id': rid, 'name': str(name or '参考图')[:200], 'width': image.width,
                    'height': image.height, 'sha256': rid, 'size': len(data)}
        write_json(self.root / (rid + '.json'), metadata)
        return {**metadata, 'url': '/api/image-inputs/' + rid + '/file'}

    def get(self, rid):
        if not isinstance(rid, str) or not re.fullmatch(r'[0-9a-f]{64}', rid):
            raise ValueError('参考图标识无效。')
        path = self.root / (rid + '.png')
        metadata = read_json(self.root / (rid + '.json'), {})
        if not path.is_file() or not metadata:
            raise ValueError('参考图文件不存在，请重新上传。')
        return {**metadata, 'url': '/api/image-inputs/' + rid + '/file'}

    def file(self, rid):
        self.get(rid)
        return self.root / (rid + '.png')

    def snapshot(self, ids, folder):
        inputs = [self.get(rid) for rid in ids]
        result = []
        for item in inputs:
            source = self.file(item['id'])
            if hashlib.sha256(source.read_bytes()).hexdigest() != item['sha256']:
                raise ValueError('参考图文件已改变，请重新上传后生成。')
            relative = f'references/{item["id"]}.png'
            destination = contained(folder, relative)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
            result.append({**item, 'file': relative})
        return result
