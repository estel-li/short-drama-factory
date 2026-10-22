from __future__ import annotations

import base64
import io
import json
import time
from urllib.parse import urlsplit, urlunsplit

import httpx
from PIL import Image

from .schemas import Provider


class ProviderError(RuntimeError):
    pass


class RetryableProviderError(ProviderError):
    def __init__(self, message, delay=None):
        super().__init__(message)
        self.delay = delay


class Cancelled(RuntimeError):
    pass


class LLMClient:
    def __init__(self, provider: Provider, key='', proxy=''):
        self.provider, self.key, self.proxy = provider, key, proxy

    def headers(self):
        return {'Authorization': 'Bearer ' + self.key} if self.key else {}

    def url(self, path):
        return self.provider.base_url.rstrip('/') + '/' + path.lstrip('/')

    def origin(self):
        p = urlsplit(self.provider.base_url)
        return urlunsplit((p.scheme, p.netloc, '', '', ''))

    def client(self):
        local = self.provider.local or urlsplit(self.provider.base_url).hostname in ('localhost', '127.0.0.1', '::1')
        return httpx.Client(timeout=httpx.Timeout(self.provider.timeout, connect=20),
                            proxy=None if local else self.proxy or None, trust_env=not local, follow_redirects=False)

    def wait_retry(self, attempt, error, status=None, cancel=None):
        if attempt >= self.provider.retries:
            raise ProviderError(f'{error} 已用尽 {self.provider.retries} 次额外重试。') from error
        delay = min(30, max(0, getattr(error, 'delay', None) or 2 ** attempt))
        if status:
            status(f'{error} {delay:g} 秒后重试 {attempt + 1}/{self.provider.retries}。')
        end = time.monotonic() + delay
        while time.monotonic() < end:
            if cancel and cancel():
                raise Cancelled('重试等待已停止，已完成成果保留。')
            time.sleep(min(.1, max(0, end - time.monotonic())))

    @staticmethod
    def network_error(exc):
        if isinstance(exc, httpx.ConnectTimeout):
            return RetryableProviderError('连接或 HTTPS 握手超时，请检查网络与代理。')
        if isinstance(exc, httpx.ReadTimeout):
            return RetryableProviderError('等待模型响应超时。')
        return RetryableProviderError('模型网络连接中断（' + type(exc).__name__ + '）。')

    def check_response(self, response):
        if response.is_success:
            return
        code = response.status_code
        if code in (408, 425, 429) or 500 <= code <= 599:
            try:
                delay = float(response.headers.get('retry-after', '0'))
            except ValueError:
                delay = None
            raise RetryableProviderError(f'{self.provider.name} API 暂时失败 HTTP {code}。', delay)
        reasons = {400: '请求参数或模型不兼容', 401: '认证信息无效', 402: '账户余额不足',
                   403: '服务拒绝访问', 404: '模型或服务路径不存在', 422: '请求参数无效'}
        raise ProviderError(f'{self.provider.name} 请求失败 HTTP {code}：{reasons.get(code, "请检查地址、认证和模型配置")}。')

    def models(self):
        for attempt in range(self.provider.retries + 1):
            try:
                with self.client() as client:
                    result = client.get(self.url('models'), headers=self.headers())
                    self.check_response(result)
                    return [m['id'] for m in result.json().get('data', []) if isinstance(m.get('id'), str)]
            except httpx.RequestError as exc:
                self.wait_retry(attempt, self.network_error(exc))
            except RetryableProviderError as exc:
                self.wait_retry(attempt, exc)

    def generate(self, messages, schema=None, model='', status=None, cancel=None):
        from .execution_policy import enforce_provider_call
        enforce_provider_call('text_provider')
        p = self.provider
        if not (model or p.model):
            raise ProviderError('请先选择文字模型。')
        if p.kind == 'deepseek' and not self.key:
            raise ProviderError('请先配置 DeepSeek API key。')
        payload = {'model': model or p.model, 'messages': messages, 'temperature': p.temperature,
                   'max_tokens': p.max_tokens, 'stream': p.stream, **p.extra}
        if schema and (p.structured == 'schema' or (p.kind == 'lmstudio' and p.structured == 'json')):
            payload['response_format'] = {'type': 'json_schema', 'json_schema': {
                'name': 'stage_output', 'schema': schema, 'strict': True}}
        elif schema and p.structured == 'json':
            payload['response_format'] = {'type': 'json_object'}
        if p.stream:
            payload['stream_options'] = {'include_usage': True}
        usage = {}
        for attempt in range(p.retries + 1):
            if cancel and cancel():
                raise Cancelled('任务已停止。')
            pieces = []
            finish = None
            usage = {}
            started = time.monotonic()
            try:
                with self.client() as client:
                    with client.stream('POST', self.url('chat/completions'), headers=self.headers(), json=payload) as response:
                        self.check_response(response)
                        if p.stream:
                            for line in response.iter_lines():
                                if cancel and cancel():
                                    raise Cancelled('任务已停止。')
                                if time.monotonic() - started > p.timeout:
                                    raise RetryableProviderError('文字生成超过配置的总超时。')
                                if not line.startswith('data:'):
                                    continue
                                raw = line[5:].strip()
                                if raw == '[DONE]':
                                    break
                                event = json.loads(raw)
                                if event.get('error'):
                                    raise RetryableProviderError('模型服务在生成过程中返回错误。')
                                usage = event.get('usage') or usage
                                for choice in event.get('choices', []):
                                    pieces.append(choice.get('delta', {}).get('content') or '')
                                    finish = choice.get('finish_reason') or finish
                        else:
                            data = json.loads(response.read())
                            if data.get('error'):
                                raise RetryableProviderError('模型服务返回错误。')
                            choice = data['choices'][0]
                            pieces.append(choice['message'].get('content') or '')
                            usage, finish = data.get('usage') or {}, choice.get('finish_reason')
                if finish == 'length':
                    raise ProviderError('文字输出被截断，请提高最大输出长度或减小分镜批次。')
                content = ''.join(pieces).strip()
                if not content:
                    raise RetryableProviderError('模型没有返回文字内容。')
                if p.stream and finish is None:
                    raise RetryableProviderError('模型流式响应提前结束，没有完成标记。')
                return {'text': content, 'usage': usage, 'model': model or p.model, 'provider': p.id}
            except httpx.RequestError as exc:
                self.wait_retry(attempt, self.network_error(exc), status, cancel)
            except RetryableProviderError as exc:
                self.wait_retry(attempt, exc, status, cancel)
            except (json.JSONDecodeError, KeyError, TypeError) as exc:
                self.wait_retry(attempt, RetryableProviderError('模型接口响应不完整或格式不兼容。'), status, cancel)
        raise ProviderError('模型生成失败。')

    def probe(self, model=''):
        results = {'models': self.models(), 'capabilities': {}}
        schema = {'type': 'object', 'properties': {'ok': {'type': 'boolean'}}, 'required': ['ok'], 'additionalProperties': False}
        messages = [{'role': 'user', 'content': 'Return only JSON: {"ok":true}.'}]
        for label in ('text', 'stream', 'json', 'schema', 'vision'):
            value = self.provider.model_copy(deep=True)
            value.max_tokens, value.retries, value.timeout = 256, 0, min(value.timeout, 90)
            value.stream, value.structured = label == 'stream', label if label in ('json', 'schema') else 'text'
            probe_messages = messages
            if label == 'vision':
                output = io.BytesIO()
                Image.new('RGB', (32, 32), 'red').save(output, format='PNG')
                probe_messages = [{'role': 'user', 'content': [
                    {'type': 'text', 'text': 'Name the main color in this image in one word.'},
                    {'type': 'image_url', 'image_url': {'url': 'data:image/png;base64,' + base64.b64encode(output.getvalue()).decode()}}]}]
            try:
                result = LLMClient(value, self.key, self.proxy).generate(probe_messages, schema if label in ('json', 'schema') else None, model)
                if label in ('json', 'schema') and json.loads(result['text']).get('ok') is not True:
                    raise ValueError('结构化探测结果未通过校验。')
                if label == 'vision' and 'red' not in result['text'].lower() and '红' not in result['text']:
                    raise ValueError('图片颜色回答未通过校验。')
                results['capabilities'][label] = {'supported': True, 'verified': True}
            except (ProviderError, ValueError) as exc:
                results['capabilities'][label] = {'supported': False, 'verified': True, 'reason': str(exc)}
        return results

    def unload(self, model=''):
        if not self.provider.local or not self.provider.unload_after_use:
            return {'unloaded': False, 'reason': '当前提供商不需要卸载。'}
        try:
            with self.client() as client:
                if self.provider.kind == 'ollama':
                    response = client.post(self.origin() + '/api/generate', headers=self.headers(),
                                           json={'model': model or self.provider.model, 'keep_alive': 0})
                    response.raise_for_status()
                    return {'unloaded': True}
                if self.provider.kind == 'lmstudio':
                    response = client.get(self.origin() + '/api/v1/models', headers=self.headers())
                    response.raise_for_status()
                    instances = []
                    for entry in response.json().get('models', []):
                        if entry.get('key') == (model or self.provider.model) or any(i.get('id') == (model or self.provider.model) for i in entry.get('loaded_instances', [])):
                            instances.extend(i['id'] for i in entry.get('loaded_instances', []))
                    for instance in instances:
                        response = client.post(self.origin() + '/api/v1/models/unload', headers=self.headers(), json={'instance_id': instance})
                        response.raise_for_status()
                    return {'unloaded': True, 'instances': instances}
        except (httpx.HTTPError, KeyError) as exc:
            raise ProviderError('本地文字模型卸载失败，请关闭模型后再运行 H3。') from exc
        raise ProviderError('自定义本地服务没有卸载适配器。请关闭模型或设置仅 CPU 运行并关闭自动卸载。')
