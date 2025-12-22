"""
YTDx - GUI Module
PyQt6 tabanlı kullanıcı arayüzü
"""

import os
import sys
import logging
from typing import Optional, List, Dict, Any
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QFileDialog, QComboBox,
    QProgressBar, QTabWidget, QGroupBox, QMessageBox, QTextEdit,
    QSizePolicy, QDialog, QDialogButtonBox, QCheckBox, QMenu,
    QGridLayout, QSpacerItem, QStatusBar, QFrame, QRadioButton
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QUrl, QSize, QEvent
from PyQt6.QtGui import QIcon, QPixmap, QDesktopServices, QFont, QAction

# Dil modülünü içe aktar
from src.language import get_language_manager, _

# Özelleştirilmiş widget'ları içe aktar
from src.custom_widgets import TranslatedLineEdit, TranslatedTextEdit

# Loglama ayarları
logger = logging.getLogger("YTDx.GUI")

class DownloadThread(QThread):
    """İndirme işlemini arka planda yürüten thread sınıfı."""
    
    # Sinyaller
    progress_signal = pyqtSignal(float, int, int, str)  # ilerleme, indirilen, toplam, tür (video/ses)
    status_signal = pyqtSignal(str, str)  # mesaj, tür (info, warning, error, success)
    finished_signal = pyqtSignal(bool, int, int)  # başarılı mı, başarılı sayısı, başarısız sayısı
    
    def __init__(self, downloader, video_url=None, playlist_url=None, download_path=None, quality=None, 
                 audio_only=False, audio_format="mp3", audio_quality="high", include_thumbnail=True, parent=None):
        """Thread başlatıcısı."""
        super().__init__(parent)
        self.downloader = downloader
        self.video_url = video_url
        self.playlist_url = playlist_url
        self.download_path = download_path
        self.quality = quality
        self.audio_only = audio_only
        self.audio_format = audio_format
        self.audio_quality = audio_quality
        self.include_thumbnail = include_thumbnail
        self.parent = parent  # Ana pencere referansı
        
        # Callback fonksiyonlarını ayarla
        self.downloader.set_callbacks(
            progress_callback=self.update_progress,
            status_callback=self.update_status,
            ask_overwrite_callback=self.ask_overwrite_callback
        )
        
    def ask_overwrite_callback(self, filename: str) -> bool:
        """Dosya üzerine yazma izni soran callback fonksiyonu.
        
        Args:
            filename: Üzerine yazılması istenen dosyanın adı
            
        Returns:
            bool: Kullanıcı üzerine yazmayı kabul ederse True, aksi halde False
        """
        # Ana pencerenin ask_overwrite_callback metodunu çağır
        if self.parent and hasattr(self.parent, 'ask_overwrite_callback'):
            return self.parent.ask_overwrite_callback(filename)
        return False
        
    def run(self):
        """Thread çalıştırma metodu."""
        try:
            if self.playlist_url:
                if self.audio_only:
                    # Playlist'ten müzik indirme
                    success_count, failed_count = self.downloader.download_audio_playlist(
                        self.playlist_url, 
                        self.download_path, 
                        self.audio_quality,
                        self.audio_format,
                        self.include_thumbnail
                    )
                    self.finished_signal.emit(failed_count == 0, success_count, failed_count)
                else:
                    # Normal video playlist indirme
                    success_count, failed_count = self.downloader.download_playlist(
                        self.playlist_url, 
                        self.download_path, 
                        self.quality
                    )
                    self.finished_signal.emit(failed_count == 0, success_count, failed_count)
            elif self.video_url:
                if self.audio_only:
                    # Sadece ses indirme
                    result = self.downloader.download_audio(
                        self.video_url, 
                        self.download_path, 
                        self.audio_quality,
                        self.audio_format,
                        self.include_thumbnail
                    )
                    self.finished_signal.emit(result, 1 if result else 0, 0 if result else 1)
                else:
                    # Tek video indirme
                    result = self.downloader.download_video(
                        self.video_url, 
                        self.download_path, 
                        self.quality
                    )
                    self.finished_signal.emit(result, 1 if result else 0, 0 if result else 1)
            else:
                self.status_signal.emit(_("missing_url"), "error")
                self.finished_signal.emit(False, 0, 0)
        except Exception as e:
            logger.error(f"İndirme thread hatası: {str(e)}")
            self.status_signal.emit(f"İndirme hatası: {str(e)}", "error")
            self.finished_signal.emit(False, 0, 1)
            
    def update_progress(self, progress: float, bytes_downloaded: int, total_size: int, stream_type: str):
        """İlerleme durumunu günceller.
        
        Args:
            progress: İlerleme yüzdesi (0-1 arası)
            bytes_downloaded: İndirilen bayt sayısı
            total_size: Toplam bayt sayısı
            stream_type: Akış türü ("video" veya "ses")
        """
        self.progress_signal.emit(progress, bytes_downloaded, total_size, stream_type)
        
    def update_status(self, message: str, status_type: str):
        """Durum mesajını günceller."""
        self.status_signal.emit(message, status_type)


class MainWindow(QMainWindow):
    """Ana uygulama penceresi."""
    
    # Yeniden başlatma kodu
    RESTART_CODE = 42
    
    def __init__(self, lang_manager=None):
        """Ana pencere başlatıcısı.
        
        Args:
            lang_manager: Dil yöneticisi. Eğer None ise, yeni bir tane oluşturulur.
        """
        super().__init__()
        
        # Dil yöneticisini başlat
        if lang_manager is None:
            self.lang_manager = get_language_manager()
            self.lang_manager.load_language_preference()  # Kaydedilmiş dil tercihini yükle
        else:
            self.lang_manager = lang_manager
        
        # Pencere özellikleri
        self.setWindowTitle(_("app_title"))
        self.setMinimumSize(800, 730)
        
        # Durum değişkenleri
        self.download_in_progress = False
        self.download_thread = None
        
        # Arayüzü oluştur
        self._create_ui()
        
        # Downloader modülünü içe aktar
        from src.downloader import Downloader
        self.downloader = Downloader()
        
        # Callback fonksiyonlarını ayarla
        self.downloader.set_callbacks(
            progress_callback=None,  # Thread'ler tarafından yönetilecek
            status_callback=None,    # Thread'ler tarafından yönetilecek
            ask_overwrite_callback=self.ask_overwrite_callback
        )
        
        # FFmpeg kontrolü
        self._check_ffmpeg()
        
        logger.info("Ana pencere başlatıldı")
        
    def _create_ui(self):
        """Kullanıcı arayüzünü oluşturur."""
        # Ana widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Ana düzen
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # Başlık
        title_frame = QFrame()
        title_layout = QHBoxLayout(title_frame)
        title_layout.setContentsMargins(0, 0, 0, 0)
        
        title_label = QLabel(_("app_title"))
        title_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title_layout.addWidget(title_label)
        
        # Sekme widget'ı
        self.tab_widget = QTabWidget()
        
        # İndirme sekmesi
        download_tab = QWidget()
        download_layout = QVBoxLayout(download_tab)
        
        # Müzik indirme sekmesi
        audio_tab = QWidget()
        audio_tab_layout = QVBoxLayout(audio_tab)
        
        # URL giriş alanı (müzik)
        audio_url_group = QGroupBox(_('video_url'))
        audio_url_layout = QVBoxLayout(audio_url_group)
        
        self.audio_url_input = TranslatedLineEdit()
        self.audio_url_input.setPlaceholderText(_("video_url_placeholder"))
        audio_url_layout.addWidget(self.audio_url_input)
        
        # URL türü seçimi (video veya playlist)
        self.audio_url_type_group = QGroupBox(_("url_type"))
        audio_url_type_layout = QHBoxLayout(self.audio_url_type_group)
        
        self.audio_video_radio = QRadioButton(_("single_video"))
        self.audio_playlist_radio = QRadioButton(_("playlist_name"))
        self.audio_video_radio.setChecked(True)  # Varsayılan olarak tekli video
        
        audio_url_type_layout.addWidget(self.audio_video_radio)
        audio_url_type_layout.addWidget(self.audio_playlist_radio)
        
        audio_url_layout.addWidget(self.audio_url_type_group)
        
        audio_tab_layout.addWidget(audio_url_group)
        
        # Müzik indirme ayarları
        audio_settings_group = QGroupBox(_('download_settings'))
        audio_settings_layout = QGridLayout(audio_settings_group)
        
        # İndirme konumu (müzik)
        self.audio_location_label = QLabel(f"{_('download_location')}:")
        self.audio_location_input = TranslatedLineEdit()
        self.audio_location_input.setReadOnly(True)
        self.audio_path_button = QPushButton(_('select_folder'))
        self.audio_path_button.clicked.connect(self.select_audio_download_folder)
        
        audio_settings_layout.addWidget(self.audio_location_label, 0, 0)
        audio_settings_layout.addWidget(self.audio_location_input, 0, 1)
        audio_settings_layout.addWidget(self.audio_path_button, 0, 2)
        
        # Ses kalitesi
        audio_quality_label = QLabel(f"{_('audio_quality')}:")
        self.audio_quality_combo = QComboBox()
        self.audio_quality_combo.addItems([_('high_quality'), _('medium_quality'), _('low_quality')])
        
        audio_settings_layout.addWidget(audio_quality_label, 1, 0)
        audio_settings_layout.addWidget(self.audio_quality_combo, 1, 1, 1, 2)
        
        # Ses formatı
        audio_format_label = QLabel(f"{_('audio_format')}:")
        self.audio_format_combo = QComboBox()
        self.audio_format_combo.addItems([_('mp3_format'), _('m4a_format')])
        
        audio_settings_layout.addWidget(audio_format_label, 2, 0)
        audio_settings_layout.addWidget(self.audio_format_combo, 2, 1, 1, 2)
        
        # Kapak resmi ekleme seçeneği
        self.include_thumbnail_check = QCheckBox(_('include_thumbnail'))
        self.include_thumbnail_check.setChecked(True)
        
        audio_settings_layout.addWidget(self.include_thumbnail_check, 3, 0, 1, 3)
        
        audio_tab_layout.addWidget(audio_settings_group)
        
        # İndirme butonu (müzik)
        self.audio_download_button = QPushButton(_('start_download'))
        self.audio_download_button.setMinimumHeight(40)
        self.audio_download_button.clicked.connect(self.start_audio_download)
        audio_tab_layout.addWidget(self.audio_download_button)
        
        # Durum bilgisi (müzik)
        audio_status_group = QGroupBox(_('download_status'))
        audio_status_layout = QVBoxLayout(audio_status_group)
        
        self.audio_status_label = QLabel(_('ready'))
        self.audio_status_label.setStyleSheet("color: blue;")
        audio_status_layout.addWidget(self.audio_status_label)
        
        self.audio_progress_bar = QProgressBar()
        self.audio_progress_bar.setRange(0, 100)
        self.audio_progress_bar.setValue(0)
        audio_status_layout.addWidget(self.audio_progress_bar)
        
        audio_tab_layout.addWidget(audio_status_group)
        
        # URL giriş alanı
        url_group = QGroupBox(_("video_url"))
        url_layout = QVBoxLayout(url_group)
        
        # Video URL
        video_layout = QHBoxLayout()
        self.video_url_label = QLabel(f"{_('video_url')}:")
        self.video_url_input = TranslatedLineEdit()
        self.video_url_input.setPlaceholderText(_('video_url_placeholder'))
        video_layout.addWidget(self.video_url_label)
        video_layout.addWidget(self.video_url_input)
        url_layout.addLayout(video_layout)
        
        # Playlist URL
        playlist_layout = QHBoxLayout()
        self.playlist_url_label = QLabel(f"{_('playlist_url')}:")
        self.playlist_url_input = TranslatedLineEdit()
        self.playlist_url_input.setPlaceholderText(_('playlist_url_placeholder'))
        playlist_layout.addWidget(self.playlist_url_label)
        playlist_layout.addWidget(self.playlist_url_input)
        url_layout.addLayout(playlist_layout)
        
        download_layout.addWidget(url_group)
        
        # İndirme ayarları
        settings_group = QGroupBox(_("download_settings"))
        settings_layout = QGridLayout(settings_group)
        
        # İndirme konumu
        self.download_location_label = QLabel(f"{_('download_location')}:")
        self.download_location_input = TranslatedLineEdit()
        self.download_location_input.setReadOnly(True)
        self.path_button = QPushButton(_("select_folder"))
        self.path_button.clicked.connect(self.select_download_folder)
        
        settings_layout.addWidget(self.download_location_label, 0, 0)
        settings_layout.addWidget(self.download_location_input, 0, 1)
        settings_layout.addWidget(self.path_button, 0, 2)
        
        # Video kalitesi
        quality_label = QLabel(f"{_('video_quality')}:")
        self.quality_combo = QComboBox()
        self.quality_combo.addItems([_("auto"), "144p", "240p", "360p", "480p", "720p", "1080p", "1440p", "2160p", "4320p"])
        
        settings_layout.addWidget(quality_label, 1, 0)
        settings_layout.addWidget(self.quality_combo, 1, 1, 1, 2)
        
        download_layout.addWidget(settings_group)
        
        # İndirme butonu
        self.download_button = QPushButton(_("start_download"))
        self.download_button.setMinimumHeight(40)
        self.download_button.clicked.connect(self.start_download)
        download_layout.addWidget(self.download_button)
        
        # İlerleme bilgisi
        progress_group = QGroupBox(_("download_status"))
        progress_layout = QVBoxLayout(progress_group)
        
        self.status_label = QLabel(_("ready"))
        progress_layout.addWidget(self.status_label)
        
        self.progress_info_label = QLabel("")
        progress_layout.addWidget(self.progress_info_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        progress_layout.addWidget(self.progress_bar)
        
        download_layout.addWidget(progress_group)
        
        # Boşluk ekle
        download_layout.addStretch()
        
        # Ayarlar sekmesi
        settings_tab = QWidget()
        settings_tab_layout = QVBoxLayout(settings_tab)
        
        # FFmpeg ayarları
        ffmpeg_group = QGroupBox(_("ffmpeg_settings"))
        ffmpeg_layout = QVBoxLayout(ffmpeg_group)
        
        self.ffmpeg_status_label = QLabel(_("ffmpeg_status").format(_("ready")))
        ffmpeg_layout.addWidget(self.ffmpeg_status_label)
        
        ffmpeg_path_layout = QHBoxLayout()
        self.ffmpeg_input = TranslatedLineEdit()
        self.ffmpeg_input.setReadOnly(True)
        self.ffmpeg_input.setPlaceholderText("FFmpeg")
        
        self.ffmpeg_path_button = QPushButton(_("ffmpeg_select"))
        self.ffmpeg_path_button.clicked.connect(self.select_ffmpeg_path)
        
        ffmpeg_path_layout.addWidget(self.ffmpeg_input)
        ffmpeg_path_layout.addWidget(self.ffmpeg_path_button)
        
        ffmpeg_layout.addLayout(ffmpeg_path_layout)
        
        ffmpeg_info_label = QLabel(_("ffmpeg_note"))
        ffmpeg_layout.addWidget(ffmpeg_info_label)
        
        settings_tab_layout.addWidget(ffmpeg_group)
        
        # Önbellek ayarları
        cache_group = QGroupBox(_("cache_settings"))
        cache_layout = QVBoxLayout(cache_group)
        
        cache_info_label = QLabel(_("cache_info"))
        cache_layout.addWidget(cache_info_label)
        
        self.clear_cache_button = QPushButton(_("clear_cache"))
        self.clear_cache_button.clicked.connect(self.clear_cache)
        cache_layout.addWidget(self.clear_cache_button)
        
        settings_tab_layout.addWidget(cache_group)
        
        # Dil ayarları
        language_group = QGroupBox(_("language_settings"))
        language_layout = QVBoxLayout(language_group)
        
        language_label = QLabel(_("select_language"))
        language_layout.addWidget(language_label)
        
        self.language_combo = QComboBox()
        # Desteklenen dilleri ekle
        supported_languages = self.lang_manager.get_supported_languages()
        for code, name in supported_languages.items():
            self.language_combo.addItem(name, code)
        
        # Mevcut dili seç
        current_lang = self.lang_manager.current_language
        for i in range(self.language_combo.count()):
            if self.language_combo.itemData(i) == current_lang:
                self.language_combo.setCurrentIndex(i)
                break
        
        self.language_combo.currentIndexChanged.connect(self.change_language)
        language_layout.addWidget(self.language_combo)
        
        language_note = QLabel(_("restart_required"))
        language_layout.addWidget(language_note)
        
        settings_tab_layout.addWidget(language_group)
        
        # Tema ayarları
        theme_group = QGroupBox(_("theme_settings"))
        theme_layout = QVBoxLayout(theme_group)
        
        theme_label = QLabel(_("select_theme"))
        theme_layout.addWidget(theme_label)
        
        self.theme_combo = QComboBox()
        self.theme_combo.addItems([_("light_theme"), _("dark_theme")])
        
        # Mevcut temayı seç
        current_theme = self.lang_manager.current_theme
        self.theme_combo.setCurrentIndex(0 if current_theme == "light" else 1)
        
        self.theme_combo.currentIndexChanged.connect(self.change_theme)
        theme_layout.addWidget(self.theme_combo)
        
        theme_note = QLabel(_("restart_required"))
        theme_layout.addWidget(theme_note)
        
        settings_tab_layout.addWidget(theme_group)
        
        # Hakkında bilgisi
        about_group = QGroupBox(_("about"))
        about_layout = QVBoxLayout(about_group)
        
        about_text = QLabel(_("about_text"))
        about_layout.addWidget(about_text)
        
        settings_tab_layout.addWidget(about_group)
        
        # Boşluk ekle
        settings_tab_layout.addStretch(1)
        
        # Sekmeleri ekle
        self.tab_widget.addTab(download_tab, _("download_status"))
        self.tab_widget.addTab(audio_tab, _("audio_download_tab"))
        self.tab_widget.addTab(settings_tab, _("settings"))
        
        main_layout.addWidget(title_frame)
        main_layout.addWidget(self.tab_widget)
        
        # Durum çubuğu
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage(_("ready"))
        
    def ask_overwrite_callback(self, filename: str) -> bool:
        """Dosya üzerine yazma izni soran callback fonksiyonu.
        
        Args:
            filename: Üzerine yazılması istenen dosyanın adı
            
        Returns:
            bool: Kullanıcı üzerine yazmayı kabul ederse True, aksi halde False
        """
        # UI işlemleri ana thread'de yapılmalı
        response = [QMessageBox.StandardButton.No]  # Varsayılan değer
        
        def show_dialog():
            response[0] = QMessageBox.question(
                self,
                _('audio_file_exists'),
                _('audio_file_exists_question').format(filename),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
        
        # Eğer bu çağrı ana thread'den gelmiyorsa, invokeMethod kullan
        if QThread.currentThread() != self.thread():
            QMetaObject.invokeMethod(
                self, 
                "ask_overwrite_callback", 
                Qt.ConnectionType.BlockingQueuedConnection,
                Q_RETURN_ARG(bool),
                Q_ARG(str, filename)
            )
            return response[0] == QMessageBox.StandardButton.Yes
            
        # Ana thread'deyiz, doğrudan göster
        show_dialog()
        return response[0] == QMessageBox.StandardButton.Yes
    
    def _check_ffmpeg(self):
        """FFmpeg'in var olup olmadığını kontrol eder."""
        if self.downloader.ffmpeg.is_available:
            self.ffmpeg_status_label.setText(_('ffmpeg_status').format(_('ffmpeg_available')))
            self.ffmpeg_status_label.setStyleSheet("color: green")
        else:
            self.ffmpeg_status_label.setText(_('ffmpeg_status').format(_('ffmpeg_not_available')))
            self.ffmpeg_status_label.setStyleSheet("color: red")
            
            # Kullanıcıya uyarı göster
            QMessageBox.warning(
                self,
                _("ffmpeg_not_found"),
                _("ffmpeg_required"),
                QMessageBox.StandardButton.Ok
            )
            
            # Ayarlar sekmesine geç
            self.tab_widget.setCurrentIndex(2)
    
    def select_download_folder(self):
        """İndirme klasörünü seçer."""
        folder = QFileDialog.getExistingDirectory(
            self,
            _("select_folder"),
            os.path.expanduser("~")
        )
        
        if folder:
            self.download_location_input.setText(folder)
            logger.info(f"İndirme klasörü seçildi: {folder}")
    
    def select_audio_download_folder(self):
        """Müzik indirme klasörünü seçer."""
        folder = QFileDialog.getExistingDirectory(
            self,
            _("select_folder"),
            os.path.expanduser("~")
        )
        
        if folder:
            self.audio_location_input.setText(folder)
            logger.info(f"Müzik indirme klasörü seçildi: {folder}")
    
    def select_ffmpeg_path(self):
        """FFmpeg yolunu seçer."""
        # Çeviri fonksiyonunu yerel olarak al
        from src.language import _ as translate
        
        # Önce klasör seçimi dene
        folder = QFileDialog.getExistingDirectory(
            self,
            translate("ffmpeg_select_folder"),
            os.path.expanduser("~")
        )
        
        if folder:
            # FFmpeg yolunu ayarla
            if self.downloader.ffmpeg.set_custom_path(folder):
                self.ffmpeg_input.setText(folder)
                self.ffmpeg_status_label.setText(_("ffmpeg_status").format(_("ffmpeg_available")))
                self.ffmpeg_status_label.setStyleSheet("color: green")
                
                QMessageBox.information(
                    self,
                    _("ffmpeg_found"),
                    _("ffmpeg_setup_success"),
                    QMessageBox.StandardButton.Ok
                )
            else:
                # Dosya seçimi dene
                from src.language import _ as translate
                file_path, unused_filter = QFileDialog.getOpenFileName(
                    self,
                    translate("ffmpeg_select_exe"),
                    folder,
                    translate("executable_files")
                )
                
                if file_path:
                    if self.downloader.ffmpeg.set_custom_path(file_path):
                        self.ffmpeg_input.setText(file_path)
                        from src.language import _ as translate
                        self.ffmpeg_status_label.setText(translate("ffmpeg_status").format(translate("ffmpeg_available")))
                        self.ffmpeg_status_label.setStyleSheet("color: green")
                        
                        QMessageBox.information(
                            self,
                            translate("ffmpeg_found"),
                            translate("ffmpeg_setup_success"),
                            QMessageBox.StandardButton.Ok
                        )
                    else:
                        from src.language import _ as translate
                        QMessageBox.warning(
                            self,
                            translate("ffmpeg_invalid"),
                            translate("ffmpeg_invalid_message"),
                            QMessageBox.StandardButton.Ok
                        )
        
    def start_download(self):
        """İndirme işlemini başlatır."""
        # İndirme zaten devam ediyorsa, uyarı ver
        if self.download_in_progress:
            QMessageBox.warning(
                self,
                _("error"),
                _("download_in_progress_message"),
                QMessageBox.StandardButton.Ok
            )
            return
            
        # URL'leri al
        video_url = self.video_url_input.text().strip()
        playlist_url = self.playlist_url_input.text().strip()
        download_path = self.download_location_input.text().strip()
        quality = self.quality_combo.currentText()
        
        if not download_path:
            QMessageBox.warning(
                self,
                _("error"),
                _("missing_download_location"),
                QMessageBox.StandardButton.Ok
            )
            return
            
        if not (video_url or playlist_url):
            QMessageBox.warning(
                self,
                _("error"),
                _("missing_url"),
                QMessageBox.StandardButton.Ok
            )
            return
            
        # İndirme işlemini başlat
        self.download_in_progress = True
        self.status_label.setText(_("starting_download"))
        self.status_label.setStyleSheet("color: blue")
        self.progress_bar.setValue(0)
        
        # İndirme thread'ini başlat
        self.download_thread = DownloadThread(
            downloader=self.downloader,
            video_url=video_url if video_url else None,
            playlist_url=playlist_url if playlist_url else None,
            download_path=download_path,
            quality=quality,
            parent=self  # Ana pencereyi parent olarak veriyoruz
        )
        
        # Sinyalleri bağla
        self.download_thread.progress_signal.connect(self.update_progress)
        self.download_thread.status_signal.connect(self.update_status)
        self.download_thread.finished_signal.connect(self.download_finished)
        
        # Thread'i başlat
        self.download_thread.start()
        
        # Durum çubuğunu güncelle
        self.status_bar.showMessage(_("starting_download"))
    
    def start_audio_download(self):
        """Çevrimiçi videodan sadece ses indirme işlemini başlatır."""
        # İndirme zaten devam ediyorsa, uyarı ver
        if self.download_in_progress:
            QMessageBox.warning(
                self,
                _("error"),
                _("download_in_progress_message"),
                QMessageBox.StandardButton.Ok
            )
            return
            
        # URL'yi ve diğer ayarları al
        url = self.audio_url_input.text().strip()
        download_path = self.audio_location_input.text().strip()
        
        # Ses kalitesini belirle
        audio_quality_text = self.audio_quality_combo.currentText()
        if audio_quality_text == _("high_quality"):
            audio_quality = "high"
        elif audio_quality_text == _("low_quality"):
            audio_quality = "low"
        else:
            audio_quality = "medium"
        
        # Ses formatını belirle
        audio_format_text = self.audio_format_combo.currentText()
        if audio_format_text == _("mp3_format"):
            audio_format = "mp3"
        else:
            audio_format = "m4a"
        
        # Kapak resmi eklensin mi?
        include_thumbnail = self.include_thumbnail_check.isChecked()
        
        if not download_path:
            QMessageBox.warning(
                self,
                _("error"),
                _("missing_download_location"),
                QMessageBox.StandardButton.Ok
            )
            return
            
        if not url:
            QMessageBox.warning(
                self,
                _("error"),
                _("missing_url"),
                QMessageBox.StandardButton.Ok
            )
            return
            
        # İndirme işlemini başlat
        self.download_in_progress = True
        self.audio_status_label.setText(_("starting_download"))
        self.audio_status_label.setStyleSheet("color: blue")
        self.audio_progress_bar.setValue(0)
        
        # URL türünü belirle (video veya playlist)
        is_playlist = self.audio_playlist_radio.isChecked()
        
        # İndirme thread'ini başlat
        if is_playlist:
            # Playlist indirme
            self.download_thread = DownloadThread(
                downloader=self.downloader,
                video_url=None,
                playlist_url=url,
                download_path=download_path,
                quality=None,  # Video kalitesi kullanılmayacak
                audio_only=True,
                audio_format=audio_format,
                audio_quality=audio_quality,
                include_thumbnail=include_thumbnail,
                parent=self  # Ana pencereyi parent olarak veriyoruz
            )
            logger.info(f"Playlist ses indirme başlatılıyor: {url}")
        else:
            # Tekli video indirme
            self.download_thread = DownloadThread(
                downloader=self.downloader,
                video_url=url,
                playlist_url=None,
                download_path=download_path,
                quality=None,  # Video kalitesi kullanılmayacak
                audio_only=True,
                audio_format=audio_format,
                audio_quality=audio_quality,
                include_thumbnail=include_thumbnail,
                parent=self  # Ana pencereyi parent olarak veriyoruz
            )
            logger.info(f"Tekli video ses indirme başlatılıyor: {url}")
        
        # Sinyalleri bağla
        self.download_thread.progress_signal.connect(self.update_audio_progress)
        self.download_thread.status_signal.connect(self.update_audio_status)
        self.download_thread.finished_signal.connect(self.audio_download_finished)
        
        # Thread'i başlat
        self.download_thread.start()
        
        # Durum çubuğunu güncelle
        self.status_bar.showMessage(_("starting_download"))

    def update_progress(self, progress: float, bytes_downloaded: int, total_size: int, stream_type: str):
        """İlerleme durumunu günceller.
        
        Args:
            progress: İlerleme yüzdesi (0-1 arası)
            bytes_downloaded: İndirilen bayt sayısı
            total_size: Toplam bayt sayısı
            stream_type: Akış türü ("video" veya "ses")
        """
        self.progress_bar.setValue(int(progress * 100))
        
        # Boyut bilgisini göster
        downloaded_mb = bytes_downloaded / 1024 / 1024
        total_mb = total_size / 1024 / 1024
        
        # Boyut formatını ayarla (MB veya GB)
        if total_mb >= 1024:
            downloaded_gb = downloaded_mb / 1024
            total_gb = total_mb / 1024
            size_text = f"{downloaded_gb:.2f}GB / {total_gb:.2f}GB"
        else:
            size_text = f"{downloaded_mb:.1f}MB / {total_mb:.1f}MB"
        
        # Video, ses veya toplam indirme aşamasını belirt
        if stream_type.lower() == "video":
            status_text = _("downloading_video")
        elif stream_type.lower() == "audio":
            status_text = _("downloading_audio")
        elif stream_type.lower() == "toplam":
            status_text = "İndiriliyor"
        else:
            status_text = stream_type.capitalize()
            
        self.progress_info_label.setText(
            f"{status_text}: {size_text} ({progress * 100:.1f}%)"
        )
        
        # İlerleme durumunu güncelle
        self.progress_bar.setValue(int(progress * 100))
        
    def update_status(self, message: str, status_type: str):
        """Durum mesajını günceller."""
        # Dosya zaten var mı kontrolü
        if status_type == "question" and message.startswith("FILE_EXISTS:"):
            # Mesajı ayrıştır
            parts = message.split(":")
            if len(parts) >= 3:
                video_title = parts[1]
                file_path = ":".join(parts[2:])  # Dosya yolunda : karakteri olabilir
                
                # Kullanıcıya sor
                reply = QMessageBox.question(
                    self,
                    _("file_exists"),
                    _("file_exists_message").format(video_title, file_path),
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
                
                # Downloader'a yanıtı gönder
                if hasattr(self.downloader, 'overwrite_response'):
                    delattr(self.downloader, 'overwrite_response')
                    
                self.downloader.overwrite_response = (reply == QMessageBox.StandardButton.Yes)
                
                # Durum mesajını güncelle
                if reply == QMessageBox.StandardButton.Yes:
                    self.status_label.setText(f"{video_title} {_('downloading')}")
                    self.status_label.setStyleSheet("color: blue")
                else:
                    self.status_label.setText(f"{video_title} {_('file_already_exists_skipping')}")
                    self.status_label.setStyleSheet("color: orange")
                
                # Durum çubuğunu güncelle
                self.status_bar.showMessage(self.status_label.text())
                return
        
        # Normal durum mesajı güncelleme
        self.status_label.setText(message)
        
        # Durum tipine göre renk ayarla
        if status_type == "error":
            self.status_label.setStyleSheet("color: red")
        elif status_type == "warning":
            self.status_label.setStyleSheet("color: orange")
        elif status_type == "success":
            self.status_label.setStyleSheet("color: green")
        elif status_type == "info":
            self.status_label.setStyleSheet("color: blue")
        else:
            self.status_label.setStyleSheet("")
            
        # Durum çubuğunu güncelle
        self.status_bar.showMessage(message)
        
    def download_finished(self, success: bool, success_count: int, failed_count: int):
        """İndirme işlemi tamamlandığında çağrılır."""
        self.download_in_progress = False
        self.download_button.setEnabled(True)
        self.download_button.setText(_("start_download"))
        
        if success:
            self.status_label.setText(_("download_complete"))
            self.status_label.setStyleSheet("color: green")
            
            if success_count > 1:
                # Playlist indirme başarılı
                QMessageBox.information(
                    self,
                    _("download_complete"),
                    f"{success_count} {_('videos_downloaded')}",
                    QMessageBox.StandardButton.Ok
                )
        else:
            self.status_label.setText(_("download_failed"))
            self.status_label.setStyleSheet("color: red")
            
            if failed_count > 0 and success_count > 0:
                # Kısmi başarı
                QMessageBox.warning(
                    self,
                    _("download_partial"),
                    f"{success_count} {_('videos_downloaded')}, {failed_count} {_('videos_failed')}",
                    QMessageBox.StandardButton.Ok
                )
    
    def update_audio_progress(self, progress: float, bytes_downloaded: int, total_size: int, stream_type: str):
        """Çevrimiçi videodan ses indirme ilerleme durumunu günceller.
        
        Args:
            progress: İlerleme yüzdesi (0-1 arası)
            bytes_downloaded: İndirilen bayt sayısı
            total_size: Toplam bayt sayısı
            stream_type: Akış türü ("video" veya "ses")
        """
        # Yüzdeyi hesapla (0-100 arası)
        percent = int(progress * 100)
        self.audio_progress_bar.setValue(percent)
        
        # Boyut bilgisini göster
        if total_size > 0:
            # MB cinsinden boyutları hesapla
            downloaded_mb = bytes_downloaded / (1024 * 1024)
            total_mb = total_size / (1024 * 1024)
            
        
            # Durum bilgisini güncelle
            if stream_type.lower() == "audio":
                status_text = f"{_('downloading_audio')} {percent}% ({downloaded_mb:.1f} MB / {total_mb:.1f} MB)"
                self.audio_status_label.setText(status_text)
                self.audio_status_label.setStyleSheet("color: blue")
    
    def update_audio_status(self, message: str, status_type: str):
        """Çevrimiçi videodan ses indirme durum mesajını günceller."""
        # Dosya zaten var mı kontrolü (video indirmedeki gibi)
        if status_type == "question" and message.startswith("FILE_EXISTS:"):
            # Mesajı ayrıştır
            parts = message.split(":")
            if len(parts) >= 3:
                video_title = parts[1]
                file_path = ":".join(parts[2:])  # Dosya yolunda : karakteri olabilir
                
                # Kullanıcıya sor
                reply = QMessageBox.question(
                    self,
                    _("file_exists"),
                    _("file_exists_message").format(video_title, file_path),
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
                
                # Downloader'a yanıtı gönder
                if hasattr(self.downloader, 'overwrite_response'):
                    delattr(self.downloader, 'overwrite_response')
                    
                self.downloader.overwrite_response = (reply == QMessageBox.StandardButton.Yes)
                
                # Durum mesajını güncelle
                if reply == QMessageBox.StandardButton.Yes:
                    self.audio_status_label.setText(f"{video_title} {_('downloading')}")
                    self.audio_status_label.setStyleSheet("color: blue")
                else:
                    self.audio_status_label.setText(f"{video_title} {_('file_already_exists_skipping')}")
                    self.audio_status_label.setStyleSheet("color: orange")
                
                # Durum çubuğunu güncelle
                self.status_bar.showMessage(self.audio_status_label.text())
                return
        
        # Normal durum mesajı güncelleme
        self.audio_status_label.setText(message)
        
        # Durum türüne göre renk ayarla
        if status_type == "error":
            self.audio_status_label.setStyleSheet("color: red")
        elif status_type == "warning":
            self.audio_status_label.setStyleSheet("color: orange")
        elif status_type == "success":
            self.audio_status_label.setStyleSheet("color: green")
        else:  # info
            self.audio_status_label.setStyleSheet("color: blue")
        
        # Durum çubuğunu da güncelle
        self.status_bar.showMessage(message)
    
    def audio_download_finished(self, success: bool, success_count: int, failed_count: int):
        """Çevrimiçi videodan ses indirme işlemi tamamlandığında çağrılır."""
        self.download_in_progress = False
        self.audio_download_button.setEnabled(True)
        self.audio_download_button.setText(_("start_download"))
        
        if success:
            self.audio_status_label.setText(_("audio_download_success"))
            self.audio_status_label.setStyleSheet("color: green")
            
            QMessageBox.information(
                self,
                _("download_complete"),
                _("audio_download_success"),
                QMessageBox.StandardButton.Ok
            )
        else:
            self.audio_status_label.setText(_("audio_download_failed"))
            self.audio_status_label.setStyleSheet("color: red")
            
            QMessageBox.warning(
                self,
                _("download_failed"),
                _("audio_download_failed"),
                QMessageBox.StandardButton.Ok
            )
                
        logger.info(f"Download completed: {success_count} successful, {failed_count} failed")
        
    def change_language(self, index):
        """Dili değiştirir.
        
        Args:
            index: Dil seçeneğinin indeksi
        """
        # Seçilen dil kodunu al
        language_code = self.language_combo.itemData(index)
        
        if not language_code or language_code == self.lang_manager.current_language:
            return
            
        # Dili değiştir
        if self.lang_manager.load_language(language_code):
            # Dil tercihini kaydet
            self.lang_manager.save_language_preference(language_code)
            
            # Kullanıcıya bilgi ver ve yeniden başlatma seçeneği sun
            restart_msg = QMessageBox(
                QMessageBox.Icon.Information,
                _("language"),
                _("restart_required"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                self
            )
            restart_msg.setDefaultButton(QMessageBox.StandardButton.Yes)
            restart_msg.button(QMessageBox.StandardButton.Yes).setText(_("restart_now"))
            restart_msg.button(QMessageBox.StandardButton.No).setText(_("restart_later"))
            
            if restart_msg.exec() == QMessageBox.StandardButton.Yes:
                # Uygulamayı yeniden başlat
                QApplication.quit()
                QApplication.exit(self.RESTART_CODE)
            
            # Arayüzü güncelle
            self._update_ui_language()
            
            logger.info(f"Dil değiştirildi: {language_code}")
        else:
            # Hata durumunda
            QMessageBox.warning(
                self,
                _("language"),
                _("language_error").format(language_code),
                QMessageBox.StandardButton.Ok
            )
            logger.error(f"Dil yüklenirken hata oluştu: {language_code}")
            
    def change_theme(self, index):
        """Temayı değiştirir.
        
        Args:
            index: Tema seçeneğinin indeksi
        """
        selected_theme = "light" if index == 0 else "dark"
        if selected_theme == self.lang_manager.current_theme:
            return
            
        # Temayı kaydet
        self.lang_manager.save_theme_preference(selected_theme)
        
        # Kullanıcıya bilgi ver ve yeniden başlatma seçeneği sun
        restart_msg = QMessageBox(
            QMessageBox.Icon.Information,
            _("theme_settings"),
            _("restart_required"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            self
        )
        restart_msg.setDefaultButton(QMessageBox.StandardButton.Yes)
        restart_msg.button(QMessageBox.StandardButton.Yes).setText(_("restart_now"))
        restart_msg.button(QMessageBox.StandardButton.No).setText(_("restart_later"))
        
        if restart_msg.exec() == QMessageBox.StandardButton.Yes:
            # Uygulamayı yeniden başlat
            QApplication.quit()
            QApplication.exit(self.RESTART_CODE)
            
    def _update_ui_language(self):
        """Arayüz dilini günceller."""
        # Pencere başlığı
        self.setWindowTitle(_("app_title"))
        
        # Ana başlık
        for i in range(self.tab_widget.count()):
            widget = self.tab_widget.widget(i)
            if hasattr(widget, 'layout') and widget.layout() is not None:
                for j in range(widget.layout().count()):
                    item = widget.layout().itemAt(j)
                    if item and item.widget() and isinstance(item.widget(), QLabel) and item.widget().font().pointSize() > 14:
                        item.widget().setText(_("app_title"))
        
        # Sekme başlıkları
        self.tab_widget.setTabText(0, _("download_status"))
        self.tab_widget.setTabText(1, _("settings"))
        
        # İndirme sekmesi
        download_tab = self.tab_widget.widget(0)
        if download_tab:
            # URL grupları
            for group in download_tab.findChildren(QGroupBox):
                if "URL" in group.title():
                    group.setTitle(_("video_url"))
                elif "Ayarlar" in group.title() or "Settings" in group.title():
                    group.setTitle(_("download_settings"))
                elif "Durum" in group.title() or "Status" in group.title():
                    group.setTitle(_("download_status"))
            
            # Etiketler
            for label in download_tab.findChildren(QLabel):
                if "URL" in label.text():
                    if "Playlist" in label.text() or "playlist" in label.text():
                        label.setText(f"{_('playlist_url')}:")
                    else:
                        label.setText(f"{_('video_url')}:")
                elif "Konum" in label.text() or "Location" in label.text():
                    label.setText(f"{_('download_location')}:")
                elif "Kalite" in label.text() or "Quality" in label.text():
                    label.setText(f"{_('video_quality')}:")
                elif "Hazır" == label.text() or "Ready" == label.text():
                    label.setText(_("ready"))
            
            # Butonlar
            for button in download_tab.findChildren(QPushButton):
                if "Başlat" in button.text() or "Start" in button.text():
                    button.setText(_("start_download"))
                elif "Seç" in button.text() or "Select" in button.text():
                    button.setText(_("select_folder"))
            
            # Giriş alanları
            for input_field in download_tab.findChildren(QLineEdit):
                if not input_field.text() and input_field.placeholderText():
                    if "video" in input_field.placeholderText().lower():
                        input_field.setPlaceholderText(_("video_url_placeholder"))
                    elif "playlist" in input_field.placeholderText().lower():
                        input_field.setPlaceholderText(_("playlist_url_placeholder"))
            
            # Video kalitesi combobox
            for combo in download_tab.findChildren(QComboBox):
                if combo.count() > 0 and combo.itemText(0) in ["auto", "otomatik", "automático", "авто"]:
                    current_index = combo.currentIndex()
                    combo.clear()
                    combo.addItems([_("auto"), "144p", "240p", "360p", "480p", "720p", "1080p", "1440p", "2160p", "4320p"])
                    combo.setCurrentIndex(current_index)
        
        # Ayarlar sekmesi
        settings_tab = self.tab_widget.widget(1)
        if settings_tab:
            # Gruplar
            for group in settings_tab.findChildren(QGroupBox):
                if "FFmpeg" in group.title():
                    group.setTitle(_("ffmpeg_settings"))
                elif "Önbellek" in group.title() or "Cache" in group.title():
                    group.setTitle(_("cache_settings"))
                elif "Dil" in group.title() or "Language" in group.title():
                    group.setTitle(_("language_settings"))
                elif "Hakkında" in group.title() or "About" in group.title():
                    group.setTitle(_("about"))
            
            # Etiketler
            for label in settings_tab.findChildren(QLabel):
                if "FFmpeg" in label.text() and ("Durum" in label.text() or "Status" in label.text()):
                    if self.downloader.ffmpeg.is_available:
                        label.setText(_("ffmpeg_status").format(_("ffmpeg_available")))
                        label.setStyleSheet("color: green")
                    else:
                        label.setText(_("ffmpeg_status").format(_("ffmpeg_not_available")))
                        label.setStyleSheet("color: red")
                elif "Not:" in label.text() or "Note:" in label.text():
                    label.setText(_("ffmpeg_note"))
                elif "Önbellek" in label.text() or "Cache" in label.text() or "cache" in label.text():
                    if "temizle" not in label.text().lower() and "clear" not in label.text().lower():
                        label.setText(_("cache_info"))
                elif "Dil" in label.text() or "Language" in label.text():
                    if "Seç" in label.text() or "Select" in label.text():
                        label.setText(_("select_language"))
                    elif "yeniden" in label.text().lower() or "restart" in label.text().lower():
                        label.setText(_("restart_required"))
                elif "YTDx" in label.text() and "Sürüm" in label.text() or "Version" in label.text():
                    label.setText(_("about_text"))
            
            # Butonlar
            for button in settings_tab.findChildren(QPushButton):
                if "FFmpeg" in button.text() and "Seç" in button.text() or "Select" in button.text():
                    button.setText(_("ffmpeg_select"))
                elif "Temizle" in button.text() or "Clear" in button.text():
                    button.setText(_("clear_cache"))
        
        # Durum çubuğu
        self.status_bar.showMessage(_("ready"))
        
        # İlerleme bilgisi
        self.status_label.setText(_("ready"))
    
    def clear_cache(self):
        """YouTube indirme önbelleğini temizler."""
        try:
            # Önbellek temizleme işlemini başlat
            result = self.downloader.clear_cache()
            
            if result:
                self.update_status(_("cache_cleared"), "success")
                QMessageBox.information(
                    self,
                    _("cache_settings"),
                    _("cache_cleared"),
                    QMessageBox.StandardButton.Ok
                )
                logger.info("Cache cleared successfully")
            else:
                self.update_status(_("cache_clear_failed"), "error")
                QMessageBox.warning(
                    self,
                    _("cache_settings"),
                    _("cache_clear_failed"),
                    QMessageBox.StandardButton.Ok
                )
                logger.warning("Cache clearing failed")
        except Exception as e:
            error_msg = str(e)
            self.update_status(f"Önbellek temizleme hatası: {error_msg}", "error")
            QMessageBox.critical(
                self,
                _("cache_settings"),
                f"Önbellek temizleme hatası:\n{error_msg}",
                QMessageBox.StandardButton.Ok
            )
            logger.error(f"Cache clearing error: {error_msg}")
    
    def closeEvent(self, event):
        """Pencere kapatılırken çağrılır."""
        if self.download_in_progress:
            reply = QMessageBox.question(
                self,
                _("download_in_progress"),
                _("download_in_progress_message"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                if self.download_thread and self.download_thread.isRunning():
                    self.download_thread.terminate()
                    self.download_thread.wait()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()
