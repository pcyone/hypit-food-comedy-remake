from pathlib import Path
import array, json, math, subprocess, wave

root=Path(__file__).resolve().parent.parent
source_dir=root/'output';out=source_dir/'rebuilt-v3';sr=48000
for source in ['baseline-voice-v3.wav','cheer-v3-a.wav','cheer-v3-b.wav']:
    if not (source_dir/source).is_file():raise FileNotFoundError(source_dir/source)
cues_path=root/'analysis/cues-v3.json'
if not cues_path.is_file():raise FileNotFoundError(cues_path)
# A fresh output directory preserves the approved baseline and prior rebuilds.
out.mkdir(exist_ok=False)
def run(args):subprocess.run(['ffmpeg','-y','-v','error',*args],cwd=root,check=True)
def read(path):
    with wave.open(str(path),'rb') as w:
        assert (w.getframerate(),w.getnchannels(),w.getsampwidth())==(sr,1,2)
        a=array.array('h');a.frombytes(w.readframes(w.getnframes()));return a
def save(path,samples):
    with wave.open(str(path),'wb') as w:
        w.setnchannels(1);w.setsampwidth(2);w.setframerate(sr);w.writeframes(samples.tobytes())

old=read(source_dir/'baseline-voice-v3.wav')
master=array.array('h',[0])*(13*sr);keep=round(8.3*sr)
master[:keep]=old[:keep]
tail=array.array('h',[0])*(len(master)-keep)
# Four distinct newly performed WHOLE phrases. No word-by-word assembly.
# Only a mild pitch-preserving tempo change fits the source comedy's beat.
slots=[
    ('a',.150,.875,8.420,.85),
    ('a',1.064,1.785,9.660,.85),
    ('b',.185,.957,10.940,.85),
    ('b',1.235,2.105,12.030,.90),
]
actual=[];previous_end=8.3
for i,(source,a,b,start,tempo) in enumerate(slots,1):
    path=out/f'cheer-v3-phrase-{i}.wav'
    fil=f'atrim=start={a}:end={b},asetpts=PTS-STARTPTS,atempo={tempo},aresample=48000,asetpts=N/SR/TB'
    run(['-i',str(source_dir/f'cheer-v3-{source}.wav'),'-af',fil,'-ar',str(sr),'-ac','1','-c:a','pcm_s16le',str(path)])
    clip=read(path)
    # Fades stay inside the retained quiet consonant/tail margins.
    fin=round(.003*sr);fout=round(.008*sr)
    for k in range(fin):clip[k]=round(clip[k]*k/fin)
    for k in range(fout):clip[-1-k]=round(clip[-1-k]*k/fout)
    index=round((start-8.3)*sr);end=start+len(clip)/sr
    assert start>=previous_end and index+len(clip)<=len(tail),(i,start,end)
    tail[index:index+len(clip)]=clip;previous_end=end
    actual.append(dict(phrase=i,source=source,source_start=a,source_end=b,start=start,end=end,tempo=tempo))
save(out/'cheer-v3-arranged.wav',tail)
run(['-i',str(out/'cheer-v3-arranged.wav'),'-af','highpass=f=65,loudnorm=I=-13.8:TP=-1.3:LRA=8,aresample=48000,asetpts=N/SR/TB','-ar',str(sr),'-ac','1','-c:a','pcm_s16le',str(out/'cheer-v3-master-tail.wav')])
tail=read(out/'cheer-v3-master-tail.wav')
assert len(tail)==len(master)-keep
master[keep:]=tail
assert master[:keep]==old[:keep]
save(out/'voice-master.wav',master)
cues=json.loads(cues_path.read_text())[:6]
cues += [['豆腐，加油！',x['start'],min(13,x['end']+.02)] for x in actual]
(out/'cues-v3.json').write_text(json.dumps(cues,ensure_ascii=False,indent=2))

# User-reported regression: the final second must have real speech energy.
blocks=[]
for k in range(11*sr,len(master),480):
    v=master[k:k+480];rms=math.sqrt(sum(x*x for x in v)/len(v))/32768
    db=20*math.log10(max(rms,1e-9));blocks.append((k/sr,db))
last_active=max(t+.01 for t,db in blocks if db>-40)
last_second_active=sum(.01 for t,db in blocks if t>=12 and db>-40)
assert last_active>=12.90,('ending_silence',last_active)
assert last_second_active>=.55,('missing_final_chant',last_second_active)
report={'version':'V3','duration':13,'chant_count':4,'unchanged_prefix_seconds':8.3,
 'prefix_pcm_identical':True,'original_generated_audio_mixed':False,
 'phrases':actual,'last_audible_frame_end':last_active,
 'voiced_seconds_in_final_second':last_second_active,
 'voice_build':'private-baseline',
 'scope':'New energetic voice performances and timing; no regenerated video or phoneme-level face editing.'}
(out/'cheer-v3-timing.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps(report,ensure_ascii=False))
