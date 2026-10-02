#!/usr/bin/env python3
"""Bir filmin seslendirme notlarını Google Cloud TTS ile seslendirir.

Kullanım:  python3 seslendirme/tts.py <film-deposu> [ses-adı]
  <film-deposu>: captions.js içeren klasör (ör. ../ucer-ucer-bolukler)
  GOOGLE_TTS_API_KEY ortam değişkeni gerekir.

Ücretsiz kota koruması: gönderilen her karakter seslendirme/kota.json
dosyasına ay ay yazılır. Seçilen ses türünün aylık ücretsiz sınırının
%90'ına gelinirse betik istek göndermeden durur. Aynı cümle aynı sesle
daha önce seslendirildiyse önbellekten gelir, kotadan düşmez.
Not: bu sayaç yalnızca bu betikle yapılan istekleri bilir; aynı Google
projesinde başka TTS kullanımı varsa Cloud Console'dan kontrol edin.
"""
import base64, hashlib, json, os, subprocess, sys, urllib.request
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
# Aylık ücretsiz karakter sınırları (cloud.google.com/text-to-speech/pricing, Ekim 2026)
FREE = {'Chirp3-HD': 1_000_000, 'Neural2': 1_000_000, 'Studio': 1_000_000,
        'Wavenet': 4_000_000, 'Standard': 4_000_000}
SAFETY = 0.90

def tier(voice):
    for k in FREE:
        if f'-{k}-' in voice: return k
    sys.exit(f'Bilinmeyen ses türü: {voice} (ücretsiz kotası olmayan sesler kullanılmaz)')

def load_captions(repo):
    js = f"console.log(JSON.stringify(require({json.dumps(str(Path(repo).resolve() / 'captions.js'))})))"
    return json.loads(subprocess.check_output(['node', '-e', js]))

def main():
    repo = sys.argv[1]
    voice = sys.argv[2] if len(sys.argv) > 2 else 'tr-TR-Chirp3-HD-Kore'
    key = os.environ.get('GOOGLE_TTS_API_KEY') or sys.exit('GOOGLE_TTS_API_KEY yok')
    film = Path(repo).resolve().name
    t = tier(voice)
    caps = load_captions(repo)

    out = HERE / film / 'clips' / voice
    out.mkdir(parents=True, exist_ok=True)
    (HERE / film / 'ses.txt').write_text(voice + '\n')   # birlestir.py bu sesi kullanır
    ledger_path = HERE / 'kota.json'
    ledger = json.loads(ledger_path.read_text()) if ledger_path.exists() else {}
    month = date.today().strftime('%Y-%m')
    used = ledger.setdefault(month, {}).setdefault(t, 0)

    jobs = []
    for i, c in enumerate(caps):
        h = hashlib.sha1(f'{voice}|{c["note"]}'.encode()).hexdigest()[:10]
        f = out / f'{i+1:02d}-{h}.wav'
        if not f.exists(): jobs.append((f, c['note']))
    need = sum(len(n) for _, n in jobs)
    limit = int(FREE[t] * SAFETY)
    print(f'{t} · bu ay kullanılan {used:,} / ücretsiz {FREE[t]:,} · bu çalıştırma {need:,} karakter')
    if used + need > limit:
        sys.exit(f'DUR: {used + need:,} karakter, ücretsiz sınırın %{int(SAFETY*100)}\'ını aşar. Ücretli kısma geçmemek için istek gönderilmedi.')

    for f, note in jobs:
        body = {'input': {'text': note},
                'voice': {'languageCode': 'tr-TR', 'name': voice},
                'audioConfig': {'audioEncoding': 'LINEAR16', 'sampleRateHertz': 48000}}
        req = urllib.request.Request('https://texttospeech.googleapis.com/v1/text:synthesize',
            data=json.dumps(body).encode(), headers={'Content-Type': 'application/json', 'X-Goog-Api-Key': key})
        audio = json.load(urllib.request.urlopen(req))['audioContent']
        f.write_bytes(base64.b64decode(audio))
        ledger[month][t] += len(note)
        ledger_path.write_text(json.dumps(ledger, indent=2) + '\n')
        print(f'  ✓ {f.name}  ({len(note)} karakter)')
    print(f'Bitti · {t} bu ay toplam {ledger[month][t]:,} karakter')

if __name__ == '__main__':
    main()
