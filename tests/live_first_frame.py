"""Opt-in integration check; uses the configured provider and GPU, creates a new project."""
import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.assets import Assets
from app.config import ConfigStore
from app.content import Content
from app.database import Database
from app.jobs import Worker
from app.projects import Projects
from app.schemas import Options
from app.skills import Skills
from app.storage import ROOT, read_json, write_json


def main():
    parser = argparse.ArgumentParser(description='真实首帧验证（会调用 API；--render 会使用 GPU）')
    parser.add_argument('--render', action='store_true')
    args = parser.parse_args()
    config = ConfigStore()
    db = Database(ROOT / 'data/first_frame_live.sqlite3')
    projects = Projects(config, db)
    content = Content(config, Skills(), projects)
    assets = Assets(config, projects)
    options = Options(input_mode='script', execution_mode='auto', duration_rule='count', total_seconds=8,
                      shot_count=2, auto_reference=False, subtitles=False, render_retries=0)
    source = '''标题：同一杯热茶。温暖二维动画，没有对白、没有音乐。只有一个穿黄色毛衣的女孩与一张桌子。
严格两镜，每镜4秒，均为同一书房、同一段连续动作、固定机位、相同光照和相同构图，没有换场或时间跳跃。
第一镜：女孩坐在桌前，向杯子伸出右手，末尾手指刚触碰杯柄；杯子仍在桌面。
第二镜：从上一镜头结束时的完全相同状态接着发生，右手握住杯柄，轻轻提起杯子，停在胸前。
禁止重演伸手动作，禁止换机位、正反打或新构图。让AI分镜人依首帧功能规则判断是否需要接续首帧。'''
    project = projects.create(source, options.model_dump())
    content.outline(project, options, print, lambda: False)
    story = content.storyboard(project, options, print, lambda: False)
    decisions = [{'id':s['id'], 'enabled':s['use_previous_last_frame'], 'reason':s['first_frame_reason']} for s in story['shots']]
    report = {'project_id':project.name, 'ai_decisions':decisions, 'render_requested':args.render}
    write_json(ROOT / 'logs/first_frame_live.json', report)
    print(json.dumps(report, ensure_ascii=False), flush=True)
    if not story['shots'][1]['use_previous_last_frame']:
        raise RuntimeError('本次 AI 没有选中第二镜，不能据此证明首帧渲染；检查真实分镜与 AI 决策。')
    if args.render:
        worker = Worker(db, config, projects, content, assets)
        jid = db.enqueue(project.name, 'render')
        job = db.claim()
        assert job['id'] == jid
        try:
            worker.execute(job)
            db.update(jid, 'done', '首帧真实验证完成')
        except Exception as exc:
            db.update(jid, 'error', str(exc))
            raise
        state = read_json(project/'state.json')
        frame = state['shots']['2']['first_frame']
        graph = read_json(project/'prompts/002.json')
        assert graph['7']['class_type'] == 'MiniMaxH3ImageToVideo'
        assert 'first_frame' in graph['7']['inputs'] and 'last_frame' not in graph['7']['inputs']
        assert frame['source_clip_sha256'] == hashlib.sha256(Path(state['shots']['1']['clip']).read_bytes()).hexdigest()
        import av
        from PIL import Image
        with av.open(state['shots']['1']['clip']) as media:
            last = None
            for last in media.decode(video=0): pass
            expected = last.to_image().tobytes()
        with Image.open(project/frame['file']) as image:
            assert image.tobytes() == expected
        report.update(status=state['status'], first_frame=frame, media=read_json(project/'媒体验收.json'))
        # Resume through the same worker and ensure neither provider nor Comfy submits again.
        from unittest.mock import patch
        import pipeline
        original_api = pipeline.api
        def reject_submit(path, data=None):
            if path == '/prompt': raise AssertionError('续跑不应再次提交 GPU 任务')
            return original_api(path, data)
        with patch.object(content, 'call', side_effect=AssertionError('续跑不应再次调用 LLM')), patch('pipeline.api', side_effect=reject_submit):
            worker.execute(job)
        report['resume_reused_all_clips_and_prompts'] = True
        write_json(ROOT/'logs/first_frame_live.json', report)
        print('LIVE_FIRST_FRAME_PASSED ' + project.name, flush=True)


if __name__ == '__main__':
    main()
