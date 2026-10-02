# Seslendirme

Filmlerin `captions.js` içindeki seslendirme notları (`note`) Google Cloud Text-to-Speech ile seslendirilir.

```sh
# 1) Sesleri üret (GOOGLE_TTS_API_KEY gerekir; varsayılan ses tr-TR-Chirp3-HD-Kore)
python3 seslendirme/tts.py ../ucer-ucer-bolukler
# 2) Sesleri sessiz filme yerleştir (ağa çıkmaz)
python3 seslendirme/birlestir.py ../ucer-ucer-bolukler videos/ucer-ucer-bolukler.mp4   # isteğe bağlı 3. argüman: cümle sonrası bekleme (sn), varsayılan 1.5
```

**Ücretsiz kota.** `tts.py` gönderdiği her karakteri `kota.json` dosyasına ay ay yazar ve seçilen ses türünün aylık ücretsiz sınırının %90'ına gelince istek göndermeden durur (Chirp 3 HD, Neural2, Studio: 1M; WaveNet, Standard: 4M karakter). Ücretsiz kotası olmayan sesler (Gemini-TTS, özel ses) kabul edilmez. Sayaç yalnızca bu betikle yapılan istekleri bilir.

**Zamanlama.** Her cümle kendi altyazısıyla başlar. Her cümleden sonra bir sonraki cümleye kadar en az 1,5 sn bekleme kalır, çocuklar takip edebilsin diye; gerekirse görüntü bölüm sonunda dondurulur. Konuşma hızlandırılmaz. Bu adım yalnızca yerel ses dosyalarını kullanır, kota harcamaz.

| Film | Ses | Karakter | Süre |
|---|---|---|---|
| Üçer Üçer Bölükler | tr-TR-Chirp3-HD-Kore | 1 403 | 92 sn → 123,7 sn |

Çıktılar `seslendirme/<film>/`: `-sesli.mp4` (seslendirilmiş film), `-seslendirme.mp3` (yalnızca ses), `-seslendirme.srt` (anlatım metni, yeni zamanlarla).
