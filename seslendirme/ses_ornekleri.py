#!/usr/bin/env python3
"""Aynı cümleyi birkaç sesle seslendirir; ses seçmek için dinleme örnekleri.

Kullanım:  python3 seslendirme/ses_ornekleri.py "cümle" ses1 ses2 ...
Çıktı: seslendirme/ornekler/<ses>-<cümle-özeti>.wav. Kota tts.py ile aynı kota.json'dan
düşülür ve aynı ücretsiz sınır koruması uygulanır.
"""
import base64, hashlib, json, os, sys, urllib.request
from datetime import date
from tts import FREE, SAFETY, HERE, tier

def main():
    text, voices = sys.argv[1], sys.argv[2:]
    key = os.environ.get('GOOGLE_TTS_API_KEY') or sys.exit('GOOGLE_TTS_API_KEY yok')
    out = HERE / 'ornekler'; out.mkdir(exist_ok=True)
    ledger_path = HERE / 'kota.json'
    ledger = json.loads(ledger_path.read_text()) if ledger_path.exists() else {}
    month = date.today().strftime('%Y-%m')
    h = hashlib.sha1(text.encode()).hexdigest()[:8]
    path = lambda v: out / f'{v}-{h}.wav'
    jobs = [v for v in voices if not path(v).exists()]
    need = {}
    for v in jobs: need[tier(v)] = need.get(tier(v), 0) + len(text)
    for t, n in need.items():
        used = ledger.setdefault(month, {}).setdefault(t, 0)
        print(f'{t} · bu ay kullanılan {used:,} / ücretsiz {FREE[t]:,} · bu çalıştırma {n:,} karakter')
        if used + n > FREE[t] * SAFETY:
            sys.exit(f'DUR: {t} ücretsiz sınırın %{int(SAFETY*100)}\'ını aşar. İstek gönderilmedi.')
    for v in jobs:
        body = {'input': {'text': text}, 'voice': {'languageCode': v[:5], 'name': v},
                'audioConfig': {'audioEncoding': 'LINEAR16', 'sampleRateHertz': 48000}}
        req = urllib.request.Request('https://texttospeech.googleapis.com/v1/text:synthesize',
            data=json.dumps(body).encode(), headers={'Content-Type': 'application/json', 'X-Goog-Api-Key': key})
        path(v).write_bytes(base64.b64decode(json.load(urllib.request.urlopen(req))['audioContent']))
        ledger[month][tier(v)] += len(text)
        ledger_path.write_text(json.dumps(ledger, indent=2) + '\n')
        print(f'  ✓ {v}')
    print('Bitti ·', ', '.join(f'{t} bu ay {c:,}' for t, c in ledger[month].items()))

if __name__ == '__main__':
    main()
