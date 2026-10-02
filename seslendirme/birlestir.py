#!/usr/bin/env python3
"""tts.py ile üretilen sesleri filme yerleştirir (ağa çıkmaz, kota harcamaz).

Kullanım:  python3 seslendirme/birlestir.py <film-deposu> <sessiz.mp4> [bekleme-sn]
Her cümle kendi altyazısının başladığı anda başlar. Her cümle bittikten
sonra bir sonraki cümleye kadar en az <bekleme-sn> (varsayılan 1,5 sn)
sessizlik kalır; gerekirse görüntü o bölümün sonunda dondurulur. Böylece
konuşma hızlandırılmaz ve çocuklara her cümleden sonra düşünme payı kalır.
Çıktı: seslendirme/<film>/<film>-sesli.mp4
"""
import json, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PAUSE = 1.5  # her cümleden sonra en az bekleme (sn); 3. argümanla değiştirilebilir

def dur(f):
    return float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', str(f)]))

def main():
    repo, video = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
    film = repo.name
    pause = float(sys.argv[3]) if len(sys.argv) > 3 else PAUSE
    js = f"console.log(JSON.stringify(require({json.dumps(str(repo / 'captions.js'))})))"
    caps = json.loads(subprocess.check_output(['node', '-e', js]))
    d = HERE / film
    (d / 'trim').mkdir(exist_ok=True)
    clips = sorted((d / 'clips').glob('*.wav'))
    assert len(clips) == len(caps), 'ses sayısı altyazı sayısıyla eşleşmiyor; önce tts.py çalıştırın'
    trimmed = []
    for c in clips:   # baştaki ve sondaki sessizliği kırp
        t = d / 'trim' / c.name
        sil = 'silenceremove=start_periods=1:start_threshold=-45dB'
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(c), '-af', f'{sil},areverse,{sil},areverse', str(t)], check=True)
        trimmed.append(t)

    total = dur(video)
    cuts = [0.0] + [c['start'] for c in caps] + [total]   # bölüm sınırları (özgün zaman)
    segs, starts, shift = [], [], 0.0
    for k in range(len(cuts) - 1):
        a, b, ext = cuts[k], cuts[k + 1], 0.0
        if k >= 1:
            i = k - 1
            starts.append(caps[i]['start'] + shift)
            end_needed = caps[i]['start'] + dur(trimmed[i]) + pause
            ext = max(0.0, end_needed - b)
        segs.append((a, b, ext))
        shift += ext

    fc, vlabels = [], []
    for k, (a, b, ext) in enumerate(segs):
        pad = f',tpad=stop_mode=clone:stop_duration={ext:.3f}' if ext > 0 else ''
        fc.append(f'[0:v]trim=start={a}:end={b},setpts=PTS-STARTPTS{pad}[v{k}]')
        vlabels.append(f'[v{k}]')
    fc.append(''.join(vlabels) + f'concat=n={len(segs)}:v=1:a=0[v]')
    alabels = []
    for i, s in enumerate(starts):
        ms = int(round(s * 1000))
        fc.append(f'[{i+1}:a]aformat=sample_rates=48000:channel_layouts=mono,adelay={ms}:all=1[a{i}]')
        alabels.append(f'[a{i}]')
    fc.append(''.join(alabels) + f'amix=inputs={len(alabels)}:normalize=0:duration=longest,apad=whole_dur={total + shift:.3f},atrim=end={total + shift:.3f}[a]')

    out = d / f'{film}-sesli.mp4'
    cmd = ['ffmpeg', '-v', 'error', '-y', '-i', str(video)]
    for t in trimmed: cmd += ['-i', str(t)]
    cmd += ['-filter_complex', ';'.join(fc), '-map', '[v]', '-map', '[a]',
            '-c:v', 'libx264', '-crf', '20', '-preset', 'slow', '-pix_fmt', 'yuv420p',
            '-c:a', 'aac', '-b:a', '128k', '-ac', '1', '-movflags', '+faststart', str(out)]
    subprocess.run(cmd, check=True)

    # yeni zamanlarla altyazı ve sadece-ses dosyası
    def ts(x):
        ms = int(round(x * 1000)); return f'{ms//3600000:02d}:{ms//60000%60:02d}:{ms//1000%60:02d},{ms%1000:03d}'
    srt = []
    for i, c in enumerate(caps):
        s = starts[i]; e = s + max(c['end'] - c['start'], dur(trimmed[i]))
        srt.append(f"{i+1}\n{ts(s)} --> {ts(e)}\n{c['note']}\n")
    (d / f'{film}-seslendirme.srt').write_text('\n'.join(srt))
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(out), '-vn', '-c:a', 'libmp3lame', '-q:a', '3', str(d / f'{film}-seslendirme.mp3')], check=True)
    print(f'✓ {out.name}: {dur(out):.1f} sn (özgün {total:.1f} sn, {shift:.1f} sn dondurma, cümle sonrası en az {pause} sn)')
    for k, (a, b, ext) in enumerate(segs):
        if ext: print(f'   {b:5.1f} sn’de {ext:.1f} sn dondurma')

if __name__ == '__main__':
    main()
