# Seslendirme

Sayfadaki videolar, her filmin `captions.js` dosyasındaki seslendirme notlarıyla (`note`) Google Cloud Text-to-Speech kullanılarak seslendirildi. Ses `tr-TR-Chirp3-HD-Charon`; İngilizce bonus film *The Learning Ink* için `en-US-Chirp3-HD-Charon`. Her cümleden sonra en az 2 sn bekleme var; çocuklar takip edebilsin diye konuşma hızlandırılmaz, gerekirse görüntü bölüm sonunda dondurulur.

```sh
# Bütün filmler (10'arlı gruplar hâlinde, her grup dala gönderilir; kaldığı yerden sürer)
python3 seslendirme/hepsi.py <depolar>/ <sessiz-videolar>/
# Tek film
python3 seslendirme/tts.py ../ucer-ucer-bolukler                       # sesleri üret (GOOGLE_TTS_API_KEY)
python3 seslendirme/birlestir.py ../ucer-ucer-bolukler sessiz.mp4 videos/ucer-ucer-bolukler.mp4 --bekleme 2 --crf 27
```

Sessiz özgün videolar git geçmişinde durur (`git show 1d9da12:videos/<id>.mp4 > sessiz/<id>.mp4`); ayrıca her filmin kendi deposundaki Releases sayfasında.

**Ücretsiz kota.** `tts.py` gönderdiği her karakteri `kota.json` dosyasına ay ay yazar ve seçilen ses türünün aylık ücretsiz sınırının %90'ına gelince istek göndermeden durur (Chirp 3 HD, Neural2, Studio: 1M; WaveNet, Standard: 4M karakter). Ücretsiz kotası olmayan sesler (Gemini-TTS, özel ses) kabul edilmez. Aynı cümle aynı sesle bir daha gönderilmez. Sayaç yalnızca bu betiklerin isteklerini bilir. 100 filmin notları toplam ~121 500 karakter.

**Boyut.** GitHub Pages sitesi 1 GB'ı geçmemeli. Videolar x264 `veryslow`, `tune=animation`, CRF 27, ses AAC 64 kb/s mono ile sıkıştırılır; `hepsi.py` videos/ boyutunu izler, gidişat 900 MB'ı aşacaksa kalan filmlerde CRF'yi artırır.

**Dosyalar.** `sureler.json`: seslendirilmiş filmlerin süreleri. `<film>/<film>-seslendirme.srt`: anlatım metni, yeni zamanlarla. `ses_ornekleri.py`, `ses-ornekleri.mp3`, `sadachbia-charon.mp3`: ses seçimi için örnekler.
