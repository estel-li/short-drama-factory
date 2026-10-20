"""Small native H3 media adapters. No downloads, model patching or extra runtime."""
import torch
import torch.nn.functional as F
import torchaudio
import comfy.nested_tensor
import comfy.utils


def av_parts(latent):
    video, audio = latent['samples'].unbind()
    if video.ndim != 5 or video.shape[1] != 24 or audio.ndim != 4 or audio.shape[1:3] != (32, 2):
        raise ValueError('需要 MiniMax H3 的视频／音频配对潜空间。')
    return video, audio


def crop_audio(audio, start, seconds):
    if not audio or audio.get('waveform') is None:
        return {'sample_rate': 32000, 'waveform': torch.zeros(1, 2, round(seconds*32000))}
    sr = int(audio['sample_rate']);wave = audio['waveform']
    offset, length = round(start*sr), round(seconds*sr)
    if offset >= wave.shape[-1]:raise ValueError('音频起点超出源素材时长。')
    wave = wave[..., offset:offset+length]
    if wave.shape[-1] < length:wave = F.pad(wave, (0, length-wave.shape[-1]))
    return {'sample_rate': sr, 'waveform': wave}


class DramaH3AudioInput:
    @classmethod
    def INPUT_TYPES(cls):
        return {'required': {'audio': ('AUDIO',), 'start_seconds': ('FLOAT', {'default': 0, 'min': 0, 'max': 15}),
            'frames': ('INT', {'default': 107, 'min': 5, 'max': 362}), 'fps': ('FLOAT', {'default': 24})}}
    RETURN_TYPES = ('AUDIO',)
    FUNCTION = 'prepare'
    CATEGORY = '短剧工厂/H3 工作流'
    def prepare(self, audio, start_seconds, frames, fps):
        return (crop_audio(audio, start_seconds, frames/fps),)


class DramaH3VideoInput:
    @classmethod
    def INPUT_TYPES(cls):
        return {'required': {'images': ('IMAGE',), 'audio': ('AUDIO',), 'fps': ('FLOAT', {'default': 24}),
            'width': ('INT', {'default': 832, 'min': 32}), 'height': ('INT', {'default': 480, 'min': 32}),
            'frames': ('INT', {'default': 107, 'min': 1, 'max': 362}),
            'start_seconds': ('FLOAT', {'default': 0, 'min': 0, 'max': 15}), 'tail': ('BOOLEAN', {'default': False})}}
    RETURN_TYPES = ('IMAGE', 'AUDIO')
    FUNCTION = 'prepare'
    CATEGORY = '短剧工厂/H3 工作流'
    def prepare(self, images, audio, fps, width, height, frames, start_seconds, tail):
        if abs(fps-24) > 0.01:raise ValueError('源视频必须为 24fps，请通过工作台素材上传转换。')
        start = images.shape[0]-frames if tail else round(start_seconds*fps)
        if start < 0 or start+frames > images.shape[0]:
            raise ValueError('源视频可用帧数不足，请缩短目标镜头或更换源片。')
        result = images[start:start+frames, ..., :3]
        if tuple(result.shape[1:3]) != (height, width):
            result = comfy.utils.common_upscale(result.movedim(-1, 1), width, height, 'bicubic', 'center').movedim(1, -1)
        return result, crop_audio(audio, start/fps, frames/fps)


class DramaH3StageInputs:
    @classmethod
    def INPUT_TYPES(cls):
        return {'required': {'conditioning': ('CONDITIONING',), 'latent': ('LATENT',),
            'width': ('INT', {'default': 832}), 'height': ('INT', {'default': 480}), 'length': ('INT', {'default': 107})}}
    RETURN_TYPES = ('CONDITIONING', 'LATENT')
    FUNCTION = 'prepare'
    CATEGORY = '短剧工厂/H3 工作流'
    def prepare(self, conditioning, latent, width, height, length):
        video, _ = av_parts(latent)
        if (video.shape[-1]*16, video.shape[-2]*16) != (width, height):raise ValueError('媒体潜空间与项目尺寸不一致。')
        return conditioning, latent


class DramaH3AudioDrive:
    @classmethod
    def INPUT_TYPES(cls):
        return {'required': {'latent': ('LATENT',), 'audio': ('AUDIO',), 'audio_vae': ('VAE',)}}
    RETURN_TYPES = ('LATENT',)
    FUNCTION = 'prepare'
    CATEGORY = '短剧工厂/H3 工作流'
    def prepare(self, latent, audio, audio_vae):
        video, template = av_parts(latent)
        rate = int(getattr(audio_vae, 'audio_sample_rate', 32000))
        waveform = audio['waveform'][:1]
        if waveform.shape[1] == 1:waveform = waveform.repeat(1, 2, 1)
        elif waveform.shape[1] > 2:waveform = waveform[:, :2]
        if audio['sample_rate'] != rate:waveform = torchaudio.functional.resample(waveform, audio['sample_rate'], rate)
        encoded = audio_vae.encode(waveform.movedim(1, -1)).to(template)
        if encoded.shape[:-1] != template.shape[:-1]:raise ValueError('驱动音频 VAE 输出形状不匹配。')
        encoded = encoded[..., :template.shape[-1]]
        encoded = F.pad(encoded, (0, template.shape[-1]-encoded.shape[-1]))
        result = dict(latent)
        result['samples'] = comfy.nested_tensor.NestedTensor((video, encoded))
        result['noise_mask'] = comfy.nested_tensor.NestedTensor((torch.ones_like(video), torch.zeros_like(encoded)))
        return (result,)


class DramaH3FoleyLatent:
    @classmethod
    def INPUT_TYPES(cls):
        return {'required': {'latent': ('LATENT',), 'images': ('IMAGE',), 'vae': ('VAE',)}}
    RETURN_TYPES = ('LATENT',)
    FUNCTION = 'prepare'
    CATEGORY = '短剧工厂/H3 工作流'
    def prepare(self, latent, images, vae):
        template, audio = av_parts(latent)
        video = vae.encode(images[..., :3]).to(template)
        if video.shape != template.shape:raise ValueError('源视频编码帧数／尺寸与目标不一致。')
        result = dict(latent)
        result['samples'] = comfy.nested_tensor.NestedTensor((video, audio))
        result['noise_mask'] = comfy.nested_tensor.NestedTensor((torch.zeros_like(video), torch.ones_like(audio)))
        return (result,)


class DramaH3TrimAV:
    @classmethod
    def INPUT_TYPES(cls):
        return {'required': {'images': ('IMAGE',), 'audio': ('AUDIO',),
            'frames': ('INT', {'default': 107, 'min': 1, 'max': 362}), 'fps': ('FLOAT', {'default': 24})}}
    RETURN_TYPES = ('IMAGE', 'AUDIO')
    FUNCTION = 'prepare'
    CATEGORY = '短剧工厂/H3 工作流'
    def prepare(self, images, audio, frames, fps):
        if images.shape[0] < frames:raise ValueError('接续输出帧数不足，不能假报目标时长。')
        return images[:frames], crop_audio(audio, 0, frames/fps)


CLASSES = {cls.__name__: cls for cls in (DramaH3AudioInput, DramaH3VideoInput, DramaH3StageInputs,
    DramaH3AudioDrive, DramaH3FoleyLatent, DramaH3TrimAV)}
