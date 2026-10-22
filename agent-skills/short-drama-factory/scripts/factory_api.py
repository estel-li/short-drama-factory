#!/usr/bin/env python3
"""Stdlib client for Short Drama Factory's loopback API. No write retries.

Exit: 0 success/done, 1 request failure, 2 review/paused/error,
3 still active, 4 unknown task. Watching never cancels or restarts a job.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
from http.client import HTTPException
import json
import math
import os
from pathlib import Path
import re
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener


class APIError(RuntimeError):
    """A safe machine-readable error; raw HTTP bodies are never exposed."""

    def __init__(self, message, *, http_status=None, payload=None):
        super().__init__(message)
        self.http_status = http_status
        self.payload = {"error": message, "message": message, "retried": False}
        if http_status is not None:
            self.payload["http_status"] = http_status
        if payload:
            self.payload.update(payload)


def safe_server_error(value):
    """Accept our explicit error contract, never FastAPI's input/ctx/detail."""
    if not isinstance(value, dict):
        return {}
    code, message = value.get("code"), value.get("message")
    if (not isinstance(code, str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,100}", code)
            or not isinstance(message, str)):
        return {}
    result = {"code": code, "message": message[:4000], "error": message[:4000]}
    for name in ("field", "uid"):
        if isinstance(value.get(name), str):
            result[name] = value[name][:500]
    if type(value.get("retryable")) is bool:
        result["retryable"] = value["retryable"]
    if isinstance(value.get("next_actions"), list):
        result["next_actions"] = [v[:1000] for v in value["next_actions"][:30] if isinstance(v, str)]
    if isinstance(value.get("details"), list):
        result["details"] = [{k: row[k][:1000] for k in ("field", "type", "message")
                              if isinstance(row.get(k), str)}
                             for row in value["details"][:100] if isinstance(row, dict)]
    return result


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class Client:
    def __init__(self, base_url="http://127.0.0.1:8765", timeout=30):
        parsed = urlsplit(base_url)
        if (parsed.scheme not in ("http", "https")
                or parsed.hostname not in ("localhost", "127.0.0.1", "::1")
                or parsed.username or parsed.password or parsed.query or parsed.fragment
                or parsed.path not in ("", "/")):
            raise APIError("使用本机工作台地址，例如 http://127.0.0.1:8765；不要填 ComfyUI 地址。")
        if not math.isfinite(timeout) or timeout <= 0:
            raise APIError("请求超时必须为正数。")
        self.base = base_url.rstrip("/")
        self.timeout = timeout
        self.opener = build_opener(ProxyHandler({}), NoRedirect())

    def url(self, path):
        parsed = urlsplit(path)
        if (parsed.scheme or parsed.netloc or parsed.fragment
                or not (parsed.path.startswith(("/api/", "/media/")) or parsed.path == "/openapi.json")):
            raise APIError("使用 /api/... 或 /media/... 相对接口路径，不接受外部 URL。")
        return self.base + quote(path, safe="/%?=&:+,~@")

    def open(self, method, path, body=None, timeout=None, headers=None):
        payload = None if body is None else json.dumps(body, ensure_ascii=False, allow_nan=False).encode("utf-8")
        if payload is not None and len(payload) > 12_000_000:
            raise APIError("JSON 请求超过工作台 12MB 上限。")
        request_headers = {"Content-Type": "application/json", "Accept": "application/json"}
        for name, value in (headers or {}).items():
            if not isinstance(name, str) or not isinstance(value, str) or any(c in name + value for c in "\r\n"):
                raise APIError("请求头必须是没有换行的字符串。")
            request_headers[name] = value
        request = Request(self.url(path), data=payload, method=method, headers=request_headers)
        try:
            return self.opener.open(request, timeout=timeout or self.timeout)
        except HTTPError as exc:
            code = exc.code
            safe = {}
            try:
                raw = exc.read(65537)
                if len(raw) <= 65536 and "application/json" in exc.headers.get("Content-Type", ""):
                    safe = safe_server_error(json.loads(raw))
            except (OSError, HTTPException, ValueError):
                pass
            finally:
                exc.close()
            message = safe.get("message", f"HTTP {code}，接口未提供结构化错误；未自动重试。")
            raise APIError(message, http_status=code, payload=safe) from None
        except (URLError, TimeoutError, OSError, HTTPException) as exc:
            detail = "写请求结果未知；先查询项目与任务，勿直接重发。" if method != "GET" else "查询失败，不代表后台任务停止。"
            raise APIError(f"无法连接或请求超时。{detail}") from exc

    def request(self, method, path, body=None, timeout=None, headers=None):
        try:
            with self.open(method, path, body, timeout, headers=headers) as response:
                if "application/json" not in response.headers.get("Content-Type", ""):
                    raise APIError("接口未返回 JSON；文件请使用 download 命令。")
                return json.load(response)
        except (OSError, HTTPException, ValueError) as exc:
            detail = "写请求结果未知，查询队列后再决定后续操作。" if method != "GET" else "后台状态未知，请再次查询原任务。"
            raise APIError("响应未完整读取或不是有效 JSON。" + detail) from exc

    def download(self, path, target):
        if not (path.startswith(("/media/", "/api/exports/"))
                or re.fullmatch(r'/api/images/[A-Za-z0-9_-]+/file', path)):
            raise APIError("download 仅用于媒体、项目导出和 /api/images/{id}/file。")
        target = Path(target).resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        created = False
        digest, size = hashlib.sha256(), 0
        try:
            with self.open("GET", path) as response, target.open("xb") as dest:
                created = True
                while block := response.read(1024 * 1024):
                    dest.write(block)
                    digest.update(block)
                    size += len(block)
                length = response.headers.get("Content-Length")
                if not size or (length is not None and size != int(length)):
                    raise APIError("下载不完整，已移除本次不完整文件。")
        except BaseException:
            if created:
                target.unlink(missing_ok=True)
            raise
        return {"path": str(target), "size": size, "sha256": digest.hexdigest()}


def emit(value):
    print(json.dumps(value, ensure_ascii=False, allow_nan=False), flush=True)


def load_body(name):
    text = sys.stdin.read() if name == "-" else Path(name).read_text(encoding="utf-8-sig")
    value = json.loads(text)
    if not isinstance(value, dict):
        raise APIError("请求文件必须是 JSON 对象。")
    return value


def identifier(value):
    if not value or not all(c.isascii() and (c.isalnum() or c in "_-") for c in value):
        raise argparse.ArgumentTypeError("ID 只能包含 ASCII 字母、数字、下划线和连字符。")
    return value


def project_diagnostics(project, jobs, preflight):
    """Describe persisted evidence; never infer a live stall or repair user data."""
    state, story = project.get('state') or {}, project.get('story') or {}
    assets = project.get('assets') or {}
    cast = {c['id'] for c in story.get('characters', [])}
    by_uid, by_id = state.get('shots_by_uid') or {}, state.get('shots') or {}
    rows, issues = [], []
    for shot in story.get('shots', []):
        uid = shot.get('uid')
        # If a UID map is present, do not mix it with stale positional records.
        record = (by_uid.get(uid) if by_uid else by_id.get(str(shot['id']))) or {}
        media = record.get('media') or {}
        timing = (record.get('timings') or {}).get('sampling') or {}
        seconds, count = timing.get('seconds'), media.get('frames')
        valid_seconds = type(seconds) in (int, float) and math.isfinite(seconds) and seconds >= 0
        valid_count = type(count) is int and count > 0
        matching_sample = bool(timing.get('prompt_id')) and timing.get('prompt_id') == record.get('sampling_prompt_id')
        per_frame = (round(seconds / count, 4) if valid_seconds and valid_count
                     and record.get('status') == 'done' and matching_sample else None)
        bindings = shot.get('bindings') or {}
        linked = shot.get('use_previous_last_frame') is True
        counts = {}
        for slot in ('images', 'videos', 'audios', 'first_frame', 'last_frame'):
            raw = bindings.get(slot)
            ids = (raw if isinstance(raw, list) else [raw]) if raw else []
            counts[slot] = len(ids)
            if linked:
                continue  # Previous-frame mode supersedes manual bindings.
            for aid in ids:
                asset = assets.get(aid) if isinstance(aid, str) else None
                if not asset:
                    issues.append({'kind': 'missing_asset', 'uid': uid, 'slot': slot, 'asset_id': aid})
                elif slot == 'images' and asset.get('character') and asset['character'] not in shot.get('characters', []):
                    issues.append({'kind': 'asset_character_not_in_shot', 'uid': uid,
                                   'asset_id': aid, 'character': asset['character'],
                                   'message': '核对素材用途；Ref2VA 身份参考不能绑定未出场角色，场景图不应误标人物。'})
        for cid in shot.get('characters', []):
            if cid not in cast:
                issues.append({'kind': 'undefined_character', 'uid': uid, 'character': cid})
        if not shot.get('prompt'):
            issues.append({'kind': 'missing_prompt', 'uid': uid,
                           'message': 'render 会尝试调用文字模型补齐；外部 AI 路径请先写好。'})
        duration = shot.get('duration', 4)
        planned = math.ceil(duration * 24)
        planned += (5 - planned % 17) % 17
        rows.append({'id': shot['id'], 'uid': uid, 'characters': shot.get('characters', []),
                     'requested_mode': shot.get('mode', 'auto'), 'previous_frame': linked,
                     'manual_binding_counts': counts, 'planned_frames': planned,
                     'record_status': record.get('status'), 'recorded_frames': count if valid_count else None,
                     'recorded_sampling_seconds': seconds if valid_seconds else None,
                     'recorded_seconds_per_frame': per_frame,
                     'changed_since_render': uid in state.get('changed_shots', []),
                     'has_recorded_clip': bool(record.get('clip') or record.get('clip_relative'))})
    relevant = [j for j in jobs if j.get('project_id') == project['id']]
    return {'project_id': project['id'], 'busy': project.get('busy'),
            'project_status': state.get('status'), 'current_stage': state.get('current_stage'),
            'current_shot': state.get('current_shot'), 'final': project.get('final', False),
            'jobs': [{k: j.get(k) for k in ('id', 'status', 'kind', 'message', 'updated_at')} for j in relevant],
            'preflight': preflight, 'issues': issues, 'shots': rows,
            'limits': ['只读诊断，不停止、不修复、不排队。',
                       '耗时来自历史完成记录；除数为同记录的实际媒体帧数，不是新分镜时长。',
                       '缺失或不匹配的记录返回 null；未测当前 GPU 进度，也不判定停摆。',
                       '素材与原片存在性、完整提示词和 GPU 就绪仍需另行核验；jobs 只含最近 100 条。']}


def diagnose(client, project_id):
    project = client.request('GET', f'/api/project/{project_id}')
    jobs = client.request('GET', '/api/jobs')
    preflight = client.request('GET', f'/api/projects/{project_id}/preflight')
    return project_diagnostics(project, jobs, preflight)


def get_job(client, job_id, timeout=None):
    """Read an exact persisted job; old servers alone need the bounded fallback."""
    try:
        return client.request("GET", f"/api/jobs/{job_id}", timeout=timeout)
    except APIError as exc:
        if exc.http_status != 404:
            raise
        # A new API's explicit missing result must not be hidden by a legacy list.
        if exc.payload.get("code") in ("job_not_found", "JOB_NOT_FOUND"):
            return None
        if exc.payload.get("code"):
            raise
        jobs = client.request("GET", "/api/jobs", timeout=timeout)
        return next((job for job in jobs if job.get("id") == job_id), None)


def watch(client, project_id, job_id, seconds=45, interval=5):
    if not (math.isfinite(seconds) and 0 < seconds <= 45 and math.isfinite(interval) and 1 <= interval <= 15):
        raise APIError("seconds 为 0～45 秒（不含 0）；interval 为 1～15 秒。")
    deadline = time.monotonic() + seconds
    while True:
        remaining = max(.1, deadline - time.monotonic())
        job = get_job(client, job_id, timeout=min(client.timeout, remaining))
        remaining = max(.1, deadline - time.monotonic())
        if job and project_id and job.get("project_id") != project_id:
            raise APIError("任务 ID 不属于指定项目。")
        project = client.request("GET", f"/api/project/{project_id}", timeout=min(client.timeout, remaining)) if project_id else {}
        state = project.get("state") or {}
        status = job["status"] if job else "unknown"
        event = {"project_id": project_id or (job or {}).get("project_id"), "job_id": job_id, "job_status": status,
                 "kind": job.get("kind") if job else None,
                 "message": job.get("message", "") if job else "未找到此任务 ID；旧版服务的查询范围可能有限。"}
        for name in ("terminal", "outcome", "next_actions"):
            if job and name in job:
                event[name] = job[name]
        if job and job.get('failure'):
            failure = safe_server_error(job['failure'])
            if failure:
                event['failure'] = failure
        if project_id:
            event.update({
              "busy": project.get("busy"), "project_status": state.get("status"),
              "stage": state.get("current_stage"),
              "final": project.get("final", False), "subtitled": project.get("subtitled", False),
              "completed_shots": sum(s.get("status") == "done" for s in state.get("shots", {}).values()),
              "total_shots": state.get("total_shots")})
        emit(event)
        if status == "done":
            return 0
        if status in ("review", "paused", "error", "failed", "blocked", "cancelled"):
            return 2
        if status not in ("queued", "running"):
            return 4
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return 3
        time.sleep(min(interval, remaining))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=os.environ.get("DRAMA_FACTORY_URL", "http://127.0.0.1:8765"))
    parser.add_argument("--timeout", type=float, default=30)
    sub = parser.add_subparsers(dest="command", required=True)
    get = sub.add_parser("get", help="读取 JSON 接口")
    get.add_argument("path")
    post = sub.add_parser("post", help="提交一次请求，不重试；默认请求体 {}")
    post.add_argument("path")
    post.add_argument("--json", dest="json_file", help="UTF-8 JSON 文件，- 表示标准输入")
    download = sub.add_parser("download", help="流式下载文件，不覆盖已有文件")
    download.add_argument("path")
    download.add_argument("--output", required=True)
    asset = sub.add_parser("asset", help="上传图片/视频/音频，返回真实素材 ID")
    asset.add_argument("--project", required=True, type=identifier)
    asset.add_argument("--file", required=True)
    asset.add_argument("--kind", choices=("image", "video", "audio"), required=True)
    asset.add_argument("--character", default="")
    diagnostic = sub.add_parser("diagnose", help="只读检查绑定身份、计划帧数和已完成采样耗时")
    diagnostic.add_argument("--project", required=True, type=identifier)
    monitor = sub.add_parser("watch", help="观察确切任务，时间到不会取消或重启任务")
    monitor.add_argument("--project", required=True, type=identifier)
    monitor.add_argument("--job", required=True, type=identifier)
    monitor.add_argument("--seconds", type=float, default=45)
    monitor.add_argument("--interval", type=float, default=5)
    args = parser.parse_args(argv)
    try:
        client = Client(args.base_url, args.timeout)
        if args.command == "watch":
            return watch(client, args.project, args.job, args.seconds, args.interval)
        if args.command == "diagnose":
            result = diagnose(client, args.project)
        elif args.command == "download":
            result = client.download(args.path, args.output)
        elif args.command == "asset":
            path = Path(args.file)
            if path.stat().st_size > 8_000_000:
                raise APIError("素材超过 8MB，请先缩小或截短。")
            body = {"type": args.kind, "name": path.name, "character": args.character,
                    "data": base64.b64encode(path.read_bytes()).decode("ascii")}
            result = client.request("POST", f"/api/projects/{args.project}/assets", body)
        else:
            body = load_body(args.json_file) if args.command == "post" and args.json_file else {}
            result = client.request(args.command.upper(), args.path, body if args.command == "post" else None)
        emit(result)
        return 0
    except (APIError, OSError, ValueError, HTTPException) as exc:
        message = f"JSON 格式错误：第 {exc.lineno} 行，第 {exc.colno} 列。" if isinstance(exc, json.JSONDecodeError) else str(exc)
        emit(exc.payload if isinstance(exc, APIError) else {"error": message, "retried": False})
        return 1


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
