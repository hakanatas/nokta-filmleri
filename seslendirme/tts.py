#!/usr/bin/env python3
"""Bir filmin seslendirme notlarını Google Cloud TTS ile seslendirir.

Kullanım:  python3 seslendirme/tts.py <film-deposu> [ses-adı]
  <film-deposu>: captions.js içeren klasör (ör. ../ucer-ucer-bolukler)
  ses-adı: varsayılan tr-TR-Chirp3-HD-Charon; dil ses adından alınır (en-US-...).
  GOOGLE_TTS_API_KEY ortam değişkeni gerekir.

Ücretsiz kota koruması: gönderilen her karakter seslendirme/kota.json
dosyasına ay ay yazılır. Seçilen ses türünün aylık ücretsiz sınırının
%90'ına gelinirse betik istek göndermeden durur. Aynı cümle aynı sesle
daha önce seslendirildiyse önbellekten gelir, kotadan düşmez.
Not: bu sayaç yalnızca bu betiklerle yapılan istekleri bilir; aynı Google
projesinde başka TTS kullanımı varsa Cloud Console'dan kontrol edin.
"""
import base64, hashlib, http.client, json, os, subprocess, sys, time, urllib.error, urllib.request
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
VOICE = 'tr-TR-Chirp3-HD-Charon'
# Aylık ücretsiz karakter sınırları (cloud.google.com/text-to-speech/pricing, Ekim 2026)
FREE = {'Chirp3-HD': 1_000_000, 'Neural2': 1_000_000, 'Studio': 1_000_000,
        'Wavenet': 4_000_000, 'Standard': 4_000_000}
SAFETY = 0.90
LEDGER = HERE / 'kota.json'

def tier(voice):
    for k in FREE:
        if f'-{k}-' in voice: return k
    sys.exit(f'Bilinmeyen ses türü: {voice} (ücretsiz kotası olmayan sesler kullanılmaz)')

def load_captions(repo):
    js = f"console.log(JSON.stringify(require({json.dumps(str(Path(repo).resolve() / 'captions.js'))})))"
    caps = json.loads(subprocess.check_output(['node', '-e', js]))
    # seslendirme/<film>/notlar-tr.json varsa notların yerine o (çeviri) okunur
    tr = HERE / Path(repo).resolve().name / 'notlar-tr.json'
    if tr.exists():
        notes = json.loads(tr.read_text())
        assert len(notes) == len(caps), f'{tr}: {len(notes)} not, {len(caps)} altyazı'
        for c, n in zip(caps, notes): c['note'] = n
    # seslendirme/<film>/ek-notlar.json: altyazısı olmayan yerlere eklenen cümleler [{start, end, note}]
    ek = HERE / Path(repo).resolve().name / 'ek-notlar.json'
    if ek.exists():
        caps = sorted(caps + json.loads(ek.read_text()), key=lambda c: c['start'])
    return caps

def clip_path(film, voice, i, note):
    h = hashlib.sha1(f'{voice}|{note}'.encode()).hexdigest()[:10]
    d = HERE / film / 'clips' / voice
    old = sorted(d.glob(f'*-{h}.wav'))   # sıra numarası değişse de aynı cümlenin sesi yeniden kullanılır
    return old[0] if old else d / f'{i+1:02d}-{h}.wav'

def ledger():
    return json.loads(LEDGER.read_text()) if LEDGER.exists() else {}

def synth(text, voice, key):
    body = {'input': {'text': text}, 'voice': {'languageCode': voice[:5], 'name': voice},
            'audioConfig': {'audioEncoding': 'LINEAR16', 'sampleRateHertz': 48000}}
    for attempt in range(6):
        req = urllib.request.Request('https://texttospeech.googleapis.com/v1/text:synthesize',
            data=json.dumps(body).encode(), headers={'Content-Type': 'application/json', 'X-Goog-Api-Key': key})
        try:
            return base64.b64decode(json.load(urllib.request.urlopen(req, timeout=60))['audioContent'])
        except urllib.error.HTTPError as e:
            if e.code not in (429, 500, 503) or attempt == 5: raise
        except (urllib.error.URLError, TimeoutError, ConnectionError, http.client.HTTPException):
            if attempt == 5: raise
        time.sleep(2 ** attempt)

def main():
    repo = sys.argv[1]
    voice = sys.argv[2] if len(sys.argv) > 2 else VOICE
    key = os.environ.get('GOOGLE_TTS_API_KEY') or sys.exit('GOOGLE_TTS_API_KEY yok')
    film = Path(repo).resolve().name
    t = tier(voice)
    caps = load_captions(repo)
    (HERE / film / 'clips' / voice).mkdir(parents=True, exist_ok=True)
    (HERE / film / 'ses.txt').write_text(voice + '\n')   # birlestir.py bu sesi kullanır

    L = ledger()
    month = date.today().strftime('%Y-%m')
    used = L.setdefault(month, {}).setdefault(t, 0)
    jobs = [(clip_path(film, voice, i, c['note']), c['note']) for i, c in enumerate(caps)]
    jobs = [(f, n) for f, n in jobs if not f.exists()]
    need = sum(len(n) for _, n in jobs)
    print(f'{film} · {t} bu ay {used:,} / ücretsiz {FREE[t]:,} · bu film {need:,} karakter')
    if used + need > FREE[t] * SAFETY:
        sys.exit(f'DUR: {used + need:,} karakter, ücretsiz sınırın %{int(SAFETY*100)}\'ını aşar. Ücretli kısma geçmemek için istek gönderilmedi.')
    for f, note in jobs:
        f.write_bytes(synth(note, voice, key))
        L[month][t] += len(note)
        LEDGER.write_text(json.dumps(L, indent=2) + '\n')

if __name__ == '__main__':
    main()
