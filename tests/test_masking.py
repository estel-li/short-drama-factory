import tempfile
import unittest
from pathlib import Path

import av
from PIL import Image,ImageDraw
import pipeline

from app.masking import Mask,apply_masks,mask_frame


class MaskingTests(unittest.TestCase):
    def mask(self):
        return {'shot_uid':'s1','start':0,'end':2,'color':'#EEEEEE',
                'keyframes':[{'time':0,'points':[[0,0],[1,0],[1,1],[0,1]]}],
                'protect':[{'keyframes':[
                    {'time':0,'points':[[.1,.2],[.3,.2],[.3,.7],[.1,.7]]},
                    {'time':2,'points':[[.6,.2],[.8,.2],[.8,.7],[.6,.7]]}]}]}

    def test_occlusion_protection_changes_each_frame(self):
        mask=Mask.model_validate(self.mask())
        early=mask_frame(mask,0,160,128);late=mask_frame(mask,1.9,160,128)
        self.assertEqual(early.getpixel((30,50)),0)
        self.assertEqual(late.getpixel((30,50)),255)
        self.assertEqual(late.getpixel((110,50)),0)
        self.assertEqual(early.getpixel((110,50)),255)

    def test_grayscale_video_alphamerge_preserves_moving_foreground(self):
        with tempfile.TemporaryDirectory() as directory:
            folder=Path(directory);raw=folder/'raw.mp4'
            with av.open(str(raw),'w') as movie:
                stream=movie.add_stream('libx264',rate=24);stream.width=160;stream.height=128;stream.pix_fmt='yuv420p'
                for index in range(48):
                    image=Image.new('RGB',(160,128),'white');draw=ImageDraw.Draw(image)
                    draw.rectangle((8,8,145,20),fill='black')
                    x=round((.1+.5*(index/24)/2)*159);draw.rectangle((x,26,x+30,88),fill='red')
                    frame=av.VideoFrame.from_image(image)
                    for packet in stream.encode(frame):movie.mux(packet)
                for packet in stream.encode():movie.mux(packet)
            source=folder/'source.mp4'
            pipeline.ffmpeg(['-i',raw,'-f','lavfi','-i','anullsrc=r=48000:cl=stereo','-c:v','copy','-c:a','aac','-t','2',source])
            result,reports=apply_masks(source,folder/'masked.mp4',[self.mask()],160,128,48,folder/'alpha')
            self.assertEqual(reports[0]['frames'],48)
            with av.open(str(result)) as movie:
                for index,frame in enumerate(movie.decode(video=0)):
                    if index not in (0,45):continue
                    image=frame.to_image();x=round((.1+.5*(index/24)/2)*159)+15
                    red=image.getpixel((x,50));gray=image.getpixel((20,14))
                    self.assertGreater(red[0],red[2]+100)
                    self.assertGreater(gray[0],180,'visible board text must be covered')
            self.assertTrue((folder/'alpha/mask_00.mkv').is_file())


if __name__=='__main__':unittest.main()
