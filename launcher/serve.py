import os
import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from launcher.seed_resources import seed
import uvicorn

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='运行短剧工厂 API 服务')
    parser.add_argument('--serve-only', action='store_true', help='不恢复或领取旧任务')
    parser.add_argument('--port', type=int, default=int(os.environ.get('FACTORY_PORT', '8765')))
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error('端口必须在 1～65535 之间。')
    if args.serve_only:
        os.environ['FACTORY_SERVE_ONLY'] = '1'
    seed()
    uvicorn.run('app.api:app', host='127.0.0.1', port=args.port, workers=1, access_log=False)
