import copy
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import av
import pipeline

from app.finishing import build, collect_clips, concatenate, ffmpeg, versions
from app.quality import render_contract
from app.storage import read_json, write_json


class FinishingTests(unittest.TestCase):
    def video(self,path,color='red',frames=192):
        pipeline.ffmpeg(['-f','lavfi','-i',f'color=c={color}:s=160x256:r=24',
                         '-f','lavfi','-i',r'aevalsrc=if(between(t\,2\,3)\,0.3*sin(2*PI*440*t)\,0.01*sin(2*PI*170*t)):s=48000',
                         '-c:v','libx264','-bf','0','-c:a','aac','-frames:v',frames,'-t',frames/24,path])

    def color(self,path):
        with av.open(str(path)) as media:
            frame=next(media.decode(video=0)).to_image()
            return frame.getpixel((2,2))

    def test_zero_render_edit_rebuild_and_fresh_subtitle_input(self):
        with tempfile.TemporaryDirectory() as folder:
            project=Path(folder);source=project/'clip.mp4';self.video(source)
            self.video(project/'成片.mp4','blue')
            original=(hashlib.sha256(source.read_bytes()).hexdigest(),source.stat().st_mtime_ns)
            story={'title':'test','shots':[{'id':1,'uid':'s1','duration':8,'dialogue':[{'text':'你好。'}]}]}
            speech={'method':'fixture','speech_intervals':[[2,3]],'relaxed_speech_intervals':[[1.9,3.1]],'safe_for_auto_edit':True,'speech_density':.125,'energy':{}}
            settings={'edit_preset':'compact','subtitle_alignment':'speech','subtitles':True,'notes':[{'start':.4,'end':1.2,'text':'说明文字'}]}
            with patch('app.finishing.ensure_model',return_value=None),patch('app.finishing.analyze_audio',return_value=speech):
                result=build(project,story,[source],160,256,settings)
            report=read_json(project/'媒体验收.json')
            self.assertLess(report['expected_frames'],192)
            self.assertEqual(report['detected_speech_cut_count'],0)
            self.assertGreater(report['edited_speech_density'],report['original_speech_density'])
            red=self.color(project/'成片_字幕版.mp4');self.assertGreater(red[0],red[2],'subtitle render must use current red source, not the previous blue root film')
            self.assertEqual(original,(hashlib.sha256(source.read_bytes()).hexdigest(),source.stat().st_mtime_ns))
            self.assertIn('PlayResX: 160',(project/'字幕.ass').read_text(encoding='utf-8'))
            self.assertIn('\\pos',(project/'字幕.ass').read_text(encoding='utf-8'))
            edit=read_json(project/'current_edit.json')['id'];recipe=read_json(project/'edits'/edit/'recipe.json')
            self.video(source,'blue')
            with patch('app.finishing.ensure_model',side_effect=AssertionError('rebuild must reuse frozen speech detection')):
                build(project,story,[],160,256,settings,recipe=recipe)
            self.assertEqual(read_json(project/'媒体验收.json')['expected_frames'],report['expected_frames'])
            red=self.color(result);self.assertGreater(red[0],red[2],'rebuild must use immutable original snapshots')
            self.assertEqual(len(versions(project)),2)
            self.assertTrue(list((project/'takes').glob('final_*/成片.mp4')))

    def test_changed_dialogue_requires_native_rerender(self):
        with tempfile.TemporaryDirectory() as folder:
            project=Path(folder);source=project/'clip.mp4';self.video(source)
            story={'characters':[],'shots':[{'id':1,'uid':'s1','prompt':'same','dialogue':[{'text':'原话'}]}]}
            write_json(project/'state.json',{'shots_by_uid':{'s1':{'status':'done','clip':str(source),'render_contract':render_contract(story,story['shots'][0])}}})
            self.assertEqual(collect_clips(project,story),[source])
            altered=copy.deepcopy(story);altered['shots'][0]['dialogue'][0]['text']='新话'
            with self.assertRaisesRegex(ValueError,'必须重生成'):collect_clips(project,altered)

    def test_filter_conflict_is_caught_before_ffmpeg(self):
        with self.assertRaisesRegex(ValueError,'不能同时使用'):ffmpeg(['-filter_complex','[0:a]volume=1[a]','-af','volume=.5'])

    def test_multi_clip_audio_does_not_accumulate_aac_padding(self):
        import numpy as np
        from app.speech import pcm_audio
        with tempfile.TemporaryDirectory() as directory:
            folder=Path(directory);source=folder/'clip.mp4';self.video(source,frames=107)
            duration=107/24
            checks=[{'edited':{'frames':107}}]*3
            output=folder/'joined.mp4'
            concatenate(folder,[source]*3,checks,output)
            self.assertEqual(pipeline.media_info(output,True)['frames'],321)
            original=pcm_audio(source,duration);joined=pcm_audio(output,duration*3)
            x=original[32000:48000]
            for i in range(3):
                start=round((i*duration+2)*16000)
                y=joined[start:start+len(x)]
                correlation=float(np.dot(x,y)/(np.linalg.norm(x)*np.linalg.norm(y)))
                self.assertGreater(correlation,.97,'AAC encoder padding must not shift dialogue at each cut')

    def test_legacy_quoted_dialogue_requires_matching_render_record(self):
        with tempfile.TemporaryDirectory() as directory:
            project=Path(directory);source=project/'clip.mp4';self.video(source)
            prompt='integrated_multimodal_description: [Shot 1] girl\noverall_soundscape: rain\ndiegetic dialogue: girl: "原句"\nnon_diegetic_music: None'
            story={'shots':[{'id':1,'uid':'s1','prompt':prompt,'dialogue':[{'text':'原句'}]}]}
            write_json(project/'state.json',{'shots':{'1':{'status':'done','clip':str(source)}}})
            write_json(project/'prompts/001.json',{'7':{'class_type':'MiniMaxH3ImageToVideo','inputs':{'prompt':prompt}}})
            self.assertEqual(collect_clips(project,story),[source])
            story['shots'][0]['dialogue'][0]['text']='改词'
            with self.assertRaises(ValueError):collect_clips(project,story)


if __name__=='__main__':unittest.main()
