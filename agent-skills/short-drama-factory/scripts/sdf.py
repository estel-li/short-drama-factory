#!/usr/bin/env python3
"""Short Drama Factory task CLI. Stdlib only; all output and failures are JSON.

Copy this script together with factory_api.py to use it outside the application.
Connecting and diagnosis never start a service, resume a queue, or generate media.
"""
from __future__ import annotations

import argparse
import base64
import copy
import hashlib
from http.client import HTTPException
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import uuid
from urllib.parse import quote, urlencode

from factory_api import APIError, Client, emit, get_job, identifier, load_body, watch


CONTEXT_VERSION = 1
SUPPORTED_PROTOCOLS = (1,)
DEFAULT_URL = "http://127.0.0.1:8765"
SENSITIVE_FIELDS = {'api_key', 'api_token', 'access_token', 'password', 'authorization', 'comfy_auth_token', 'secret'}


class Parser(argparse.ArgumentParser):
    def error(self, message):
        if 'unrecognized arguments:' in message:
            # An accidentally supplied --value TOKEN must not be echoed.
            message = '存在不支持的参数；凭证仅支持 --env 变量名或 --stdin。'
        raise APIError(message, payload={"code": "invalid_arguments", "retryable": False})


def positive_limit(value):
    try:
        number = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError("limit 必须为整数。") from None
    if not 1 <= number <= 200:
        raise argparse.ArgumentTypeError("limit 必须为 1～200。")
    return number


def bounded_wait(value):
    number = float(value)
    if not 0 < number <= 45:
        raise argparse.ArgumentTypeError('等待时间必须大于 0 且不超过 45 秒；超时不会停止后台任务。')
    return number


def same_path(first, second):
    return os.path.normcase(str(Path(first).resolve())) == os.path.normcase(str(Path(second).resolve()))


def read_context(path):
    if not path.exists():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        raise APIError("连接文件无法读取；请重新运行 connect。", payload={"code": "invalid_connection"}) from None
    if (not isinstance(value, dict) or value.get("version") != CONTEXT_VERSION
            or not isinstance(value.get("base_url"), str)
            or not isinstance(value.get("application_root"), str)):
        raise APIError("连接文件版本或内容无效；请重新运行 connect。", payload={"code": "invalid_connection"})
    return value


def verify_health(client, application_root=None):
    health = client.request("GET", "/api/health")
    protocol = health.get("protocol_version")
    if type(protocol) is not int or protocol not in SUPPORTED_PROTOCOLS:
        raise APIError("服务协议版本不受支持，请使用兼容的工厂和技能版本。",
                       payload={"code": "unsupported_protocol", "retryable": False,
                                "next_actions": ["更新工厂与技能，确保 protocol_version 为 1。"]})
    root = health.get("application_root")
    if not isinstance(root, str) or not root:
        raise APIError("服务未返回 application_root，无法核对实例。", payload={"code": "missing_instance_identity"})
    if application_root is not None and not same_path(root, application_root):
        raise APIError("地址对应的 application_root 与指定应用目录不同。",
                       payload={"code": "instance_mismatch", "retryable": False,
                                "next_actions": ["核对 --app 和 --url；不会自动切换或启动服务。"]})
    return health


def connect(args):
    app = Path(args.app).expanduser().resolve()
    if not app.is_dir():
        raise APIError("指定的应用目录不存在。", payload={"code": "application_not_found"})
    client = Client(args.url or args.base_url or os.environ.get("DRAMA_FACTORY_URL", DEFAULT_URL), args.timeout)
    health = verify_health(client, app)
    connection = {"version": CONTEXT_VERSION, "base_url": client.base,
                  "application_root": str(app), "protocol_version": health["protocol_version"],
                  "app_version": health.get("app_version", health.get("version"))}
    path = Path(args.context).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    # Atomic replacement keeps a previous binding usable if writing fails.
    temporary = path.with_name(path.name + f".{os.getpid()}.tmp")
    try:
        temporary.write_text(json.dumps(connection, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)
    return {"connected": True, "context": str(path), **connection}


def client_for(args):
    context = read_context(Path(args.context).expanduser().resolve())
    url = args.base_url or os.environ.get("DRAMA_FACTORY_URL") or (context or {}).get("base_url") or DEFAULT_URL
    client = Client(url, args.timeout)
    # An explicit URL is an explicit instance selection; otherwise enforce the saved binding.
    if context and not args.base_url and not os.environ.get("DRAMA_FACTORY_URL"):
        verify_health(client, context["application_root"])
    return client


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    try:
        with temporary.open('x', encoding='utf-8') as stream:
            json.dump(value, stream, ensure_ascii=False, allow_nan=False, indent=2)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def request_key(value):
    if (not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', value)
            or re.fullmatch(r'(?i)(con|prn|aux|nul|com[1-9]|lpt[1-9])', value)):
        raise argparse.ArgumentTypeError('请求标识使用 1～128 位 ASCII 字母、数字、下划线或连字符；不能是系统保留文件名。')
    return value


def check_no_credentials(value):
    if isinstance(value, dict):
        if any(str(key).lower() in SENSITIVE_FIELDS for key in value):
            raise APIError('凭证不能写入请求文件或操作账本，请使用 credential set。', payload={'code': 'credential_in_request'})
        for item in value.values():
            check_no_credentials(item)
    elif isinstance(value, list):
        for item in value:
            check_no_credentials(item)


def ledger_path(args, key):
    return Path(args.context).expanduser().resolve().parent / 'requests' / (request_key(key) + '.json')


def request_checksum(method, path, body):
    canonical = json.dumps({'method': method, 'path': path, 'body': body}, sort_keys=True, ensure_ascii=False,
                           separators=(',', ':'), allow_nan=False)
    return hashlib.sha256(canonical.encode('utf-8')).hexdigest()


def replay_route_allowed(method, path):
    if method == 'PATCH':
        return path == '/api/v2/config' or bool(re.fullmatch(r'/api/v2/projects/[A-Za-z0-9_-]+', path))
    if method != 'POST':
        return False
    return path in ('/api/v2/projects', '/api/v2/images', '/api/v2/image-inputs', '/api/v2/environment/speech/prepare') or bool(
        re.fullmatch(r'/api/v2/projects/[A-Za-z0-9_-]+/(validate|plans|run|assets)', path)
        or re.fullmatch(r'/api/v2/jobs/[A-Za-z0-9_-]+/(resume|stop)', path))


def read_receipt(args, key):
    path = ledger_path(args, key)
    if not path.is_file():
        raise APIError('本地没有该请求账本。', payload={'code': 'local_operation_not_found', 'request_key': key})
    value = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(value, dict) or value.get('request_key') != key or value.get('version') != 1:
        raise APIError('请求账本无效。', payload={'code': 'invalid_operation_receipt'})
    if (not isinstance(value.get('method'), str) or not isinstance(value.get('path'), str)
            or not isinstance(value.get('body'), dict) or not isinstance(value.get('base_url'), str)
            or value.get('request_hash') != request_checksum(value['method'], value['path'], value['body'])):
        raise APIError('请求账本内容与保存的摘要不一致，拒绝恢复。', payload={'code': 'invalid_operation_receipt'})
    return value


def mutation(args, client, method, path, body, *, key=None, replayable=True):
    """Durably publish the exact request before submitting once. Never retry."""
    check_no_credentials(body)
    key = request_key(key or getattr(args, 'request_key', None) or uuid.uuid4().hex)
    target = ledger_path(args, key)
    checksum = request_checksum(method, path, body)
    if target.exists():
        record = read_receipt(args, key)
        if record.get('request_hash') != checksum or record.get('base_url') != client.base:
            raise APIError('此请求标识已用于不同内容或实例；请保留原请求并换用新标识。',
                           payload={'code': 'local_idempotency_conflict', 'request_key': key})
    else:
        record = {'version': 1, 'request_key': key, 'base_url': client.base, 'method': method, 'path': path,
                  'body': body, 'request_hash': checksum, 'status': 'prepared', 'replayable': replayable, 'result': None}
        # Exclusive creation prevents concurrent commands from reserving the same
        # local key for different bodies before either reaches the server.
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            with target.open('x', encoding='utf-8') as stream:
                json.dump(record, stream, ensure_ascii=False, allow_nan=False)
                stream.flush()
                os.fsync(stream.fileno())
        except FileExistsError:
            return mutation(args, client, method, path, body, key=key, replayable=replayable)
    recovery = 'sdf operation get ' + key
    emit({'event': 'request_saved', 'request_key': key, 'receipt': str(target), 'recovery_command': recovery})
    try:
        health = verify_health(client)
        owner = health['application_root']
        if record.get('application_root') and not same_path(record['application_root'], owner):
            raise APIError('请求账本属于其他应用实例，拒绝重发。', payload={'code': 'instance_mismatch'})
        record['application_root'] = owner
        if record.get('status') == 'completed':
            return record['result']
        if record.get('status') not in ('prepared',) and not getattr(args, 'explicit_retry', False):
            raise APIError('此请求已提交或结果未知；先查询原操作，重发需使用 operation retry。',
                           payload={'code': 'operation_requires_recovery'})
        if getattr(args, 'explicit_retry', False) and not record.get('replayable'):
            raise APIError('旧接口没有幂等保障，不能自动重发该操作；请读取当前状态后提交新操作。',
                           payload={'code': 'operation_not_replayable'})
        record['status'] = 'submitted'
        atomic_json(target, record)
        result = client.request(method, path, body, headers={'Idempotency-Key': key})
        record.update(status='completed', result=result)
        atomic_json(target, record)
        return result
    except (APIError, OSError, ValueError, HTTPException) as failure:
        exc = failure if isinstance(failure, APIError) else APIError(
            '本地回执保存或响应处理失败；请按请求标识查询服务器结果，勿直接创建新请求。',
            payload={'code': 'operation_result_unknown'})
        if record.get('status') == 'submitted':
            record.update(status='unknown' if exc.http_status is None or exc.http_status >= 500 else 'rejected', error=exc.payload)
            try:
                atomic_json(target, record)
            except OSError:
                pass  # The original pre-submit ledger still identifies the request.
        exc.payload.update(request_key=key, receipt=str(target), recovery_command=recovery,
                           retry_command='sdf operation retry ' + key, retried=False)
        raise exc from None


def body_file(args):
    return load_body(args.json_file) if getattr(args, 'json_file', None) else {}


def create_body(value):
    body = copy.deepcopy(value)
    if body.get('start') is not None and body.get('start') is not False:
        raise APIError('创建项目仅创建草稿；start:true 不受支持，请使用计划和 run。', payload={'code': 'implicit_generation_rejected'})
    body.pop('start', None)
    return body


def with_revision(client, pid, body, expected=None, *, args=None, key=None):
    value = copy.deepcopy(body)
    if expected and value.get('expected_revision') and value['expected_revision'] != expected:
        raise APIError('参数与文件里的 expected_revision 不一致。', payload={'code': 'revision_argument_conflict'})
    if not expected and not value.get('expected_revision') and args is not None:
        token = key or getattr(args, 'request_key', None)
        if token and ledger_path(args, token).is_file():
            old = read_receipt(args, token)
            previous = old.get('body') or {}
            if old.get('path') == '/api/v2/projects/' + pid and {k: v for k, v in previous.items() if k != 'expected_revision'} == value:
                value['expected_revision'] = previous.get('expected_revision')
    value['expected_revision'] = expected or value.get('expected_revision') or client.request('GET', '/api/v2/projects/' + pid)['revision']
    return value


def plan_request(args):
    value = body_file(args)
    for key, option in (('action', 'plan_action'), ('uids', 'uids')):
        if getattr(args, option, None) is not None:
            value[key] = getattr(args, option)
    if getattr(args, 'allow_internal_text', False):
        value['internal_text'] = 'allowed'
    return value


def submit_plan(args, client, pid, body, key=None):
    # Planning writes only a deterministic plan. Explicit replay is safe but may
    # return a new plan if project inputs changed; run still validates its ID.
    return mutation(args, client, 'POST', f'/api/v2/projects/{pid}/plans', body, key=key)


def submit_run(args, client, pid, plan_id, key=None):
    return mutation(args, client, 'POST', f'/api/v2/projects/{pid}/run', {'plan_id': plan_id}, key=key)


def maybe_watch(args, client, result):
    emit(result)
    wait = getattr(args, 'wait', None)
    return watch(client, None, result['job_id'], wait) if wait is not None and result.get('job_id') else 0


def start_service(args):
    app = Path(args.app).expanduser().resolve()
    script = app / 'launcher/start.py'
    if not script.is_file() or not 1 <= args.port <= 65535:
        raise APIError('找不到应用启动器或端口无效。', payload={'code': 'invalid_application'})
    # The launcher launches the persistent server itself. Its bounded startup
    # probe does not resume old tasks when --serve-only is supplied.
    result = subprocess.run([sys.executable, str(script), '--port', str(args.port), '--no-browser', '--serve-only'],
                            cwd=app, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=55,
                            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    if result.returncode:
        raise APIError('启动未成功，请检查应用 logs/panel.stderr.log。', payload={'code': 'startup_failed'})
    args.url = f'http://127.0.0.1:{args.port}'
    return connect(args)


def credential_set(args, client):
    value = os.environ.get(args.env) if args.env else sys.stdin.readline(4097).rstrip('\r\n')
    if value is None or not value.strip() or len(value) > 4000 or '\n' in value or '\r' in value:
        raise APIError('凭证输入为空或格式无效。', payload={'code': 'invalid_credential_input'})
    key = request_key(getattr(args, 'request_key', None) or uuid.uuid4().hex)
    # Credentials deliberately have no body ledger, response echo or automatic
    # recovery. The user can explicitly re-enter the value if submission fails.
    emit({'event': 'credential_submission', 'request_key': key, 'provider': args.provider, 'body_saved': False})
    verify_health(client)
    try:
        client.request('POST', '/api/provider/key', {'id': args.provider, 'key': value}, headers={'Idempotency-Key': key})
    except APIError:
        raise APIError('凭证设置未确认；请检查配置状态，需要时显式重新输入。',
                       payload={'code': 'credential_result_unknown', 'request_key': key, 'retried': False}) from None
    return {'configured': True, 'provider': args.provider, 'request_key': key}


def parser():
    result = Parser(description=__doc__)
    result.add_argument("--base-url")
    result.add_argument("--timeout", type=float, default=30)
    result.add_argument("--context", default=str(Path.cwd() / ".sdf" / "connection.json"))
    commands = result.add_subparsers(dest="command", required=True)
    connection = commands.add_parser("connect", help="绑定并核对已经运行的本地实例")
    connection.add_argument("--app", required=True)
    connection.add_argument("--url")
    start = commands.add_parser('start', help='启动无界面 API，不恢复旧队列')
    start.add_argument('--app', required=True)
    start.add_argument('--port', type=int, default=8765)
    commands.add_parser("doctor", help="只读检查环境和可用能力")
    commands.add_parser("capabilities", help="读取机器可用的能力目录")
    job = commands.add_parser("job", help="查询或观察持久任务")
    actions = job.add_subparsers(dest="action", required=True)
    get = actions.add_parser("get")
    get.add_argument("id", type=identifier)
    listing = actions.add_parser("list")
    listing.add_argument("--project", type=identifier)
    listing.add_argument("--status")
    listing.add_argument("--limit", type=positive_limit, default=100)
    listing.add_argument("--before")
    events = actions.add_parser("events")
    events.add_argument("id", type=identifier)
    events.add_argument("--after", type=int, default=0)
    monitor = actions.add_parser("watch")
    monitor.add_argument("id", type=identifier)
    monitor.add_argument("--project", type=identifier)
    monitor.add_argument("--seconds", type=float, default=45)
    monitor.add_argument("--interval", type=float, default=5)
    resume = actions.add_parser('resume')
    resume.add_argument('id', type=identifier)
    resume.add_argument('--expected-revision')
    resume.add_argument('--request-key', type=request_key)
    stop = actions.add_parser('stop')
    stop.add_argument('id', type=identifier)
    stop.add_argument('--immediate', action='store_true')
    stop.add_argument('--request-key', type=request_key)

    def json_input(command, required=True):
        command.add_argument('--json', dest='json_file', required=required, help='UTF-8 JSON 文件；- 读取标准输入')

    def write_options(command, wait=False):
        command.add_argument('--request-key', type=request_key)
        if wait:
            command.add_argument('--wait', nargs='?', type=bounded_wait, const=45, help='有界观察原任务，默认 45 秒')

    project = commands.add_parser('project')
    projects = project.add_subparsers(dest='action', required=True)
    projects.add_parser('list')
    project_get = projects.add_parser('get')
    project_get.add_argument('id', type=identifier)
    create = projects.add_parser('create')
    json_input(create)
    write_options(create)
    validate = projects.add_parser('validate')
    validate.add_argument('id', type=identifier)
    write_options(validate)
    update = projects.add_parser('update')
    update.add_argument('id', type=identifier)
    update.add_argument('--expected-revision')
    json_input(update)
    write_options(update)
    planning = projects.add_parser('plan')
    planning.add_argument('id', type=identifier)
    json_input(planning, required=False)
    planning.add_argument('--action', dest='plan_action', choices=('render', 'plan', 'finish'))
    planning.add_argument('--uids', nargs='+', type=identifier)
    planning.add_argument('--allow-internal-text', action='store_true')
    write_options(planning)
    run = projects.add_parser('run')
    run.add_argument('id', type=identifier)
    run.add_argument('--plan', required=True, type=identifier)
    write_options(run, wait=True)
    produce = commands.add_parser('produce', help='创建草稿、计算严格渲染计划并按计划执行')
    json_input(produce)
    write_options(produce, wait=True)

    shot = commands.add_parser('shot')
    shots = shot.add_subparsers(dest='action', required=True)
    for action in ('update', 'regenerate'):
        item = shots.add_parser(action)
        item.add_argument('project', type=identifier)
        item.add_argument('uid', type=identifier)
        item.add_argument('--expected-revision')
        write_options(item, wait=action == 'regenerate')
        if action == 'update':
            json_input(item)
        else:
            item.add_argument('--seed', type=int, help='仅显式提供时修改种子；默认强制重生成但保留配置种子')

    operation = commands.add_parser('operation')
    operations = operation.add_subparsers(dest='action', required=True)
    for action in ('get', 'retry'):
        item = operations.add_parser(action)
        item.add_argument('key', type=request_key)
    config = commands.add_parser('config')
    configurations = config.add_subparsers(dest='action', required=True)
    configurations.add_parser('get')
    config_patch = configurations.add_parser('patch')
    json_input(config_patch)
    write_options(config_patch)
    prompt = commands.add_parser('prompt')
    prompts = prompt.add_subparsers(dest='action', required=True)
    compile_prompt = prompts.add_parser('compile', help='从外部 AI 的章节文本确定性组装 H3 提示词；不保存或调用模型')
    compile_prompt.add_argument('--project', required=True, type=identifier)
    compile_prompt.add_argument('--shot', required=True, type=identifier)
    json_input(compile_prompt)
    credential = commands.add_parser('credential')
    credentials = credential.add_subparsers(dest='action', required=True)
    setting = credentials.add_parser('set')
    setting.add_argument('--provider', required=True, type=identifier)
    source = setting.add_mutually_exclusive_group(required=True)
    source.add_argument('--env', help='本地环境变量名；不在参数中填写密钥值')
    source.add_argument('--stdin', action='store_true')
    write_options(setting)

    image = commands.add_parser('image')
    images = image.add_subparsers(dest='action', required=True)
    images.add_parser('list')
    image_get = images.add_parser('get')
    image_get.add_argument('id', type=identifier)
    image_create = images.add_parser('create')
    json_input(image_create)
    image_create.add_argument('--allow-internal-text', action='store_true')
    write_options(image_create, wait=True)
    image_input = images.add_parser('input')
    image_input.add_argument('--file', required=True)
    write_options(image_input)
    asset = commands.add_parser('asset')
    uploads = asset.add_subparsers(dest='action', required=True)
    upload = uploads.add_parser('upload')
    upload.add_argument('--project', required=True, type=identifier)
    upload.add_argument('--file', required=True)
    upload.add_argument('--kind', required=True, choices=('image', 'video', 'audio'))
    upload.add_argument('--character', default='')
    write_options(upload)
    environment = commands.add_parser('environment')
    environments = environment.add_subparsers(dest='action', required=True)
    environments.add_parser('speech-plan')
    prepare = environments.add_parser('speech-prepare')
    prepare.add_argument('--confirmation', required=True)
    write_options(prepare)
    deliver = commands.add_parser('deliver', help='读取交付清单，可核验并下载当前版本产物')
    deliver.add_argument('project', type=identifier)
    deliver.add_argument('--verify', action='store_true', help='请求服务器完整解码当前成片；内容验收仍单独记录')
    deliver.add_argument('--output', help='可选新建输出目录；已有目录不会覆盖')
    deliver.add_argument('--include-shots', action='store_true', help='同时下载当前分镜原片，不包含历史版本视频')
    batch = commands.add_parser('batch', help='按已有执行计划逐项目排队；每项独立记录结果')
    json_input(batch)
    batch.add_argument('--request-key', required=True, type=request_key)
    batch.add_argument('--retry-unknown', action='store_true', help='仅显式重发结果未知的原请求；不重发明确拒绝项')
    return result


def phase_key(root, phase):
    return hashlib.sha256((root + '/' + phase).encode('utf-8')).hexdigest()


def upload_body(path):
    source = Path(path).expanduser()
    if source.stat().st_size > 8_000_000:
        raise APIError('上传文件超过 8MB，请先缩小或截短。', payload={'code': 'asset_too_large'})
    return {'name': source.name, 'data': base64.b64encode(source.read_bytes()).decode('ascii')}


def delivery_selection(manifest, pid, include_shots):
    current = manifest.get('version_id')
    selected, paths = [], set()
    common = {'original', 'subtitled', 'subtitles', 'subtitle_script', 'recorded_report'}
    evidence = {'review_index', 'review_page', 'edit_recipe.json', 'edit_媒体验收.json', 'edit_completed.json'}
    artifacts = manifest.get('artifacts', [])
    if not isinstance(artifacts, list) or any(not isinstance(item, dict) or not isinstance(item.get('kind'), str) for item in artifacts):
        raise APIError('交付清单的文件列表无效。', payload={'code': 'invalid_delivery_manifest'})
    for artifact in artifacts:
        kind = artifact.get('kind')
        if not (kind in common or kind in evidence and current and artifact.get('version_id') == current
                or include_shots and kind == 'shot_clip'):
            continue
        name = artifact.get('relative_path')
        if not isinstance(name, str) or not name or '\\' in name or ':' in name or any(ord(character) < 32 for character in name):
            raise APIError('交付清单含无效文件路径。', payload={'code': 'invalid_delivery_path'})
        relative = PurePosixPath(name)
        if (relative.is_absolute() or relative.as_posix() != name or any(part in ('', '.', '..')
                or part.startswith('.') or part.endswith((' ', '.'))
                or re.fullmatch(r'(?i)(con|prn|aux|nul|com[1-9]|lpt[1-9])', part.split('.')[0]) for part in relative.parts)
                or name.casefold() == 'delivery.json' or name.casefold() in paths):
            raise APIError('交付清单含越界、保留或重复文件路径。', payload={'code': 'invalid_delivery_path'})
        expected_url = f'/api/v2/projects/{pid}/delivery/files/' + quote(name, safe='/')
        if artifact.get('api_url') != expected_url:
            raise APIError('交付文件地址不属于当前项目专用下载接口。', payload={'code': 'invalid_delivery_url'})
        if (not isinstance(artifact.get('sha256'), str) or not re.fullmatch(r'[a-f0-9]{64}', artifact['sha256'])
                or type(artifact.get('size')) is not int or artifact['size'] < 0):
            raise APIError('交付清单缺少有效 SHA256 或文件大小。', payload={'code': 'invalid_delivery_integrity'})
        paths.add(name.casefold())
        selected.append(artifact)
    return selected


def deliver_artifacts(args, client):
    manifest = client.request('GET', f'/api/v2/projects/{args.project}/delivery?' + urlencode({'verify': str(args.verify).lower()}))
    if not isinstance(manifest, dict) or manifest.get('project_id') != args.project:
        raise APIError('交付清单项目标识不匹配。', payload={'code': 'invalid_delivery_manifest'})
    if not args.output:
        return manifest
    selected = delivery_selection(manifest, args.project, args.include_shots)
    target = Path(args.output).expanduser().resolve()
    if target.exists():
        raise APIError('交付输出目录已经存在，请指定新的目录。', payload={'code': 'delivery_output_exists'})
    target.mkdir(parents=True, exist_ok=False)
    result = {**manifest, 'download_directory': str(target), 'downloads': [], 'download_failures': [],
              'download_complete': False, 'delivery_manifest': str(target / 'delivery.json')}
    # Persist the server's scope and evidence even if verification or download
    # later fails. No file is replaced and historical movies are never selected.
    atomic_json(target / 'delivery.json', result)
    for artifact in selected:
        destination = target.joinpath(*PurePosixPath(artifact['relative_path']).parts)
        try:
            if not destination.resolve().is_relative_to(target):
                raise APIError('输出路径越出交付目录。', payload={'code': 'invalid_delivery_path'})
            downloaded = client.download(artifact['api_url'], destination,
                                         expected_sha256=artifact['sha256'], expected_size=artifact['size'])
            result['downloads'].append({'relative_path': artifact['relative_path'], 'kind': artifact['kind'],
                                         'version_id': artifact.get('version_id'), **downloaded})
        except (APIError, OSError, ValueError, HTTPException) as exc:
            error = exc.payload if isinstance(exc, APIError) else {'code': 'delivery_download_failed', 'message': '文件下载未完成。'}
            result['download_failures'].append({'relative_path': artifact['relative_path'], **error})
            result['ready_for_delivery'] = False
            atomic_json(target / 'delivery.json', result)
            raise APIError('交付下载未完成；已保存清单和失败记录。',
                           payload={'code': 'delivery_download_incomplete', 'delivery_manifest': result['delivery_manifest'],
                                    'download_failures': result['download_failures']}) from None
    result['download_complete'] = True
    atomic_json(target / 'delivery.json', result)
    return result


def batch_submit(args, client):
    text = sys.stdin.read() if args.json_file == '-' else Path(args.json_file).read_text(encoding='utf-8-sig')
    items = json.loads(text)
    if not isinstance(items, list) or not 1 <= len(items) <= 150:
        raise APIError('批次请求应为 1～150 项 JSON 数组。', payload={'code': 'invalid_batch'})
    seen = set()
    for item in items:
        if (not isinstance(item, dict) or set(item) != {'project_id', 'plan_id'}
                or not isinstance(item.get('project_id'), str)
                or not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', item['project_id'])
                or not isinstance(item.get('plan_id'), str) or not re.fullmatch(r'[a-f0-9]{64}', item['plan_id'])
                or item['project_id'] in seen):
            raise APIError('每项须含唯一 project_id 和有效 plan_id。', payload={'code': 'invalid_batch'})
        seen.add(item['project_id'])
    path = Path(args.context).expanduser().resolve().parent / 'batches' / (args.request_key + '.json')
    checksum = hashlib.sha256(json.dumps(items, sort_keys=True, separators=(',', ':')).encode('utf-8')).hexdigest()
    if path.exists():
        saved = json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(saved, dict) or saved.get('items') != items or saved.get('request_hash') != checksum or saved.get('base_url') != client.base:
            raise APIError('此批次标识已用于其他请求或实例。', payload={'code': 'batch_idempotency_conflict'})
    else:
        saved = {'version': 1, 'batch_key': args.request_key, 'request_hash': checksum, 'base_url': client.base,
                 'items': items, 'results': []}
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with path.open('x', encoding='utf-8') as stream:
                json.dump(saved, stream, ensure_ascii=False, allow_nan=False)
                stream.flush()
                os.fsync(stream.fileno())
        except FileExistsError:
            saved = json.loads(path.read_text(encoding='utf-8'))
            if not isinstance(saved, dict) or saved.get('items') != items or saved.get('request_hash') != checksum or saved.get('base_url') != client.base:
                raise APIError('此批次标识已被另一请求占用。', payload={'code': 'batch_idempotency_conflict'}) from None
    emit({'event': 'batch_saved', 'batch_key': args.request_key, 'receipt': str(path), 'atomic': False})
    results = []
    for item in items:
        key = phase_key(args.request_key, item['project_id'])
        local = read_receipt(args, key) if ledger_path(args, key).exists() else None
        previous_retry = getattr(args, 'explicit_retry', False)
        args.explicit_retry = bool(args.retry_unknown and local and local.get('status') in ('unknown', 'submitted'))
        try:
            value = submit_run(args, client, item['project_id'], item['plan_id'], key=key)
            results.append({**item, 'request_key': key, 'submission_status': 'confirmed', 'result': value})
        except APIError as exc:
            receipt = read_receipt(args, key) if ledger_path(args, key).exists() else {}
            status = 'unknown' if receipt.get('status') in ('unknown', 'submitted') else 'failed'
            results.append({**item, 'request_key': key, 'submission_status': status, 'error': exc.payload})
        finally:
            args.explicit_retry = previous_retry
        saved['results'] = results
        atomic_json(path, saved)
    confirmed = sum(item['submission_status'] == 'confirmed' for item in results)
    unknown = sum(item['submission_status'] == 'unknown' for item in results)
    return {'batch_key': args.request_key, 'receipt': str(path), 'atomic': False, 'results': results,
            'confirmed': confirmed, 'unknown': unknown, 'failed': len(results) - confirmed - unknown,
            'status': 'submitted' if confirmed == len(results) else 'partial_failure'}


def recover_operation(args, client):
    if args.action == 'get':
        local = read_receipt(args, args.key) if ledger_path(args, args.key).exists() else None
        if local is not None:
            if local.get('base_url') != client.base:
                raise APIError('本地请求属于其他实例。', payload={'code': 'instance_mismatch'})
            verify_health(client, local.get('application_root'))
        try:
            remote = client.request('GET', '/api/v2/operations/' + args.key)
        except APIError as exc:
            if exc.http_status != 404 or local is None:
                raise
            summary = {key: local.get(key) for key in ('status', 'method', 'path', 'result', 'error')}
            return {'request_key': args.key, 'server_operation': None, 'local': summary,
                    'receipt': str(ledger_path(args, args.key)),
                    'next_action': 'operation retry uses the saved body; legacy non-idempotent writes cannot be replayed'}
        if local is not None:
            if local.get('base_url') != client.base:
                raise APIError('本地请求属于其他实例。', payload={'code': 'instance_mismatch'})
            if remote.get('status') == 'completed':
                local.update(status='completed', result=remote.get('result'))
                atomic_json(ledger_path(args, args.key), local)
        return {'request_key': args.key, 'server_operation': remote, 'local_status': (local or {}).get('status')}
    local = read_receipt(args, args.key)
    if local.get('base_url') != client.base:
        raise APIError('原请求属于其他实例；请使用对应连接执行恢复。', payload={'code': 'instance_mismatch'})
    if not replay_route_allowed(local['method'], local['path']):
        raise APIError('账本中的接口不属于允许恢复的类型化操作，拒绝发送。',
                       payload={'code': 'operation_route_not_allowed', 'request_key': args.key})
    args.explicit_retry = True
    return mutation(args, client, local['method'], local['path'], local['body'], key=args.key,
                    replayable=local.get('replayable', False))


def execute_task(args, client):
    if args.command == 'deliver':
        return deliver_artifacts(args, client)
    if args.command == 'batch':
        return batch_submit(args, client)
    if args.command == 'project':
        if args.action == 'list':
            return client.request('GET', '/api/projects')
        if args.action == 'get':
            return client.request('GET', '/api/v2/projects/' + args.id)
        if args.action == 'create':
            return mutation(args, client, 'POST', '/api/v2/projects', create_body(body_file(args)))
        if args.action == 'update':
            body = with_revision(client, args.id, body_file(args), args.expected_revision, args=args)
            return mutation(args, client, 'PATCH', '/api/v2/projects/' + args.id, body)
        if args.action == 'validate':
            return mutation(args, client, 'POST', f'/api/v2/projects/{args.id}/validate', {})
        if args.action == 'plan':
            return submit_plan(args, client, args.id, plan_request(args))
        return submit_run(args, client, args.id, args.plan)
    if args.command == 'produce':
        root = args.request_key or uuid.uuid4().hex
        project = mutation(args, client, 'POST', '/api/v2/projects', create_body(body_file(args)), key=root)
        plan = submit_plan(args, client, project['id'], {'action': 'render', 'internal_text': 'forbid'}, key=phase_key(root, 'plan'))
        emit({'event': 'execution_plan', **plan})
        if not plan.get('ready'):
            return {'id': project['id'], 'plan_id': plan['plan_id'], 'status': 'blocked', 'blocked': plan.get('blocked', []),
                    'workflow_key': root}
        result = submit_run(args, client, project['id'], plan['plan_id'], key=phase_key(root, 'run'))
        return {**result, 'plan_id': plan['plan_id'], 'workflow_key': root}
    if args.command == 'shot':
        if args.action == 'update':
            changes = body_file(args)
            body = with_revision(client, args.project, {'shots': [{'uid': args.uid, 'changes': changes}]}, args.expected_revision, args=args)
            return mutation(args, client, 'PATCH', '/api/v2/projects/' + args.project, body)
        root = args.request_key or uuid.uuid4().hex
        expected_plan_revision = args.expected_revision
        if args.seed is not None:
            if not 0 <= args.seed <= 2**63 - 1:
                raise APIError('seed 超出可用范围。', payload={'code': 'invalid_seed'})
            body = with_revision(client, args.project, {'shots': [{'uid': args.uid, 'changes': {'seed': args.seed}}]}, args.expected_revision,
                                 args=args, key=phase_key(root, 'seed'))
            updated = mutation(args, client, 'PATCH', '/api/v2/projects/' + args.project, body, key=phase_key(root, 'seed'))
            expected_plan_revision = updated.get('revision')
        plan = submit_plan(args, client, args.project, {'action': 'render', 'internal_text': 'forbid',
                           'uids': [args.uid], 'regenerate': True}, key=phase_key(root, 'plan'))
        emit({'event': 'execution_plan', **plan})
        if expected_plan_revision and plan.get('revision') != expected_plan_revision:
            raise APIError('镜头计划的项目版本与要求不一致，未提交生成。', payload={'code': 'REVISION_CONFLICT'})
        if not plan.get('ready'):
            return {'id': args.project, 'plan_id': plan['plan_id'], 'status': 'blocked', 'blocked': plan.get('blocked', [])}
        result = submit_run(args, client, args.project, plan['plan_id'], key=root)
        return {**result, 'plan_id': plan['plan_id'], 'preserved_seed': args.seed is None}
    if args.command == 'operation':
        return recover_operation(args, client)
    if args.command == 'config':
        current = client.request('GET', '/api/v2/config')
        if args.action == 'get':
            return current
        changes = body_file(args)
        check_no_credentials(changes)
        expected = current['revision']
        if args.request_key and ledger_path(args, args.request_key).exists():
            old = read_receipt(args, args.request_key)
            if old.get('path') == '/api/v2/config' and old.get('body', {}).get('changes') == changes:
                expected = old['body']['expected_revision']
        return mutation(args, client, 'PATCH', '/api/v2/config', {'expected_revision': expected, 'changes': changes})
    if args.command == 'credential':
        return credential_set(args, client)
    if args.command == 'prompt':
        return client.request('POST', f'/api/v2/projects/{args.project}/shots/{args.shot}/compile', {'sections': body_file(args)})
    if args.command == 'image':
        if args.action == 'list':
            return client.request('GET', '/api/images')
        if args.action == 'get':
            return client.request('GET', '/api/images/' + args.id)
        if args.action == 'input':
            return mutation(args, client, 'POST', '/api/v2/image-inputs', upload_body(args.file))
        value = body_file(args)
        body = value if 'request' in value else {'request': value}
        if not isinstance(body.get('request'), dict):
            raise APIError('图片 request 必须是 JSON 对象。', payload={'code': 'invalid_image_request'})
        body['request'].setdefault('optimize', False)
        body['internal_text'] = 'allowed' if args.allow_internal_text else body.get('internal_text', 'forbid')
        return mutation(args, client, 'POST', '/api/v2/images', body)
    if args.command == 'asset':
        body = {**upload_body(args.file), 'type': args.kind, 'character': args.character}
        return mutation(args, client, 'POST', f'/api/v2/projects/{args.project}/assets', body)
    if args.command == 'environment':
        if args.action == 'speech-plan':
            return client.request('GET', '/api/v2/environment/speech/plan')
        return mutation(args, client, 'POST', '/api/v2/environment/speech/prepare', {'download_confirmation': args.confirmation})
    if args.action in ('resume', 'stop'):
        body = {'expected_revision': args.expected_revision} if args.action == 'resume' else {'immediate': args.immediate}
        return mutation(args, client, 'POST', f'/api/v2/jobs/{args.id}/{args.action}', body)
    if args.action == 'get':
        return get_job(client, args.id)
    if args.action == 'list':
        query = {key: val for key, val in {'project_id': args.project, 'status': args.status,
                                         'limit': args.limit, 'before': args.before}.items() if val is not None}
        return client.request('GET', '/api/jobs/page?' + urlencode(query))
    if args.action == 'events':
        if args.after < 0:
            raise APIError('after 必须为非负整数。', payload={'code': 'invalid_arguments'})
        return client.request('GET', f'/api/jobs/{args.id}/events?' + urlencode({'after': args.after}))
    raise APIError('未知命令。', payload={'code': 'invalid_arguments'})


def main(argv=None):
    try:
        args = parser().parse_args(argv)
        if args.command == "connect":
            emit(connect(args))
            return 0
        if args.command == 'start':
            emit(start_service(args))
            return 0
        client = client_for(args)
        if args.command in ("doctor", "capabilities"):
            value = client.request("GET", "/api/" + args.command)
        elif args.command == 'job' and args.action == 'watch':
            return watch(client, args.project, args.id, args.seconds, args.interval)
        else:
            value = execute_task(args, client)
        if value is None and args.command == 'job':
            emit({'job_id': args.id, 'job_status': 'unknown', 'code': 'job_not_found'})
            return 4
        if isinstance(value, dict) and value.get('status') == 'blocked':
            emit(value)
            return 2
        if (args.command == 'deliver' and args.verify and value.get('ready_for_delivery') is not True
                or args.command == 'batch' and value.get('status') == 'partial_failure'):
            emit(value)
            return 2
        return maybe_watch(args, client, value)
    except (APIError, OSError, ValueError, HTTPException, subprocess.TimeoutExpired) as exc:
        if isinstance(exc, APIError):
            emit(exc.payload)
        else:
            # File and parser exception strings may contain user content: keep errors local and concise.
            emit({"error": "本地文件或数据读取失败。", "code": "local_error", "retried": False})
        return 1


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
