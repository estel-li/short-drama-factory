"""Generate the distributable agent contract from registered request models."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def contract(app):
    from app.version import PROTOCOL_VERSION
    spec = app.openapi()
    paths = {path: value for path, value in spec['paths'].items()
             if path.startswith('/api/v2/') or path.startswith('/api/jobs/')
             or path in ('/api/doctor', '/api/capabilities', '/api/health')}
    schemas, pending = {}, [paths]
    while pending:
        value = pending.pop()
        if isinstance(value, dict):
            reference = value.get('$ref', '')
            if reference.startswith('#/components/schemas/'):
                name = reference.rsplit('/', 1)[-1]
                if name not in schemas:
                    schemas[name] = spec['components']['schemas'][name]
                    pending.append(schemas[name])
            pending.extend(value.values())
        elif isinstance(value, list):
            pending.extend(value)
    return {'openapi': spec['openapi'], 'info': spec['info'], 'x-agent-protocol': PROTOCOL_VERSION,
            'paths': paths, 'components': {'schemas': dict(sorted(schemas.items()))}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--output', type=Path, default=ROOT / 'docs/agent-api-contract.json')
    args = parser.parse_args()
    from app.api import app
    text = json.dumps(contract(app), ensure_ascii=False, indent=2, sort_keys=True) + '\n'
    if args.check:
        if not args.output.is_file() or args.output.read_text(encoding='utf-8') != text:
            parser.exit(1, 'Agent contract is stale. Run tools/generate_agent_contract.py.\n')
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding='utf-8')
    print(json.dumps({'path': str(args.output), 'checked': args.check}))


if __name__ == '__main__':
    main()
