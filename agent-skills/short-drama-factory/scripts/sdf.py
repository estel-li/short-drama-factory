#!/usr/bin/env python3
"""Short Drama Factory task CLI. Stdlib only; all output and failures are JSON.

Copy this script together with factory_api.py to use it outside the application.
Connecting and diagnosis never start a service, resume a queue, or generate media.
"""
from __future__ import annotations

import argparse
from http.client import HTTPException
import json
import os
from pathlib import Path
import sys
from urllib.parse import urlencode

from factory_api import APIError, Client, emit, get_job, identifier, watch


CONTEXT_VERSION = 1
SUPPORTED_PROTOCOLS = (1,)
DEFAULT_URL = "http://127.0.0.1:8765"


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise APIError(message, payload={"code": "invalid_arguments", "retryable": False})


def positive_limit(value):
    try:
        number = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError("limit 必须为整数。") from None
    if not 1 <= number <= 200:
        raise argparse.ArgumentTypeError("limit 必须为 1～200。")
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


def parser():
    result = Parser(description=__doc__)
    result.add_argument("--base-url")
    result.add_argument("--timeout", type=float, default=30)
    result.add_argument("--context", default=str(Path.cwd() / ".sdf" / "connection.json"))
    commands = result.add_subparsers(dest="command", required=True)
    connection = commands.add_parser("connect", help="绑定并核对已经运行的本地实例")
    connection.add_argument("--app", required=True)
    connection.add_argument("--url")
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
    return result


def main(argv=None):
    try:
        args = parser().parse_args(argv)
        if args.command == "connect":
            emit(connect(args))
            return 0
        client = client_for(args)
        if args.command in ("doctor", "capabilities"):
            value = client.request("GET", "/api/" + args.command)
        elif args.action == "get":
            value = get_job(client, args.id)
            if value is None:
                emit({"job_id": args.id, "job_status": "unknown", "code": "job_not_found"})
                return 4
        elif args.action == "list":
            query = {key: val for key, val in {"project_id": args.project, "status": args.status,
                                             "limit": args.limit, "before": args.before}.items() if val is not None}
            value = client.request("GET", "/api/jobs/page?" + urlencode(query))
        elif args.action == "events":
            if args.after < 0:
                raise APIError("after 必须为非负整数。", payload={"code": "invalid_arguments"})
            value = client.request("GET", f"/api/jobs/{args.id}/events?" + urlencode({"after": args.after}))
        else:
            return watch(client, args.project, args.id, args.seconds, args.interval)
        emit(value)
        return 0
    except (APIError, OSError, ValueError, HTTPException) as exc:
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
