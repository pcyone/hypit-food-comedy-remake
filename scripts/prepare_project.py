#!/usr/bin/env python3
"""Prepare a local copy of the restaurant comedy; no cloud calls or installs."""
import argparse, json, shlex, shutil, subprocess
from pathlib import Path

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output',required=True,type=Path)
    ap.add_argument('--mode',choices=['reuse','new'],default='reuse')
    a=ap.parse_args();dest=a.output.expanduser().resolve()
    skill=Path(__file__).resolve().parent.parent
    if dest.exists() and (not dest.is_dir() or any(dest.iterdir())):
        ap.error('Output must be a new or empty directory; existing work is preserved.')
    if a.mode=='reuse' and not shutil.which('ffmpeg'):
        ap.error('ffmpeg is needed to prepare the silent preview; no software was installed.')
    if a.mode=='reuse' and not (skill/'assets/baseline-v3/final-v3.mp4').is_file():
        ap.error('Reuse mode needs the private baseline-v3 asset pack. Public releases only support --mode new until you add your own assets.')
    dest.mkdir(parents=True,exist_ok=True)
    if any((skill/'assets/reference').iterdir()):
        shutil.copytree(skill/'assets/reference',dest/'assets')
    else:
        (dest/'assets').mkdir()
        (dest/'assets/README.md').write_text(
            '# Project assets\n\n'
            'Add your own character, restaurant, dish, voice, and reference-video files here.\n'
            'The public repository intentionally does not include private demo media.\n')
    (dest/'analysis').mkdir();(dest/'output').mkdir()
    for src in (skill/'assets/project-template').iterdir():
        target=dest/'analysis'/src.name if src.name=='rebuild_voice_v3.py' else dest/src.name
        shutil.copy2(src,target)
    node=Path.home()/'.nvm/versions/node/v22.23.2/bin/node'
    cli=Path.home()/'.nvm/versions/node/v22.23.2/lib/node_modules/@hypit/hypit/bin/hypit.mjs'
    command=(f'exec {shlex.quote(str(node))} {shlex.quote(str(cli))} "$@"'
             if node.is_file() and cli.is_file() else 'exec hypit "$@"')
    (dest/'hypit-local.sh').write_text('#!/bin/sh\n'+command+'\n')
    if a.mode=='reuse':
        for src in (skill/'assets/baseline-v3').iterdir():
            target=dest/('analysis' if src.suffix=='.json' else 'output')/src.name
            shutil.copy2(src,target)
        shutil.copy2(dest/'output/baseline-voice-v3.wav',dest/'output/voice-master.wav')
        subprocess.run(['ffmpeg','-v','error','-i',str(dest/'output/final-v3.mp4'),
                        '-map','0:v:0','-an','-c:v','copy',str(dest/'output/review-picture-silent.mp4')],check=True)
    (dest/'BRIEF.md').write_text(
        '# 催菜加油短剧\n\n顾客女主：歪博云；老板男主：克托炎；菜品：客家酿豆腐；餐厅：assets/restaurant.jpg。\n'
        '原片提供节奏，身份和食物使用用户资料；豆腐仅用原20–27秒。\n'
        '默认13秒720×1280，四遍豆腐加油到片尾，顶部白字阴影无底板。\n'
        f'准备模式：{a.mode}；未提交生成或发生费用。\n'
        '公开仓库不包含私有示例媒体；请先放入自己的角色、餐厅、菜品和参考视频素材。\n'
        'V3为可复用现状，机器检查通过，不等于明确验收逐字口型/主观听感。\n'
        '本轮新资料优先；新收费请求须有本轮范围和预算依据。\n')
    (dest/'PROGRESS.md').write_text('# 进度\n本地素材与源已准备，未运行新生成。\n'+
        ('现有成片output/final-v3.mp4；预览源已就绪。\n' if a.mode=='reuse' else '新作先改写/检查material.svrun，生成后准备预览。\n'))
    print(json.dumps({'project':str(dest),'mode':a.mode,'cloud_requests':0,
                      'video':str(dest/'output/final-v3.mp4') if a.mode=='reuse' else None},ensure_ascii=False))

if __name__=='__main__':main()
