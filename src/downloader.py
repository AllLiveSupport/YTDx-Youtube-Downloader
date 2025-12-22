"""
YTDx - Downloader Module
YouTube video indirme işlemlerini yöneten modül
"""

import os
import re
import subprocess
import logging
import time
import shutil
import tempfile
import socket
import random
import requests
import io
from typing import Callable, Dict, List, Optional, Tuple, Union, Any
from pytubefix import YouTube, Playlist
from pytubefix.exceptions import RegexMatchError, VideoUnavailable
from PIL import Image
import mutagen
from mutagen.id3 import ID3, APIC, TIT2, TPE1, TALB
from mutagen.mp4 import MP4, MP4Cover

# Dil modülünü içe aktar
from src.language import _

# Loglama ayarları
logger = logging.getLogger("YTDx.Downloader")

class FFmpegManager:
    """FFmpeg yönetim sınıfı.
    
    Bu sınıf, FFmpeg'in varlığını kontrol eder ve manuel olarak seçilen
    FFmpeg yolunu kullanabilir.
    """
    
    def __init__(self):
        """FFmpegManager sınıfının başlatıcısı."""
        self.ffmpeg_path = "ffmpeg"  # Varsayılan olarak PATH'den alır
        self.custom_ffmpeg_path = None
        self.is_available = self._check_ffmpeg()
        logger.info(f"FFmpeg kullanılabilirlik: {self.is_available}")
        
    def _check_ffmpeg(self) -> bool:
        """FFmpeg'in sistemde var olup olmadığını kontrol eder.
        
        Returns:
            bool: FFmpeg varsa True, yoksa False
        """
        # Ortam değişkenlerini yeniden yükle (PATH güncellemeleri için)
        os.environ = dict(os.environ)
        
        # Önce bilinen yolları kontrol et
        common_paths = [
            "ffmpeg",  # PATH'te varsa
            "C:\\ffmpeg\\bin\\ffmpeg.exe",
            "C:\\Program Files\\ffmpeg\\bin\\ffmpeg.exe",
            os.path.join(os.path.expanduser("~"), "ffmpeg", "bin", "ffmpeg.exe"),
        ]
        
        try:
            if self.custom_ffmpeg_path:
                # Özel yol kullanılıyorsa
                result = subprocess.run(
                    [self.custom_ffmpeg_path, "-version"], 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE, 
                    check=True
                )
                logger.info(f"FFmpeg bulundu: {self.custom_ffmpeg_path}")
                return True
            else:
                # Bilinen yolları dene
                for path in common_paths:
                    try:
                        result = subprocess.run(
                            [path, "-version"], 
                            stdout=subprocess.PIPE, 
                            stderr=subprocess.PIPE, 
                            check=True
                        )
                        # Başarılıysa, bu yolu kaydet
                        self.custom_ffmpeg_path = path
                        logger.info(f"FFmpeg otomatik olarak bulundu: {path}")
                        return True
                    except (subprocess.CalledProcessError, FileNotFoundError):
                        continue
                        
                # Bulunamadı
                logger.warning("FFmpeg bulunamadı, manuel seçim gerekebilir")
                return False
        except Exception as e:
            logger.error(f"FFmpeg kontrolü sırasında hata: {str(e)}")
            return False
            
    def set_custom_path(self, path: str) -> bool:
        """Özel bir FFmpeg yolu ayarlar.
        
        Args:
            path: FFmpeg yürütülebilir dosyasının yolu
            
        Returns:
            bool: Başarılı ise True, değilse False
        """
        if not path:
            return False
            
        # Klasör yolu verilmişse, ffmpeg.exe'yi ekle
        if os.path.isdir(path):
            ffmpeg_exe = os.path.join(path, "ffmpeg.exe")
            if os.path.exists(ffmpeg_exe):
                path = ffmpeg_exe
            else:
                # bin klasörü içinde olabilir
                bin_ffmpeg = os.path.join(path, "bin", "ffmpeg.exe")
                if os.path.exists(bin_ffmpeg):
                    path = bin_ffmpeg
                else:
                    logger.error(f"Verilen klasörde ffmpeg.exe bulunamadı: {path}")
                    return False
        
        # Dosya yolu kontrolü
        if not os.path.exists(path):
            logger.error(f"FFmpeg yolu geçersiz: {path}")
            return False
            
        self.custom_ffmpeg_path = path
        self.is_available = self._check_ffmpeg()
        
        if self.is_available:
            logger.info(f"Özel FFmpeg yolu ayarlandı: {path}")
            return True
        else:
            logger.error(f"Özel FFmpeg yolu geçersiz: {path}")
            self.custom_ffmpeg_path = None
            return False
            
    def get_ffmpeg_command(self) -> str:
        """FFmpeg komutunu döndürür.
        
        Returns:
            str: FFmpeg komutu
        """
        return self.custom_ffmpeg_path if self.custom_ffmpeg_path else "ffmpeg"


class Downloader:
    """YouTube video indirme işlemlerini yöneten sınıf.
    
    Bu sınıf, YouTube'dan video indirme, video ve ses dosyalarını birleştirme, 
    ve indirme ilerleme durumunu güncellemek için kullanılır.
    """
    
    # pytubefix önbellek dizini
    PYTUBE_CACHE_DIR = os.path.join(tempfile.gettempdir(), "pytube")
    
    # Bağlantı ayarları
    MAX_RETRIES = 3
    RETRY_DELAY = 2  # saniye
    CONNECTION_TIMEOUT = 30  # saniye
    
    def __init__(self):
        """Downloader sınıfının başlatıcısı."""
        self.failed_videos = []
        self.ffmpeg = FFmpegManager()
        self.progress_callback_fn = None
        self.status_callback_fn = None
        
        # Toplam boyut hesaplama için değişkenler
        self.total_video_size = 0
        self.total_audio_size = 0
        self.video_downloaded = 0
        self.audio_downloaded = 0
        self.current_download_phase = "video"  # "video" veya "audio"
        
        # Bağlantı zaman aşımını ayarla
        socket.setdefaulttimeout(self.CONNECTION_TIMEOUT)
        
        logger.info("Downloader başlatıldı")
        
    def clear_cache(self) -> bool:
        """pytubefix önbelleğini temizler.
        
        Returns:
            bool: Başarılı ise True, değilse False
        """
        try:
            # Önbellek klasörünü kontrol et
            if os.path.exists(self.PYTUBE_CACHE_DIR):
                # Klasörü sil
                shutil.rmtree(self.PYTUBE_CACHE_DIR, ignore_errors=True)
                logger.info(f"pytubefix önbelleği temizlendi: {self.PYTUBE_CACHE_DIR}")
                return True
            else:
                logger.info("pytubefix önbelleği zaten temiz")
                return True
        except Exception as e:
            logger.error(f"Önbellek temizleme hatası: {str(e)}")
            return False

    def set_callbacks(self, progress_callback: Callable = None, status_callback: Callable = None, ask_overwrite_callback: Callable = None):
        """Callback fonksiyonlarını ayarlar.
        
        Args:
            progress_callback: İlerleme durumunu bildiren callback
            status_callback: Durum mesajlarını bildiren callback
            ask_overwrite_callback: Dosya üzerine yazma izni soran callback
        """
        self.progress_callback_fn = progress_callback
        self.status_callback_fn = status_callback
        self.ask_overwrite_callback = ask_overwrite_callback
        
    def sanitize_filename(self, filename: str) -> str:
        """Dosya adını güvenli hale getirir.
        
        Args:
            filename: Orijinal dosya adı
            
        Returns:
            Güvenli hale getirilmiş dosya adı
        """
        filename = re.sub(r'[<>:"/\\|?*]', '', filename)
        filename = re.sub(r'\s+', '_', filename)
        return filename.strip('_')
        
    def ffmpeg_combine(self, video_file: str, audio_file: str, output_file: str) -> Tuple[bool, str]:
        """Video ve ses dosyalarını FFmpeg kullanarak birleştirir.
        
        Args:
            video_file: Video dosyasının yolu
            audio_file: Ses dosyasının yolu
            output_file: Çıktı dosyasının yolu
            
        Returns:
            Tuple[bool, str]: Başarı durumu ve FFmpeg çıktısı
        """
        try:
            # FFmpeg komutunu oluştur
            cmd = [
                self.ffmpeg.get_ffmpeg_command(),
                '-i', video_file,  # Video girişi
                '-i', audio_file,  # Ses girişi
                '-c:v', 'copy',    # Video codec'ini kopyala
                '-c:a', 'aac',      # Ses codec'i AAC
                '-map', '0:v:0',    # İlk girişten video akışını al
                '-map', '1:a:0',    # İkinci girişten ses akışını al
                '-y',               # Mevcut dosyanın üzerine yaz
                output_file
            ]
            
            # Komutu logla
            logger.info(f"FFmpeg komutu: {' '.join(cmd)}")
            
            # FFmpeg'i arka planda çalıştır (konsol penceresi göstermeden)
            startupinfo = None
            if os.name == 'nt':  # Windows için
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = 0  # SW_HIDE
            
            # FFmpeg'i çalıştır
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                startupinfo=startupinfo  # Konsol penceresini gizle
            )
            
            # Sonuçları kontrol et
            if result.returncode == 0:
                logger.info("FFmpeg birleştirme başarılı")
                return True, ""
            else:
                logger.error(f"FFmpeg hatası: {result.stderr}")
                return False, result.stderr
                
        except Exception as e:
            error_msg = str(e)
            logger.error(f"FFmpeg çalıştırma hatası: {error_msg}")
            
        except FileNotFoundError:
            error_msg = "FFmpeg sistemde bulunamadı. Lütfen FFmpeg'yi yükleyin veya manuel olarak seçin."
            logger.error(error_msg)
            return False, error_msg
            
    def progress_callback(self, stream: Any, chunk: bytes, bytes_remaining: int) -> None:
        """YouTube indirme ilerleme durumunu günceller.
        
        Args:
            stream: İndirilen akış
            chunk: İndirilen veri parçası
            bytes_remaining: Kalan bayt sayısı
        """
        if not self.progress_callback_fn:
            return
            
        total_size = stream.filesize
        bytes_downloaded = total_size - bytes_remaining
        progress = bytes_downloaded / total_size
        
        # Akış türünü belirle (video mu ses mi)
        stream_type = "video" if stream.includes_video_track else "audio"
        
        # Toplam boyut hesaplama için değişkenleri güncelle
        if stream_type == "video":
            self.video_downloaded = bytes_downloaded
        else:
            self.audio_downloaded = bytes_downloaded
        
        # Toplam indirilen ve toplam boyutu hesapla
        total_downloaded = self.video_downloaded + self.audio_downloaded
        total_combined_size = self.total_video_size + self.total_audio_size
        
        # Eğer toplam boyut biliniyorsa, toplam ilerlemeyi hesapla
        if total_combined_size > 0:
            combined_progress = total_downloaded / total_combined_size
            # Toplam boyut bilgisiyle callback çağır
            self.progress_callback_fn(combined_progress, total_downloaded, total_combined_size, "toplam")
        else:
            # Sadece mevcut akış bilgisiyle callback çağır
            self.progress_callback_fn(progress, bytes_downloaded, total_size, stream_type)
        
        # Loglama
        if progress % 0.1 < 0.01:  # Her %10'luk ilerleme için log
            if total_combined_size > 0:
                logger.info(f"Toplam indirme ilerlemesi: %{combined_progress * 100:.1f} | {total_downloaded/1024/1024:.1f}MB / {total_combined_size/1024/1024:.1f}MB")
            else:
                logger.info(f"{stream_type.capitalize()} indirme ilerlemesi: %{progress * 100:.1f} | {bytes_downloaded/1024/1024:.1f}MB / {total_size/1024/1024:.1f}MB")
            
    def download_video(self, video_url: str, download_path: str, quality: str) -> bool:
        """YouTube videosunu indirir ve işler.
        
        Args:
            video_url: İndirilecek videonun URL'si
            download_path: İndirme klasörü
            quality: Video kalitesi ("auto" veya "720p" gibi)
            
        Returns:
            İndirme başarılı ise True, değilse False
        """
        logger.info(f"Video indirme başlatılıyor: {video_url}")
        
        # Yeniden deneme sayısını sıfırla
        retry_count = 0
        
        while retry_count <= self.MAX_RETRIES:
            try:
                # Önbellek temizliği (ilk denemede değil, yeniden denemelerde)
                if retry_count > 0:
                    self.clear_cache()
                    if self.status_callback_fn:
                        self.status_callback_fn(f"Yeniden deneme {retry_count}/{self.MAX_RETRIES}...", "warning")
                    logger.info(f"Yeniden deneme {retry_count}/{self.MAX_RETRIES}: {video_url}")
                    time.sleep(self.RETRY_DELAY)  # Yeniden denemeden önce bekle
                
                # YouTube nesnesini oluştur
                video = YouTube(video_url, on_progress_callback=self.progress_callback)
                
                if self.status_callback_fn:
                    self.status_callback_fn(f"{video.title} indiriliyor...", "info")
                    
                logger.info(f"Video başlığı: {video.title}")

                # En iyi video akışını seç
                video_stream = self._select_best_video_stream(video, quality)
                if not video_stream:
                    raise ValueError(f"Video akışı bulunamadı: {quality}")
                    
                # En iyi ses akışını seç
                audio_stream = video.streams.filter(only_audio=True).order_by("abr").desc().first()
                if not audio_stream:
                    raise ValueError("Ses akışı bulunamadı")
                    
                logger.info(f"Seçilen video akışı: {video_stream.resolution}, {video_stream.mime_type}")
                logger.info(f"Seçilen ses akışı: {audio_stream.abr}")
                
                # Toplam boyut hesaplama için akış boyutlarını ayarla
                self.total_video_size = video_stream.filesize if video_stream.filesize else 0
                self.total_audio_size = audio_stream.filesize if audio_stream.filesize else 0
                self.video_downloaded = 0
                self.audio_downloaded = 0
                
                logger.info(f"Video boyutu: {self.total_video_size/1024/1024:.1f}MB, Ses boyutu: {self.total_audio_size/1024/1024:.1f}MB")
                logger.info(f"Toplam boyut: {(self.total_video_size + self.total_audio_size)/1024/1024:.1f}MB")

                # Dosya adlarını hazırla
                video_title = self.sanitize_filename(video.title)
                output_file = os.path.join(download_path, f"{video_title}.mp4")
                temp_video_file = os.path.join(download_path, f"{video_title}_video.mp4")
                temp_audio_file = os.path.join(download_path, f"{video_title}_audio.mp4")

                # Mevcut dosya kontrolü
                if os.path.exists(output_file):
                    file_size = os.path.getsize(output_file)
                    if file_size > 1024*1024:  # 1MB'dan büyükse geçerli kabul et
                        # Kullanıcıya sor
                        if self.status_callback_fn:
                            # Özel bir durum mesajı gönder
                            self.status_callback_fn(f"FILE_EXISTS:{video.title}:{output_file}", "question")
                            
                            # Yanıt bekle (bu fonksiyon dışarıdan yanıtı ayarlayacak)
                            # Yanıt gelene kadar bekle (max 30 saniye)
                            wait_start = time.time()
                            while not hasattr(self, 'overwrite_response') and time.time() - wait_start < 30:
                                time.sleep(0.1)
                                
                            # Yanıt kontrolü
                            if hasattr(self, 'overwrite_response'):
                                if not self.overwrite_response:  # Üzerine yazma
                                    logger.info(f"Kullanıcı dosyanın üzerine yazmayı reddetti: {output_file}")
                                    delattr(self, 'overwrite_response')  # Yanıtı sıfırla
                                    return True  # İndirme başarılı sayılır (kullanıcı atladı)
                                else:  # Üzerine yaz
                                    logger.info(f"Kullanıcı dosyanın üzerine yazma onayı verdi: {output_file}")
                                    os.remove(output_file)  # Mevcut dosyayı sil
                                    delattr(self, 'overwrite_response')  # Yanıtı sıfırla
                            else:
                                # Yanıt gelmedi, varsayılan olarak atlat
                                logger.info(f"Dosya zaten mevcut, atlatılıyor: {output_file}")
                                return True
                        else:
                            # Callback fonksiyonu yoksa, varsayılan olarak atlat
                            logger.info(f"Video zaten mevcut, atlatılıyor: {output_file}")
                            return True
                    else:
                        # Küçük veya bozuk dosyayı sil
                        os.remove(output_file)
                        logger.info(f"Bozuk dosya silindi: {output_file}")

                # Video indirme
                try:
                    if self.status_callback_fn:
                        self.status_callback_fn(f"{video.title} {_('downloading_video')}...", "info")
                        
                    video_file = video_stream.download(output_path=download_path, filename=f"{video_title}_video.mp4")
                    
                    # İndirilen dosyayı kontrol et
                    if not os.path.exists(video_file) or os.path.getsize(video_file) < 10*1024:  # 10KB'dan küçükse hata
                        raise Exception("Video dosyası indirilemedi veya bozuk")
                except Exception as e:
                    logger.error(f"Video indirme hatası: {str(e)}")
                    retry_count += 1
                    continue
                
                # Ses indirme
                try:
                    if self.status_callback_fn:
                        self.status_callback_fn(f"{video.title} {_('downloading_audio')}...", "info")
                        
                    audio_file = audio_stream.download(output_path=download_path, filename=f"{video_title}_audio.mp4")
                    
                    # İndirilen dosyayı kontrol et
                    if not os.path.exists(audio_file) or os.path.getsize(audio_file) < 5*1024:  # 5KB'dan küçükse hata
                        raise Exception("Ses dosyası indirilemedi veya bozuk")
                except Exception as e:
                    logger.error(f"Ses indirme hatası: {str(e)}")
                    # Video dosyasını temizle
                    if os.path.exists(video_file):
                        os.remove(video_file)
                    retry_count += 1
                    continue

                # Dosyaları birleştir
                if self.status_callback_fn:
                    self.status_callback_fn(f"{video.title} {_('merging')}...", "info")
                    
                success, ffmpeg_output = self.ffmpeg_combine(video_file, audio_file, output_file)
                
                if success:
                    # Geçici dosyaları temizle
                    try:
                        os.remove(video_file)
                        os.remove(audio_file)
                        
                        if self.status_callback_fn:
                            self.status_callback_fn(f"{video.title} başarıyla indirildi.", "success")
                            
                        logger.info(f"Video başarıyla indirildi: {output_file}")
                        return True
                    except OSError as e:
                        if self.status_callback_fn:
                            self.status_callback_fn(f"Dosya temizleme hatası: {e}", "warning")
                            
                        logger.warning(f"Geçici dosyalar temizlenemedi: {e}")
                        return True  # Yine de indirme başarılı sayılır
                else:
                    # Birleştirme başarısız, geçici dosyaları temizle ve yeniden dene
                    try:
                        if os.path.exists(video_file):
                            os.remove(video_file)
                        if os.path.exists(audio_file):
                            os.remove(audio_file)
                    except:
                        pass
                    
                    logger.error(f"FFmpeg birleştirme hatası: {ffmpeg_output}")
                    retry_count += 1
                    continue

            except (VideoUnavailable, RegexMatchError) as e:
                # Bu hatalar yeniden denemeye değmez
                self.failed_videos.append(video_url)
                error_msg = str(e)
                
                if self.status_callback_fn:
                    self.status_callback_fn(f"Video kullanılamıyor: {error_msg}", "error")
                    
                logger.error(f"Video kullanılamıyor: {error_msg} - URL: {video_url}")
                return False
                
            except Exception as e:
                # Diğer hatalar için yeniden dene
                error_msg = str(e)
                
                if self.status_callback_fn:
                    self.status_callback_fn(f"Hata: {error_msg}", "error")
                    
                logger.error(f"Video indirme hatası: {error_msg} - URL: {video_url}")
                retry_count += 1
                
                # Son deneme başarısız olduysa
                if retry_count > self.MAX_RETRIES:
                    self.failed_videos.append(video_url)
                    return False
                    
                # Yeniden denemeden önce bekle (artan süre ile)
                time.sleep(self.RETRY_DELAY * retry_count)
                continue
                
        # Tüm denemeler başarısız oldu
        self.failed_videos.append(video_url)
        return False
            
    def _select_best_video_stream(self, video: YouTube, quality: str) -> Any:
        """Belirtilen kaliteye göre en iyi video akışını seçer.
        
        Args:
            video: YouTube video nesnesi
            quality: İstenen video kalitesi
            
        Returns:
            Seçilen video akışı veya bulunamazsa None
        """
        # Otomatik kalite seçimi
        if quality == "auto":
            # Tüm video-only akışları al
            video_streams = video.streams.filter(progressive=False, only_video=True)
            if not video_streams:
                return None
                
            # VP9/AV1 kodeklerini önceliklendir
            preferred_streams = [s for s in video_streams if "vp9" in s.mime_type or "av1" in s.mime_type]
            if preferred_streams:
                return max(preferred_streams, key=lambda stream: stream.filesize)
            else:
                return max(video_streams, key=lambda stream: stream.filesize)
        else:
            # Belirli bir çözünürlükte en iyi akışı seç
            video_streams = video.streams.filter(res=quality, only_video=True)
            
            if not video_streams:
                if self.status_callback_fn:
                    self.status_callback_fn(f"{quality} bulunamadı, en yakın kaliteye geçiliyor...", "warning")
                    
                logger.warning(f"{quality} bulunamadı, en yakın kalite seçilecek")
                return max(video.streams.filter(progressive=False, only_video=True), 
                          key=lambda stream: stream.filesize)
            
            # VP9/AV1 kodeklerini önceliklendir
            preferred_streams = [s for s in video_streams if "vp9" in s.mime_type or "av1" in s.mime_type]
            if preferred_streams:
                return max(preferred_streams, key=lambda stream: stream.filesize)
            else:
                return max(video_streams, key=lambda stream: stream.filesize)
                
    def add_thumbnail_to_audio(self, audio_file: str, video: YouTube) -> bool:
        """Ses dosyasına video küçük resmini ekler.
        
        Args:
            audio_file: Ses dosyasının yolu
            video: YouTube video nesnesi
            
        Returns:
            bool: Başarılı ise True, değilse False
        """
        try:
            if self.status_callback_fn:
                self.status_callback_fn(_("adding_thumbnail"), "info")
                
            # Video ID'sini al
            video_id = video.video_id
            
            # YouTube'un thumbnail formatlarını dene (en yüksek kaliteden en düşüğe doğru)
            thumbnail_urls = [
                f"https://i.ytimg.com/vi/{video_id}/maxresdefault.jpg",  # En yüksek kalite
                f"https://i.ytimg.com/vi/{video_id}/sddefault.jpg",      # Standard definition
                f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg",      # High quality
                f"https://i.ytimg.com/vi/{video_id}/mqdefault.jpg",      # Medium quality
                f"https://i.ytimg.com/vi/{video_id}/default.jpg"         # Düşük kalite
            ]
            
            # Her bir thumbnail URL'ini dene
            img_data = None
            used_thumbnail = None
            
            for url in thumbnail_urls:
                logger.info(f"Thumbnail deneniyor: {url}")
                response = requests.get(url)
                if response.status_code == 200:
                    img_data = response.content
                    used_thumbnail = url
                    logger.info(f"Thumbnail başarıyla indirildi: {url}")
                    break
            
            # Eğer hiçbir thumbnail bulunamazsa, hata döndür
            if img_data is None:
                logger.warning(f"Video için hiçbir thumbnail bulunamadı: {video_id}")
                return False
            
            # Resmi işle
            img = Image.open(io.BytesIO(img_data))
            
            # Resmi 800x800 boyutuna getir (büyük ve kaliteli bir kapak resmi)
            img = img.resize((800, 800), Image.LANCZOS)
            
            # Resmi geçici bir dosyaya kaydet (yüksek kaliteli)
            temp_img = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
            img.save(temp_img.name, "JPEG", quality=95)
            temp_img.close()
            
            # Dosya uzantısını kontrol et ve uygun şekilde kapak resmini ekle
            file_ext = os.path.splitext(audio_file)[1].lower()
            
            if file_ext == ".mp3":
                # MP3 için ID3 etiketlerini kullan
                try:
                    # MP3 dosyasını tamamen yeniden aç
                    from mutagen.id3 import ID3, APIC, TIT2, TPE1, TALB, ID3NoHeaderError
                    
                    # Önce dosyayı kontrol et
                    try:
                        # Mevcut ID3 etiketlerini sil (temiz başlangıç için)
                        try:
                            ID3(audio_file).delete()
                        except:
                            pass
                            
                        # Yeni ID3 etiketleri oluştur
                        audio = ID3()
                        
                        # Başlık, sanatçı ve albüm bilgilerini ekle
                        audio.add(TIT2(encoding=3, text=video.title))
                        audio.add(TPE1(encoding=3, text=video.author))
                        audio.add(TALB(encoding=3, text=video.author))
                        
                        # Kapak resmini ekle
                        with open(temp_img.name, 'rb') as albumart:
                            audio.add(APIC(
                                encoding=3,
                                mime='image/jpeg',
                                type=3, # 3 = Kapak resmi
                                desc='Cover',
                                data=albumart.read()
                            ))
                        
                        # Etiketleri dosyaya kaydet
                        audio.save(audio_file)
                        logger.info(f"MP3 kapak resmi başarıyla eklendi: {audio_file}")
                    except Exception as e:
                        logger.error(f"MP3 etiket oluşturma hatası: {str(e)}")
                        raise e
                    
                except Exception as e:
                    logger.error(f"MP3 kapak resmi ekleme hatası: {str(e)}")
                    if self.status_callback_fn:
                        self.status_callback_fn(_("thumbnail_failed_but_audio_ok"), "warning")
                    # Kapak resmi eklenemese bile ses dosyası indirildi, başarılı kabul et
                    return True
                
            elif file_ext == ".m4a":
                try:
                    # M4A için MP4 etiketlerini kullan
                    audio = MP4(audio_file)
                    
                    # Başlık ve sanatçı bilgilerini ekle
                    audio["\xa9nam"] = video.title
                    audio["\xa9ART"] = video.author
                    audio["\xa9alb"] = video.author
                    
                    # Kapak resmini ekle
                    with open(temp_img.name, 'rb') as albumart:
                        audio["covr"] = [MP4Cover(albumart.read(), imageformat=MP4Cover.FORMAT_JPEG)]
                        
                    audio.save()
                except Exception as e:
                    logger.error(f"M4A kapak resmi ekleme hatası: {str(e)}")
                    # Kapak resmi eklenemedi ama ses dosyası başarıyla indirildi
                    if self.status_callback_fn:
                        self.status_callback_fn(_("thumbnail_failed_but_audio_ok"), "warning")
                    # Kapak resmi eklenemese bile ses dosyası indirildi, başarılı kabul et
                    return True
                
            # Geçici dosyayı sil
            try:
                os.unlink(temp_img.name)
            except Exception as e:
                logger.warning(f"Geçici dosya silinemedi: {str(e)}")
                
            if self.status_callback_fn:
                self.status_callback_fn(_("thumbnail_added"), "success")
                
            return True
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Kapak resmi ekleme hatası: {error_msg}")
            
            if self.status_callback_fn:
                self.status_callback_fn(_("thumbnail_failed"), "error")
                
            return False
        
    def download_audio_playlist(self, playlist_url: str, download_path: str, quality: str = "high", audio_format: str = "mp3", include_thumbnail: bool = True) -> Tuple[int, int]:
        """Bir YouTube oynatma listesindeki tüm videoların ses dosyalarını indirir.
        
        Args:
            playlist_url: İndirilecek oynatma listesinin URL'si
            download_path: İndirme klasörü
            quality: Ses kalitesi ("high", "medium", "low")
            audio_format: Ses formatı ("mp3", "m4a")
            include_thumbnail: Albüm kapak resmi eklensin mi?
            
        Returns:
            Tuple[int, int]: Başarılı ve başarısız indirme sayıları
        """
        # Başlangıçta önbelleği temizle
        self.clear_cache()
        
        # Yeniden deneme sayısı
        retry_count = 0
        max_playlist_retries = 2
        
        while retry_count <= max_playlist_retries:
            try:
                # Yeniden deneme bilgisi
                if retry_count > 0:
                    if self.status_callback_fn:
                        self.status_callback_fn(f"Playlist yeniden deneniyor ({retry_count}/{max_playlist_retries})...", "warning")
                    logger.info(f"Playlist yeniden deneniyor ({retry_count}/{max_playlist_retries}): {playlist_url}")
                    time.sleep(self.RETRY_DELAY * 2)  # Playlist için daha uzun bekle
                    self.clear_cache()  # Önbelleği temizle
                
                # Playlist bilgilerini al
                if self.status_callback_fn:
                    self.status_callback_fn(_("getting_playlist_info"), "info")
                
                # Playlist nesnesini oluştur
                try:
                    playlist = Playlist(playlist_url)
                    
                    # Video URL'lerini güvenli bir şekilde al
                    try:
                        # Önce video_urls'yi listeye dönüştür
                        video_urls = []
                        for url in playlist.video_urls:
                            video_urls.append(url)
                        total_videos = len(video_urls)
                    except Exception as e:
                        logger.error(f"Video URL'leri alınırken hata: {str(e)}")
                        raise
                    
                    # Playlist adını al
                    try:
                        playlist_title = playlist.title
                    except:
                        playlist_title = "Playlist"
                except Exception as e:
                    logger.error(f"Playlist yükleme hatası: {str(e)}")
                    retry_count += 1
                    if retry_count > max_playlist_retries:
                        if self.status_callback_fn:
                            self.status_callback_fn(f"Playlist yüklenemedi: {str(e)}", "error")
                        return 0, 0
                    continue
                
                if total_videos == 0:
                    if self.status_callback_fn:
                        self.status_callback_fn(_("playlist_empty_audio_old"), "error")
                        
                    logger.warning(f"Boş playlist: {playlist_url}")
                    return 0, 0
                    
                logger.info(f"Playlist bulundu: {playlist_title} - {total_videos} video")
                
                if self.status_callback_fn:
                    self.status_callback_fn(f"Playlist: {playlist_title} - {total_videos} {_('videos_found')}", "info")
                
                # İndirme işlemi
                success_count = 0
                failed_count = 0
                
                # Video URL'lerini karıştır (bağlantı sorunlarını azaltmak için)
                # Bu, aynı sunucuya ardışık istekleri azaltır
                video_urls_shuffled = list(video_urls)  # list() ile listeye dönüştür
                random.shuffle(video_urls_shuffled)
                
                for idx, video_url in enumerate(video_urls_shuffled):
                    # İlerleme bilgisi
                    if self.status_callback_fn:
                        self.status_callback_fn(f"{_('downloading_audio')} {idx + 1}/{total_videos}...", "info")
                        
                    logger.info(f"Playlist ses dosyası indiriliyor [{idx + 1}/{total_videos}]: {video_url}")
                    
                    # Her 5 videodan sonra önbelleği temizle
                    if idx > 0 and idx % 5 == 0:
                        self.clear_cache()
                        
                    # Ses dosyasını indir
                    result = self.download_audio(video_url, download_path, quality, audio_format, include_thumbnail)
                    if result:
                        success_count += 1
                    else:
                        failed_count += 1
                        
                    # Her 10 videodan sonra kısa bir bekleme (hız sınırlamasını önlemek için)
                    if idx > 0 and idx % 10 == 0 and idx < total_videos - 1:
                        if self.status_callback_fn:
                            self.status_callback_fn(_("waiting_to_prevent_rate_limit_audio"), "info")
                        time.sleep(2)  # 2 saniye bekle
                
                # Sonuç bilgisi
                if self.status_callback_fn:
                    if failed_count > 0:
                        self.status_callback_fn(
                            f"{success_count} {_('audio_files_downloaded')}, {failed_count} {_('audio_files_failed')}", 
                            "warning"
                        )
                    else:
                        self.status_callback_fn(
                            f"{success_count} {_('audio_files_downloaded')}", 
                            "success"
                        )
                
                return success_count, failed_count
                
            except Exception as e:
                error_msg = str(e)
                logger.error(f"Playlist ses indirme hatası: {error_msg}")
                retry_count += 1
                
                if retry_count > max_playlist_retries:
                    if self.status_callback_fn:
                        self.status_callback_fn(f"Playlist ses indirme hatası: {error_msg}", "error")
                    return 0, 0
                    
        return 0, 0
        try:
            if self.status_callback_fn:
                self.status_callback_fn(_("adding_thumbnail"), "info")
                
            # Video küçük resmini al
            thumbnail_url = video.thumbnail_url
            if not thumbnail_url:
                logger.warning("Video için küçük resim bulunamadı")
                return False
                
            # Küçük resmi indir
            response = requests.get(thumbnail_url)
            if response.status_code != 200:
                logger.error(f"Küçük resim indirilemedi: {response.status_code}")
                return False
                
            # Resmi işle
            img_data = response.content
            img = Image.open(io.BytesIO(img_data))
            
            # Resmi 800x800 boyutuna getir (büyük ve kaliteli bir kapak resmi)
            img = img.resize((800, 800), Image.LANCZOS)
            
            # Resmi geçici bir dosyaya kaydet (yüksek kaliteli)
            temp_img = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
            img.save(temp_img.name, "JPEG", quality=95)
            temp_img.close()
            
            # Dosya uzantısını kontrol et ve uygun şekilde kapak resmini ekle
            file_ext = os.path.splitext(audio_file)[1].lower()
            
            if file_ext == ".mp3":
                # MP3 için ID3 etiketlerini kullan
                try:
                    audio = ID3(audio_file)
                except:
                    # ID3 etiketleri yoksa oluştur
                    audio = ID3()
                    
                # Başlık, sanatçı ve albüm bilgilerini ekle
                audio.add(TIT2(encoding=3, text=video.title))
                audio.add(TPE1(encoding=3, text=video.author))
                audio.add(TALB(encoding=3, text=video.author))
                
                # Kapak resmini ekle
                with open(temp_img.name, 'rb') as albumart:
                    audio.add(APIC(
                        encoding=3,
                        mime='image/jpeg',
                        type=3, # 3 = Kapak resmi
                        desc='Cover',
                        data=albumart.read()
                    ))
                    
                audio.save(audio_file)
                
            elif file_ext == ".m4a":
                try:
                    # M4A için MP4 etiketlerini kullan
                    audio = MP4(audio_file)
                    
                    # Başlık ve sanatçı bilgilerini ekle
                    audio["\xa9nam"] = video.title
                    audio["\xa9ART"] = video.author
                    audio["\xa9alb"] = video.author
                    
                    # Kapak resmini ekle
                    with open(temp_img.name, 'rb') as albumart:
                        audio["covr"] = [MP4Cover(albumart.read(), imageformat=MP4Cover.FORMAT_JPEG)]
                        
                    audio.save()
                except Exception as e:
                    logger.error(f"M4A kapak resmi ekleme hatası: {str(e)}")
                    # Kapak resmi eklenemedi ama ses dosyası başarıyla indirildi
                    if self.status_callback_fn:
                        self.status_callback_fn(_("thumbnail_failed_but_audio_ok"), "warning")
                    # Kapak resmi eklenemese bile ses dosyası indirildi, başarılı kabul et
                    return True
                
            # Geçici dosyayı sil
            try:
                os.unlink(temp_img.name)
            except:
                pass
                
            if self.status_callback_fn:
                self.status_callback_fn(_("thumbnail_added"), "success")
                
            return True
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Kapak resmi ekleme hatası: {error_msg}")
            
            if self.status_callback_fn:
                self.status_callback_fn(_("thumbnail_failed"), "error")
                
            return False
    
    def download_audio(self, video_url: str, download_path: str, quality: str = "high", audio_format: str = "mp3", include_thumbnail: bool = True) -> bool:
        """YouTube videosundan sadece ses dosyasını indirir.
        
        Args:
            video_url: İndirilecek video URL'si
            download_path: İndirme klasörü
            quality: Ses kalitesi ("high", "medium", "low")
            audio_format: Ses formatı ("mp3" veya "m4a")
            include_thumbnail: Albüm kapak resmi eklensin mi
            
        Returns:
            bool: İndirme başarılı ise True, değilse False
        """
        # İndirme klasörünü oluştur
        os.makedirs(download_path, exist_ok=True)
        
        # Yeniden deneme sayısı
        max_retries = 3
        retry_count = 0
        
        while retry_count <= max_retries:
            try:
                # YouTube nesnesini oluştur
                yt = YouTube(video_url, on_progress_callback=self.progress_callback)
                
                # Video başlığını al ve güvenli dosya adı oluştur
                video_title = yt.title
                safe_title = self.sanitize_filename(video_title)
                
                # Ses akışını seç
                if self.status_callback_fn:
                    self.status_callback_fn(_("downloading_audio"), "info")
                
                # Kaliteye göre ses akışını seç
                if quality == "high":
                    audio_stream = yt.streams.filter(only_audio=True).order_by('abr').desc().first()
                elif quality == "low":
                    audio_stream = yt.streams.filter(only_audio=True).order_by('abr').first()
                else:  # medium veya diğer değerler için
                    audio_streams = yt.streams.filter(only_audio=True).order_by('abr').desc()
                    if len(audio_streams) >= 2:
                        audio_stream = audio_streams[len(audio_streams) // 2]  # Orta kalitede bir akış seç
                    else:
                        audio_stream = audio_streams.first()
                
                if not audio_stream:
                    if self.status_callback_fn:
                        self.status_callback_fn(_("audio_download_failed"), "error")
                    return False
                
                # Çıktı dosya yolunu oluştur
                temp_file = audio_stream.download(
                    output_path=tempfile.gettempdir(),
                    filename=f"{safe_title}_temp"
                )
                
                # Dosya uzantısını belirle
                if audio_format.lower() == "mp3":
                    output_file = os.path.join(download_path, f"{safe_title}.mp3")
                else:  # m4a veya diğer değerler için
                    output_file = os.path.join(download_path, f"{safe_title}.m4a")
                
                # Dosya zaten varsa kullanıcıya sor
                if os.path.exists(output_file):
                    # Kullanıcıya sor
                    if self.status_callback_fn:
                        # Özel bir durum mesajı gönder (video indirmedeki gibi)
                        self.status_callback_fn(f"FILE_EXISTS:{video_title}:{output_file}", "question")
                        
                        # Yanıt bekle (bu fonksiyon dışarıdan yanıtı ayarlayacak)
                        # Yanıt gelene kadar bekle (max 30 saniye)
                        wait_start = time.time()
                        while not hasattr(self, 'overwrite_response') and time.time() - wait_start < 30:
                            time.sleep(0.1)
                            
                        # Yanıt kontrolü
                        if hasattr(self, 'overwrite_response'):
                            if not self.overwrite_response:  # Üzerine yazma
                                logger.info(f"Kullanıcı ses dosyasının üzerine yazmayı reddetti: {output_file}")
                                delattr(self, 'overwrite_response')  # Yanıtı sıfırla
                                return True  # İndirme başarılı sayılır (kullanıcı atladı)
                            else:  # Üzerine yaz
                                logger.info(f"Kullanıcı ses dosyasının üzerine yazma onayı verdi: {output_file}")
                                try:
                                    os.remove(output_file)  # Mevcut dosyayı sil
                                except Exception as e:
                                    logger.error(f"Dosya silinirken hata oluştu: {e}")
                                delattr(self, 'overwrite_response')  # Yanıtı sıfırla
                        else:
                            # Yanıt gelmedi, varsayılan olarak atlat
                            logger.info(f"Ses dosyası zaten mevcut, atlatılıyor: {output_file}")
                            return True
                    else:
                        # Callback fonksiyonu yoksa, varsayılan olarak atlat
                        logger.info(f"Ses dosyası zaten mevcut, atlatılıyor: {output_file}")
                        return True
                    
                    # Eğer buraya geldiysek, üzerine yazma işlemi yapılacak
                    # Döngüden çıkıp indirme işlemine devam et
                    # Dosya zaten silindi veya üzerine yazma onayı alındı
                
                # FFmpeg ile ses formatını dönüştür
                if self.ffmpeg.is_available:
                    ffmpeg_cmd = self.ffmpeg.get_ffmpeg_command()
                    
                    # Ses kalitesini ayarla
                    if audio_format.lower() == "mp3":
                        if quality == "high":
                            bitrate = "320k"
                        elif quality == "medium":
                            bitrate = "192k"
                        else:  # low
                            bitrate = "128k"
                            
                        # MP3'e dönüştür
                        convert_cmd = [
                            ffmpeg_cmd, "-i", temp_file, "-codec:a", "libmp3lame", 
                            "-q:a", "0", "-b:a", bitrate, "-y", output_file
                        ]
                    else:  # m4a
                        if quality == "high":
                            bitrate = "256k"
                        elif quality == "medium":
                            bitrate = "192k"
                        else:  # low
                            bitrate = "128k"
                            
                        # M4A (AAC)'ye dönüştür
                        convert_cmd = [
                            ffmpeg_cmd, "-i", temp_file, "-codec:a", "aac", 
                            "-b:a", bitrate, "-y", output_file
                        ]
                    
                    # FFmpeg ile dönüştür
                    try:
                        subprocess.run(
                            convert_cmd,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            check=True,
                            creationflags=subprocess.CREATE_NO_WINDOW
                        )
                    except subprocess.CalledProcessError as e:
                        logger.error(f"FFmpeg dönüştürme hatası: {e.stderr.decode() if e.stderr else ''}")
                        if self.status_callback_fn:
                            self.status_callback_fn(_("audio_download_failed"), "error")
                        return False
                else:
                    # FFmpeg yoksa, sadece dosyayı kopyala/yeniden adlandır
                    shutil.copy2(temp_file, output_file)
                
                # Geçici dosyayı sil
                try:
                    os.unlink(temp_file)
                except:
                    pass
                
                # Kapak resmi ekle
                if include_thumbnail:
                    self.add_thumbnail_to_audio(output_file, yt)
                
                if self.status_callback_fn:
                    self.status_callback_fn(_("audio_download_success"), "success")
                
                return True
                
            except Exception as e:
                error_msg = str(e)
                logger.error(f"Ses indirme hatası: {error_msg}")
                
                if "429" in error_msg or "too many requests" in error_msg.lower():
                    # YouTube hız sınırlaması, daha uzun bekle
                    wait_time = self.RETRY_DELAY * (retry_count + 2)
                    logger.warning(f"YouTube hız sınırlaması, {wait_time} saniye bekleniyor...")
                    
                    if self.status_callback_fn:
                        self.status_callback_fn(f"YouTube hız sınırlaması, yeniden deneniyor ({retry_count+1}/{max_retries})...", "warning")
                        
                    time.sleep(wait_time)
                else:
                    # Diğer hatalar için kısa bekle
                    time.sleep(self.RETRY_DELAY)
                    
                    if self.status_callback_fn:
                        self.status_callback_fn(f"İndirme hatası, yeniden deneniyor ({retry_count+1}/{max_retries})...", "warning")
                
                # Önbelleği temizle ve yeniden dene
                self.clear_cache()
                retry_count += 1
                continue
        
        # Tüm denemeler başarısız oldu
        if self.status_callback_fn:
            self.status_callback_fn(_("audio_download_failed"), "error")
            
        return False
    
    def download_playlist(self, playlist_url: str, download_path: str, quality: str) -> Tuple[int, int]:
        """Bir YouTube oynatma listesindeki tüm videoları indirir.
        
        Args:
            playlist_url: İndirilecek oynatma listesinin URL'si
            download_path: İndirme klasörü
            quality: Video kalitesi
            
        Returns:
            Tuple[int, int]: Başarılı ve başarısız indirme sayıları
        """
        # Başlangıçta önbelleği temizle
        self.clear_cache()
        
        # Yeniden deneme sayısı
        retry_count = 0
        max_playlist_retries = 2
        
        while retry_count <= max_playlist_retries:
            try:
                # Yeniden deneme bilgisi
                if retry_count > 0:
                    if self.status_callback_fn:
                        self.status_callback_fn(f"Playlist yeniden deneniyor ({retry_count}/{max_playlist_retries})...", "warning")
                    logger.info(f"Playlist yeniden deneniyor ({retry_count}/{max_playlist_retries}): {playlist_url}")
                    time.sleep(self.RETRY_DELAY * 2)  # Playlist için daha uzun bekle
                    self.clear_cache()  # Önbelleği temizle
                
                # Playlist bilgilerini al
                if self.status_callback_fn:
                    self.status_callback_fn("Playlist bilgileri alınıyor...", "info")
                
                # Playlist nesnesini oluştur
                try:
                    playlist = Playlist(playlist_url)
                    
                    # Video URL'lerini güvenli bir şekilde al
                    try:
                        # Önce video_urls'yi listeye dönüştür
                        video_urls = []
                        for url in playlist.video_urls:
                            video_urls.append(url)
                        total_videos = len(video_urls)
                    except Exception as e:
                        logger.error(f"Video URL'leri alınırken hata: {str(e)}")
                        raise
                    
                    # Playlist adını al
                    try:
                        playlist_title = playlist.title
                    except:
                        playlist_title = "Playlist"
                except Exception as e:
                    logger.error(f"Playlist yükleme hatası: {str(e)}")
                    retry_count += 1
                    if retry_count > max_playlist_retries:
                        if self.status_callback_fn:
                            self.status_callback_fn(f"Playlist yüklenemedi: {str(e)}", "error")
                        return 0, 0
                    continue
                
                if total_videos == 0:
                    if self.status_callback_fn:
                        self.status_callback_fn("Playlist boş veya erişilemez.", "error")
                        
                    logger.warning(f"Boş playlist: {playlist_url}")
                    return 0, 0
                    
                logger.info(f"Playlist bulundu: {playlist_title} - {total_videos} video")
                
                if self.status_callback_fn:
                    self.status_callback_fn(f"Playlist: {playlist_title} - {total_videos} video bulundu", "info")
                
                # İndirme işlemi
                success_count = 0
                failed_count = 0
                
                # Video URL'lerini karıştır (bağlantı sorunlarını azaltmak için)
                # Bu, aynı sunucuya ardışık istekleri azaltır
                video_urls_shuffled = list(video_urls)  # list() ile listeye dönüştür
                random.shuffle(video_urls_shuffled)
                
                for idx, video_url in enumerate(video_urls_shuffled):
                    # İlerleme bilgisi
                    if self.status_callback_fn:
                        self.status_callback_fn(f"Video {idx + 1}/{total_videos} indiriliyor...", "info")
                        
                    logger.info(f"Playlist video indiriliyor [{idx + 1}/{total_videos}]: {video_url}")
                    
                    # Her 5 videodan sonra önbelleği temizle
                    if idx > 0 and idx % 5 == 0:
                        self.clear_cache()
                        
                    # Videoyu indir
                    result = self.download_video(video_url, download_path, quality)
                    if result:
                        success_count += 1
                    else:
                        failed_count += 1
                        
                    # Her 10 videodan sonra kısa bir bekleme (hız sınırlamasını önlemek için)
                    if idx > 0 and idx % 10 == 0 and idx < total_videos - 1:
                        if self.status_callback_fn:
                            self.status_callback_fn("YouTube hız sınırlamasını önlemek için kısa bir bekleme...", "info")
                        time.sleep(2)  # 2 saniye bekle
                
                # Sonuç bilgisi
                if self.status_callback_fn:
                    if failed_count > 0:
                        self.status_callback_fn(
                            f"{success_count} video başarıyla indirildi, {failed_count} video başarısız oldu.", 
                            "warning"
                        )
                    else:
                        self.status_callback_fn(
                            f"Tüm videolar başarıyla indirildi ({total_videos} video).", 
                            "success"
                        )
                        
                logger.info(f"Playlist indirme tamamlandı: {success_count} başarılı, {failed_count} başarısız")
                return success_count, failed_count
                
            except Exception as e:
                error_msg = str(e)
                
                if self.status_callback_fn:
                    self.status_callback_fn(f"Playlist hatası: {error_msg}", "error")
                    
                logger.error(f"Playlist indirme hatası: {error_msg}")
                
                retry_count += 1
                if retry_count <= max_playlist_retries:
                    # Yeniden dene
                    self.clear_cache()
                    time.sleep(self.RETRY_DELAY * 2)
                    continue
                else:
                    # Tüm denemeler başarısız
                    return 0, 0
