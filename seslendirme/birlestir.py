#!/usr/bin/env python3
"""tts.py ile üretilen sesleri filme yerleştirir (ağa çıkmaz, kota harcamaz).

Kullanım:  python3 seslendirme/birlestir.py <film-deposu> <sessiz.mp4> <çıktı.mp4> [--bekleme 2] [--crf 30]
Her cümle kendi altyazısının başladığı anda başlar. Her cümle bittikten
sonra bir sonraki cümleye kadar en az --bekleme sn sessizlik kalır;
gerekirse görüntü o bölümün sonunda dondurulur. Konuşma hızlandırılmaz,
çocuklara her cümleden sonra düşünme payı kalır.
Ayrıca seslendirme/<film>/<film>-seslendirme.srt (anlatım metni) yazılır.
"""
import argparse, json, subprocess, tempfile
from pathlib import Path
from tts import HERE, clip_path, load_captions

def dur(f):
    return float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', str(f)]))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('repo'); ap.add_argument('video'); ap.add_argument('out')
    ap.add_argument('--bekleme', type=float, default=2.0, help='her cümleden sonra en az bekleme (sn)')
    ap.add_argument('--crf', type=int, default=30, help='x264 kalite (büyük = küçük dosya)')
    a = ap.parse_args()
    repo, video, out = Path(a.repo).resolve(), Path(a.video).resolve(), Path(a.out).resolve()
    film = repo.name
    caps = load_captions(repo)
    voice = (HERE / film / 'ses.txt').read_text().strip()   # tts.py'nin kullandığı ses
    clips = [clip_path(film, voice, i, c['note']) for i, c in enumerate(caps)]
    missing = [c.name for c in clips if not c.exists()]
    assert not missing, f'eksik ses: {missing}; önce tts.py çalıştırın'

    tmp = Path(tempfile.mkdtemp())
    trimmed = []
    for c in clips:   # baştaki ve sondaki sessizliği kırp
        t = tmp / c.name
        sil = 'silenceremove=start_periods=1:start_threshold=-45dB'
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(c), '-af', f'{sil},areverse,{sil},areverse', str(t)], check=True)
        trimmed.append(t)
    lens = [dur(t) for t in trimmed]

    total = dur(video)
    cuts = [0.0] + [c['start'] for c in caps] + [total]   # bölüm sınırları (özgün zaman)
    segs, starts, shift = [], [], 0.0
    for k in range(len(cuts) - 1):
        a0, b, ext = cuts[k], cuts[k + 1], 0.0
        if k >= 1:
            i = k - 1
            starts.append(caps[i]['start'] + shift)
            ext = max(0.0, caps[i]['start'] + lens[i] + a.bekleme - b)
        segs.append((a0, b, ext))
        shift += ext
    length = total + shift

    fc, vl = [], ''
    for k, (a0, b, ext) in enumerate(segs):
        pad = f',tpad=stop_mode=clone:stop_duration={ext:.3f}' if ext > 0 else ''
        fc.append(f'[0:v]trim=start={a0}:end={b},setpts=PTS-STARTPTS{pad}[v{k}]')
        vl += f'[v{k}]'
    fc.append(f'{vl}concat=n={len(segs)}:v=1:a=0[v]')
    al = ''
    for i, s in enumerate(starts):
        fc.append(f'[{i+1}:a]aformat=sample_rates=48000:channel_layouts=mono,adelay={int(round(s * 1000))}:all=1[a{i}]')
        al += f'[a{i}]'
    fc.append(f'{al}amix=inputs={len(starts)}:normalize=0:duration=longest,alimiter=limit=0.89:level=0,'
              f'apad=whole_dur={length:.3f},atrim=end={length:.3f}[a]')

    cmd = ['ffmpeg', '-v', 'error', '-y', '-i', str(video)]
    for t in trimmed: cmd += ['-i', str(t)]
    cmd += ['-filter_complex', ';'.join(fc), '-map', '[v]', '-map', '[a]',
            '-c:v', 'libx264', '-crf', str(a.crf), '-preset', 'veryslow', '-tune', 'animation', '-pix_fmt', 'yuv420p',
            '-c:a', 'aac', '-b:a', '64k', '-ac', '1', '-movflags', '+faststart', str(out)]
    subprocess.run(cmd, check=True)
    for t in trimmed: t.unlink()
    tmp.rmdir()

    def ts(x):
        ms = int(round(x * 1000)); return f'{ms//3600000:02d}:{ms//60000%60:02d}:{ms//1000%60:02d},{ms%1000:03d}'
    srt = [f"{i+1}\n{ts(s)} --> {ts(s + max(c['end'] - c['start'], lens[i]))}\n{c['note']}\n" for i, (c, s) in enumerate(zip(caps, starts))]
    (HERE / film / f'{film}-seslendirme.srt').write_text('\n'.join(srt))
    print(f'✓ {film} [{voice}]: {total:.1f} → {dur(out):.1f} sn, {out.stat().st_size / 1e6:.1f} MB')

if __name__ == '__main__':
    main()
