import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from launcher.seed_resources import seed
import uvicorn

if __name__ == '__main__':
    seed()
    uvicorn.run('app.api:app', host='127.0.0.1', port=int(os.environ.get('FACTORY_PORT', '8765')), workers=1, access_log=False)
