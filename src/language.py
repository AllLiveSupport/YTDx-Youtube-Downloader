"""
YTDx - Language Module
Çoklu dil desteği için modül
"""

import os
import json
import logging
from typing import Dict, Any, Optional

# Loglama ayarları
logger = logging.getLogger("YTDx.Language")

class LanguageManager:
    """Dil yönetimi sınıfı."""
    
    # Desteklenen diller
    SUPPORTED_LANGUAGES = {
        "tr": "Türkçe",
        "en": "English",
        "es": "Español",
        "ru": "Русский"
    }
    
    # Desteklenen temalar
    SUPPORTED_THEMES = {
        "light": "Aydınlık",
        "dark": "Karanlık"
    }
    
    def __init__(self, language_dir: str = None):
        """Dil yöneticisi başlatıcısı.
        
        Args:
            language_dir: Dil dosyalarının bulunduğu dizin
        """
        self.language_dir = language_dir or os.path.join(os.path.dirname(os.path.dirname(__file__)), "languages")
        self.current_language = "tr"  # Varsayılan dil
        self.current_theme = "light"  # Varsayılan tema
        self.translations = {}
        
        # Dil dosyalarını yükle
        self.load_language(self.current_language)
        self.load_theme_preference()
        
        logger.info(f"Dil yöneticisi başlatıldı: {self.current_language}, Tema: {self.current_theme}")
    
    def load_language(self, language_code: str) -> bool:
        """Belirtilen dil koduna göre çevirileri yükler.
        
        Args:
            language_code: Dil kodu (tr, en, es, ru)
            
        Returns:
            bool: Başarılı ise True, değilse False
        """
        if language_code not in self.SUPPORTED_LANGUAGES:
            logger.error(f"Desteklenmeyen dil kodu: {language_code}")
            return False
            
        try:
            language_file = os.path.join(self.language_dir, f"{language_code}.json")
            
            if not os.path.exists(language_file):
                logger.error(f"Dil dosyası bulunamadı: {language_file}")
                return False
                
            with open(language_file, "r", encoding="utf-8") as f:
                self.translations = json.load(f)
                
            self.current_language = language_code
            logger.info(f"Dil yüklendi: {language_code}")
            return True
            
        except Exception as e:
            logger.error(f"Dil yükleme hatası: {str(e)}")
            return False
    
    def get_text(self, key: str, *args) -> str:
        """Belirtilen anahtara göre çeviriyi döndürür.
        
        Args:
            key: Çeviri anahtarı
            *args: Format parametreleri
            
        Returns:
            str: Çevrilmiş metin
        """
        if key not in self.translations:
            logger.warning(f"Çeviri anahtarı bulunamadı: {key}")
            return key
            
        text = self.translations[key]
        
        # Format parametreleri varsa uygula
        if args:
            try:
                text = text.format(*args)
            except Exception as e:
                logger.error(f"Çeviri format hatası: {str(e)}")
                
        return text
    
    def get_language_name(self, language_code: Optional[str] = None) -> str:
        """Dil koduna göre dil adını döndürür.
        
        Args:
            language_code: Dil kodu (belirtilmezse mevcut dil)
            
        Returns:
            str: Dil adı
        """
        code = language_code or self.current_language
        return self.SUPPORTED_LANGUAGES.get(code, code)
    
    def get_supported_languages(self) -> Dict[str, str]:
        """Desteklenen dilleri döndürür.
        
        Returns:
            Dict[str, str]: Dil kodu ve adı sözlüğü
        """
        return self.SUPPORTED_LANGUAGES
    
    def save_language_preference(self, language_code: str) -> bool:
        """Dil tercihini kaydeder.
        
        Args:
            language_code: Dil kodu
            
        Returns:
            bool: Başarılı ise True, değilse False
        """
        try:
            config_dir = os.path.dirname(self.language_dir)
            config_file = os.path.join(config_dir, "config.json")
            
            # Mevcut yapılandırmayı yükle veya oluştur
            config = {}
            if os.path.exists(config_file):
                try:
                    with open(config_file, "r", encoding="utf-8") as f:
                        config = json.load(f)
                except:
                    pass
            
            # Dil tercihini güncelle
            config["language"] = language_code
            
            # Yapılandırmayı kaydet
            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=4)
                
            logger.info(f"Dil tercihi kaydedildi: {language_code}")
            return True
            
        except Exception as e:
            logger.error(f"Dil tercihi kaydetme hatası: {str(e)}")
            return False
    
    def load_language_preference(self) -> str:
        """Kaydedilmiş dil tercihini yükler.
        
        Returns:
            str: Dil kodu
        """
        try:
            config_dir = os.path.dirname(self.language_dir)
            config_file = os.path.join(config_dir, "config.json")
            
            if not os.path.exists(config_file):
                return self.current_language
                
            with open(config_file, "r", encoding="utf-8") as f:
                config = json.load(f)
                
            language_code = config.get("language", self.current_language)
            
            # Dil kodunu doğrula
            if language_code in self.SUPPORTED_LANGUAGES:
                # Dili yükle
                if self.load_language(language_code):
                    return language_code
            
            return self.current_language
            
        except Exception as e:
            logger.error(f"Dil tercihi yükleme hatası: {str(e)}")
            return self.current_language

    def save_theme_preference(self, theme: str) -> bool:
        """Tema tercihini kaydeder.
        
        Args:
            theme: Tema adı (light/dark)
            
        Returns:
            bool: Başarılı ise True, değilse False
        """
        try:
            config_dir = os.path.dirname(self.language_dir)
            config_file = os.path.join(config_dir, "config.json")
            
            # Mevcut yapılandırmayı yükle veya oluştur
            config = {}
            if os.path.exists(config_file):
                try:
                    with open(config_file, "r", encoding="utf-8") as f:
                        config = json.load(f)
                except:
                    pass
            
            # Tema tercihini güncelle
            config["theme"] = theme
            
            # Yapılandırmayı kaydet
            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=4)
                
            logger.info(f"Tema tercihi kaydedildi: {theme}")
            return True
            
        except Exception as e:
            logger.error(f"Tema tercihi kaydetme hatası: {str(e)}")
            return False
    
    def load_theme_preference(self) -> str:
        """Kaydedilmiş tema tercihini yükler.
        
        Returns:
            str: Tema adı
        """
        try:
            config_dir = os.path.dirname(self.language_dir)
            config_file = os.path.join(config_dir, "config.json")
            
            if not os.path.exists(config_file):
                return self.current_theme
                
            with open(config_file, "r", encoding="utf-8") as f:
                config = json.load(f)
                
            theme = config.get("theme", self.current_theme)
            
            # Tema adını doğrula
            if theme in self.SUPPORTED_THEMES:
                self.current_theme = theme
                return theme
            
            return self.current_theme
            
        except Exception as e:
            logger.error(f"Tema tercihi yükleme hatası: {str(e)}")
            return self.current_theme

# Singleton örneği
_instance = None

def get_language_manager() -> LanguageManager:
    """Dil yöneticisi singleton örneğini döndürür."""
    global _instance
    if _instance is None:
        _instance = LanguageManager()
    return _instance

# Kısaltma fonksiyonu
def _(key: str, *args) -> str:
    """Çeviri için kısaltma fonksiyonu."""
    return get_language_manager().get_text(key, *args)
