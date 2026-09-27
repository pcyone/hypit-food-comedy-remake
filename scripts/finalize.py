#!/usr/bin/env python3
"""Combine approved picture and one duration-matched voice master; no generation."""
import argparse
import json
import subprocess
import tempfile
from pathlib import Path


def probe(path):
    return json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(path)]))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ['video','voice','captions','output']:
        p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--font',type=Path,default=Path('/System/Library/Fonts/Hiragino Sans GB.ttc'))
    a=p.parse_args()
    if a.output.exists():p.error('Output exists; choose a new version filename.')
    v=probe(a.video); au=probe(a.voice)
    vs=next((s for s in v['streams'] if s['codec_type']=='video'),None)
    aud=[s for s in au['streams'] if s['codec_type']=='audio']
    if not vs or len(aud)!=1:p.error('Need a video and a voice file with exactly one audio stream.')
    duration=float(v['format']['duration']); ad=float(au['format']['duration'])
    if abs(duration-ad)>.05:p.error(f'Duration mismatch: picture={duration}, voice={ad}; prepare exact master first.')
    cues=json.loads(a.captions.read_text())
    if isinstance(cues,dict):cues=cues['cues']
    prev=0
    for text,start,end in cues:
        if not isinstance(text,str) or not text or not 0<=start<end<=duration or start<prev:
            p.error('Captions must be ordered, nonoverlapping, inside duration, with nonempty text.')
        prev=end
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='restaurant-final-') as td:
        td=Path(td)
        silent=td/'picture.mp4'
        subprocess.run(['ffmpeg','-y','-v','error','-i',str(a.video),'-map','0:v:0','-an','-c:v','copy',str(silent)],check=True)
        if any(s['codec_type']=='audio' for s in probe(silent)['streams']):raise RuntimeError('Picture must be silent')
        cmd=['ffmpeg','-v','error','-i',str(silent),'-i',str(a.voice)]
        filters=[];last='0:v'
        if cues:
            from PIL import Image,ImageDraw,ImageFont,ImageFilter
            w,h=vs['width'],vs['height'];size=round(w*44/720)
            if not a.font.is_file():p.error('Chinese font missing; supply --font.')
            for i,(text,start,end) in enumerate(cues):
                font=ImageFont.truetype(str(a.font),size)
                while font.getlength(text)>w*.90 and font.size>18:
                    font=ImageFont.truetype(str(a.font),font.size-1)
                if font.getlength(text)>w*.90:p.error('Caption too long; split into readable phrases.')
                im=Image.new('RGBA',(w,h));d=ImageDraw.Draw(im)
                box=d.textbbox((0,0),text,font=font);x=(w-(box[2]-box[0]))/2;y=h*.075-box[1]
                shadow=Image.new('RGBA',(w,h))
                ImageDraw.Draw(shadow).text((x+2,y+3),text,font=font,fill=(0,0,0,210),stroke_width=1)
                im=Image.alpha_composite(im,shadow.filter(ImageFilter.GaussianBlur(2)))
                ImageDraw.Draw(im).text((x,y),text,font=font,fill='white')
                path=td/f'{i}.png';im.save(path);cmd+=['-loop','1','-i',str(path)]
                out=f'c{i}';filters.append(f"[{last}][{i+2}:v]overlay=enable='gte(t,{start})*lt(t,{end})':shortest=1:eof_action=repeat[{out}]");last=out
        if filters:cmd+=['-filter_complex',';'.join(filters),'-map',f'[{last}]','-c:v','libx264','-crf','18','-preset','fast','-pix_fmt','yuv420p']
        else:cmd+=['-map','0:v:0','-c:v','copy']
        temp=td/'final.mp4'
        cmd+=['-map','1:a:0','-c:a','aac','-b:a','192k','-t',str(duration),'-movflags','+faststart',str(temp)]
        subprocess.run(cmd,check=True)
        info=probe(temp)
        if sum(s['codec_type']=='audio' for s in info['streams'])!=1:raise RuntimeError('Expected one audio stream')
        if abs(float(info['format']['duration'])-duration)>.05:raise RuntimeError('Output duration mismatch')
        subprocess.run(['ffmpeg','-v','error','-i',str(temp),'-f','null','-'],check=True)
        # Copy after verification; temporary folder may be on another filesystem.
        import shutil
        shutil.copyfile(temp,a.output)
        print(json.dumps({'output':str(a.output.resolve()),'duration':duration,'audio_streams':1,'decode':'passed'},ensure_ascii=False))

if __name__=='__main__':main()
