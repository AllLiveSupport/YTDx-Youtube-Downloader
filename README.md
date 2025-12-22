# YTDx - YouTube Video ve Müzik İndirici

Modern ve kullanıcı dostu bir YouTube video, müzik ve oynatma listesi indirme uygulaması.

## Özellikler

### Video Özellikleri
- Tek video ve oynatma listesi indirme desteği
- Yüksek kaliteli video indirme (VP9/AV1 kodekleri öncelikli)
- Farklı video kaliteleri seçeneği (144p'den 4K'ya kadar)

### Müzik Özellikleri
- YouTube videolarından yüksek kaliteli ses dosyası indirme (MP3/M4A)
- Oynatma listelerinden toplu müzik indirme
- Her müzik için otomatik kapak resmi ekleme
- Farklı ses kalitesi seçenekleri (düşük/orta/yüksek)

### Genel Özellikler
- FFmpeg otomatik algılama ve manuel seçim desteği
- Modern PyQt6 tabanlı kullanıcı arayüzü
- **Tema Desteği**: Göz yormayan Karanlık ve Aydınlık mod seçenekleri
- **Akıllı Önbellek Yönetimi**: Sorunsuz indirmeler için otomatik önbellek temizleme ve manuel kontrol
- **Güvenli Dosya Yönetimi**: Aynı isimli dosyaların üzerine yazılmasını önleyen akıllı kontrol sistemi
- İlerleme göstergesi ve detaylı durum bilgisi
- Kapsamlı hata yönetimi
- Çoklu dil desteği (Türkçe, İngilizce, İspanyolca, Rusça)

## Kurulum

1. Gerekli paketleri yükleyin:
   ```
   pip install -r requirements.txt
   ```

2. FFmpeg'i yükleyin:
   - Windows: [FFmpeg İndirme Sayfası](https://ffmpeg.org/download.html)
   - FFmpeg'i PATH'e ekleyin veya uygulama içinden manuel olarak seçin

3. Uygulamayı çalıştırın:
   ```
   python main.py
   ```

## Kullanım

### Video İndirme
1. Video sekmesine geçin
2. Video veya oynatma listesi URL'sini girin
3. İndirme klasörünü seçin
4. Video kalitesini seçin
5. "İndirmeyi Başlat" butonuna tıklayın

### Müzik İndirme
1. Müzik sekmesine geçin
2. Video veya oynatma listesi URL'sini girin
3. İndirme klasörünü seçin
4. Ses kalitesini ve formatını (MP3/M4A) seçin
5. Tek video veya playlist seçeneğini işaretleyin
6. "İndirmeyi Başlat" butonuna tıklayın

## Modüler Yapı

- `main.py`: Ana uygulama başlatıcısı
- `src/gui.py`: PyQt6 tabanlı kullanıcı arayüzü
- `src/downloader.py`: YouTube video ve müzik indirme işlemleri
- `src/language.py`: Çoklu dil desteği
- `src/custom_widgets.py`: Özelleştirilmiş arayüz bileşenleri
- `languages/`: Dil dosyaları (JSON formatında)

## Gereksinimler

- Python 3.7+
- PyQt6
- pytubefix
- Pillow (PIL) - Kapak resimleri için
- Mutagen - MP3/M4A etiketleri için
- Requests - İnternet istekleri için
- FFmpeg - Ses ve video dönüştürme için

## Lisans

Bu proje [MIT](LICENSE) lisansı altında lisanslanmıştır. Detaylar için `LICENSE` dosyasına bakabilirsiniz.
