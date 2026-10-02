#!/usr/bin/env python3
"""Sayfadaki bütün filmleri sırayla seslendirir ve 10'arlı gruplar hâlinde dala gönderir.

Kullanım:  python3 seslendirme/hepsi.py <depolar-klasörü> <sessiz-videolar-klasörü> [dal]
  <depolar-klasörü>/<depo>/captions.js   her filmin altyazıları
  <sessiz-videolar-klasörü>/<id>.mp4     seslendirilmemiş videolar
Seslendirilmiş film videos/<id>.mp4'ün yerine yazılır, index.html'deki süre güncellenir.
Biten filmler seslendirme/sureler.json'a yazılır; yarıda kalırsa kaldığı yerden sürer.
Site 1 GB sınırının altında kalsın diye videos/ boyutu izlenir; gidişat sınırı
aşacak gibiyse kalan filmler daha yüksek CRF ile sıkıştırılır.
"""
import json, re, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HERE = ROOT / 'seslendirme'
TR, EN = 'tr-TR-Chirp3-HD-Charon', 'en-US-Chirp3-HD-Charon'
BATCH, JOBS = 10, 2
VIDEO_BUDGET = 900e6   # videos/ için üst sınır; img, sayfa ve diğerleri ~10 MB
TRAILER = '\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>\nClaude-Session: https://claude.ai/code/session_01MraUrKrz7UTGyzuhEKx4sj'

def films():
    js = ("const s=require('fs').readFileSync(process.argv[1],'utf8');"
          "const F=eval(s.match(/const FILMS = (\\[[\\s\\S]*?\\n  \\]);/)[1]);"
          "const B=eval('('+s.match(/const BONUS = (\\{[\\s\\S]*?\\});/)[1]+')');"
          "console.log(JSON.stringify([...F,B].map(f=>({id:f.id,repo:f.repo||f.id,en:!!f.repo}))))")
    return json.loads(subprocess.check_output(['node', '-e', js, str(ROOT / 'index.html')]))

def mmss(sec):
    s = int(round(sec)); return f'{s // 60}:{s % 60:02d}'

def set_dur(fid, sec):
    p = ROOT / 'index.html'; s = p.read_text()
    s2 = re.sub(r"(\{ id: '" + re.escape(fid) + r"',[^}]*?dur: ')[^']*(')", lambda m: m[1] + mmss(sec) + m[2], s, count=1)
    assert s2 != s or f"dur: '{mmss(sec)}'" in s, f'süre bulunamadı: {fid}'
    p.write_text(s2)

def dur(f):
    return float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', str(f)]))

def git(*a):
    subprocess.run(['git', '-C', str(ROOT), *a], check=True)

def push(branch):
    for wait in (0, 2, 4, 8, 16):
        time.sleep(wait)
        if subprocess.run(['git', '-C', str(ROOT), 'push', '-u', 'origin', branch]).returncode == 0: return
    sys.exit('push başarısız')

def main():
    repos, silent = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
    branch = sys.argv[3] if len(sys.argv) > 3 else 'claude/exciting-dirac-wu6z0g'
    done_p = HERE / 'sureler.json'
    done = json.loads(done_p.read_text()) if done_p.exists() else {}
    todo = [f for f in films() if f['id'] not in done]
    crf = 27
    print(f'{len(done)} film hazır, {len(todo)} film kaldı', flush=True)

    def encode(f):
        out = ROOT / 'videos' / f"{f['id']}.mp4"
        subprocess.run([sys.executable, str(HERE / 'birlestir.py'), str(repos / f['repo']), str(silent / f"{f['id']}.mp4"),
                        str(out), '--bekleme', '2', '--crf', str(crf)], check=True)
        return f, dur(out)

    for b in range(0, len(todo), BATCH):
        group = todo[b:b + BATCH]
        for f in group:   # TTS sırayla (kota koruması tts.py'de)
            subprocess.run([sys.executable, str(HERE / 'tts.py'), str(repos / f['repo']), EN if f['en'] else TR], check=True)
        with ThreadPoolExecutor(JOBS) as ex:
            for f, d in ex.map(encode, group):
                done[f['id']] = round(d, 1)
                set_dur(f['id'], d)
        done_p.write_text(json.dumps(done, indent=1, ensure_ascii=False) + '\n')

        size = sum(p.stat().st_size for p in (ROOT / 'videos').glob('*.mp4'))
        voiced = sum((ROOT / 'videos' / f"{i}.mp4").stat().st_size for i in done)
        n_left = len(films()) - len(done)
        projected = voiced + (voiced / len(done)) * n_left
        print(f'videos/ şimdi {size/1e6:.0f} MB · tahmini son hâl {projected/1e6:.0f} MB (CRF {crf})', flush=True)
        if projected > VIDEO_BUDGET and crf < 34:
            crf += 2; print(f'  bütçe için CRF {crf}', flush=True)

        names = ', '.join(f['id'] for f in group)
        git('add', 'videos', 'index.html', 'seslendirme')
        git('commit', '-q', '-m', f'Seslendirme: {len(done)}/{len(done) + n_left} film (Charon, 2 sn bekleme)\n\n{names}{TRAILER}')
        push(branch)
        print(f'→ gönderildi: {len(done)} film', flush=True)

if __name__ == '__main__':
    main()
