"""
YTDx - YouTube Video İndirici
Ana uygulama modülü
"""

import os
import sys
import logging
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon, QPalette, QColor

# Loglama ayarları
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("ytdx.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("YTDx")

def apply_theme(app, theme):
    palette = QPalette()
    if theme == 'dark':
        palette.setColor(QPalette.ColorRole.Window, QColor(32, 32, 32))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.Base, QColor(45, 45, 45))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(32, 32, 32))
        palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.ToolTipText, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.Text, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.Button, QColor(32, 32, 32))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 0, 0))
        palette.setColor(QPalette.ColorRole.Link, QColor(0, 122, 255))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(0, 122, 255))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.PlaceholderText, QColor(200, 200, 200))
        palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor(127, 127, 127))
        palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor(127, 127, 127))
        palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Highlight, QColor(80, 80, 80))
        palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.HighlightedText, QColor(127, 127, 127))
    else:  # light
        palette.setColor(QPalette.ColorRole.Window, QColor(240, 240, 240))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(0, 0, 0))
        palette.setColor(QPalette.ColorRole.Base, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(240, 240, 240))
        palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(0, 0, 0))
        palette.setColor(QPalette.ColorRole.ToolTipText, QColor(0, 0, 0))
        palette.setColor(QPalette.ColorRole.Text, QColor(0, 0, 0))
        palette.setColor(QPalette.ColorRole.Button, QColor(240, 240, 240))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(0, 0, 0))
        palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 0, 0))
        palette.setColor(QPalette.ColorRole.Link, QColor(0, 0, 255))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(0, 120, 215))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
    app.setPalette(palette)

def main():
    """Ana uygulama fonksiyonu."""
    try:
        logger.info("Uygulama başlatılıyor...")
        
        # Dil yöneticisini başlat
        from src.language import get_language_manager
        lang_manager = get_language_manager()
        lang_manager.load_language_preference()
        lang_manager.load_theme_preference()
        
        # PyQt uygulamasını başlat
        app = QApplication(sys.argv)
        app.setStyle("Fusion")  # Modern görünüm için Fusion stilini kullan
        apply_theme(app, lang_manager.current_theme)
        app.setWindowIcon(QIcon('icon.ico'))  # Uygulama ikonunu ayarla
        
        # Ana pencereyi oluştur
        from src.gui import MainWindow
        window = MainWindow(lang_manager)
        window.show()
        
        # Uygulamayı çalıştır
        exit_code = app.exec()
        
        # Yeniden başlatma kodu kontrol et
        if exit_code == MainWindow.RESTART_CODE:
            logger.info("Uygulama yeniden başlatılıyor...")
            try:
                # Windows'ta daha güvenilir bir yeniden başlatma yöntemi
                import subprocess
                import shlex
                
                # Mevcut çalışma dizinini al
                cwd = os.getcwd()
                
                # Python yürütülebilir dosyasının yolunu al
                python_exe = sys.executable
                
                # Uygulama dizinine geç
                os.chdir(os.path.dirname(os.path.abspath(__file__)))
                
                # Yeni işlemi başlat
                subprocess.Popen([python_exe] + sys.argv, cwd=cwd)
                
            except Exception as e:
                logger.error(f"Yeniden başlatma hatası: {str(e)}")
                
        # Uygulamayı kapat
        sys.exit(0)
        
    except Exception as e:
        logger.error(f"Uygulama hatası: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
