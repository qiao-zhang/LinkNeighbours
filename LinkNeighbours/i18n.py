"""
Internationalization module for Anki Add-on
Provides translation functionality that follows Anki's language settings
"""

from anki.lang import current_lang
import os
import json


class I18n:
    """
    Internationalization class that manages translations for the add-on
    """
    
    def __init__(self):
        self.translations = {}
        self._load_translations()
    
    def _load_translations(self):
        """
        Load translation files for the current language
        """
        # Get the directory of this file
        current_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Define possible translation file paths
        lang_codes = []
        
        # Add fallback languages
        if current_lang.startswith("zh"):
            lang_codes.append("zh-CN")  # Fallback to Simplified Chinese
        elif current_lang != "en":
            lang_codes.append("en")  # Fallback to English
        
        # Try to load translations from each language code
        for lang_code in lang_codes:
            translation_file = os.path.join(current_dir, "locale", f"{lang_code}.json")
            if os.path.exists(translation_file):
                try:
                    with open(translation_file, 'r', encoding='utf-8') as f:
                        translations = json.load(f)
                        self.translations.update(translations)
                        break  # Successfully loaded translations
                except Exception as e:
                    print(f"Failed to load translations for {lang_code}: {e}")
        
        # If no translations were loaded, initialize with empty dict
        if not self.translations:
            self.translations = {}
    
    def tr(self, key: str, **kwargs) -> str:
        """
        Translate a key with optional formatting
        :param key: Translation key
        :param kwargs: Format arguments
        :return: Translated string
        """
        translated = self.translations.get(key, key)
        
        # Apply formatting if arguments are provided
        if kwargs:
            try:
                translated = translated.format(**kwargs)
            except KeyError:
                # If formatting fails, return the original translated string
                pass
        
        return translated
    

# Global instance of the I18n class
i18n_instance = None

def init_i18n():
    global i18n_instance
    i18n_instance = I18n()

def tr(key: str, **kwargs) -> str:
    """
    Convenience function to translate a key
    """
    return i18n_instance.tr(key, **kwargs)
