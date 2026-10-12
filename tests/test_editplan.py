import unittest

import numpy as np

from app.editplan import align_captions, edit_plan, map_time
from app.speech import analyze_audio, intervals, rms_diagnostics


class EditPlanTests(unittest.TestCase):
    def test_quieter_voice_protected_and_frame_mapping_is_exact(self):
        speech={'speech_intervals':[[2,3],[5,6]],'relaxed_speech_intervals':[[1.85,3.15],[4.85,6.15]],'safe_for_auto_edit':True}
        shot={'dialogue':[{'text':'第一句。'},{'text':'第二句。'}]}
        plan=edit_plan(shot,192,speech,'compact')
        self.assertLess(plan['output_frames'],192)
        self.assertTrue(plan['detected_speech_covered'])
        for a,b in plan['protected_frames']:
            self.assertAlmostEqual(map_time(b/24,plan['keep_frames'])-map_time(a/24,plan['keep_frames']),(b-a)/24)
        lines=align_captions(shot,speech,plan['keep_frames'],8)
        self.assertEqual(lines[0]['source_start'],2)
        self.assertEqual(lines[1]['source_start'],5)
        self.assertEqual(lines[-1]['source_end'],6)
        self.assertLessEqual(lines[-1]['end'],plan['output_frames']/24)

    def test_no_voice_action_and_i2va_boundaries_preserve_performance(self):
        speech={'speech_intervals':[[2,3]],'relaxed_speech_intervals':[[1.9,3.1]],'safe_for_auto_edit':True}
        shot={'dialogue':[{'text':'你好'}]}
        for value in ({}, {'dialogue':[]},{**shot,'preserve_performance':True}):
            self.assertEqual(edit_plan(value,192,speech,'compact')['keep_frames'],[[0,192]])
        self.assertEqual(edit_plan(shot,192,{'safe_for_auto_edit':False},'compact')['keep_frames'],[[0,192]])
        plan=edit_plan(shot,192,speech,'compact',preserve_start=True,preserve_end=True)
        self.assertEqual(plan['keep_frames'],[[0,192]])

    def test_manual_alignment_is_authoritative_and_validated(self):
        shot={'dialogue':[{'text':'甲'},{'text':'乙'}],'dialogue_timings':[{'start':2,'end':3},{'start':5,'end':6}]}
        plan=edit_plan(shot,192,{},'compact')
        lines=align_captions(shot,{},plan['keep_frames'],8)
        self.assertTrue(all(line['alignment']=='manual' for line in lines))
        shot['dialogue_timings'][1]['start']=2.5
        with self.assertRaises(ValueError):align_captions(shot,{},[[0,192]],8)

    def test_energy_is_diagnosed_separately_from_speech(self):
        sr=16000;duration=6;time=np.arange(sr*duration)/sr
        sample=.01*np.sin(2*np.pi*200*time)
        sample[sr:2*sr]+=.10*np.sin(2*np.pi*440*time[sr:2*sr])
        data=rms_diagnostics(sample,duration)
        self.assertGreater(data['noise_floor'],.005)
        self.assertLess(data['strict_activity_density'],.3)
        self.assertGreater(data['strict_activity_density'],.1)
        fallback=analyze_audio(sample,duration)
        self.assertFalse(fallback['safe_for_auto_edit'])
        self.assertIsNone(fallback['speech_density'])
        self.assertEqual(intervals([0]*100,.032,3.2),[])
        self.assertEqual(intervals([1]*100,.032,3.2),[[0,3.2]])


if __name__=='__main__':unittest.main()
