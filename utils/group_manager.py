#Grup Yöneticisi (utils/group_manager.py)

import json
from typing import Dict, List, Set
from pathlib import Path
from config import config
from utils.logger import logger
import unicodedata
import re

class GroupManager:
    def __init__(self):
        self.groups = self.load_groups()
        self.city_to_group = self.build_city_mapping()
        self.group_cache = {}  # Grup bilgileri için cache
    
    def load_groups(self) -> Dict:
        """Grupları JSON dosyasından yükler"""
        groups_file = config.GROUPS_DIR / "groups.json"
        
        if not groups_file.exists():
            logger.warning("Gruplar dosyası bulunamadı, örnek dosya oluşturuluyor")
            self.create_sample_groups_file()
            groups_file = config.GROUPS_DIR / "groups.json"
        
        try:
            with open(groups_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Gruplar yüklenirken hata: {e}")
            return {"groups": []}
    
    def create_sample_groups_file(self):
        """Örnek gruplar dosyası oluşturur"""
        sample_groups = {
            "groups": [
                {
                    "group_id": "Grup_1",
                    "group_name": "NURHAN",
                    "cities": ["Afyon", "Aksaray", "Ankara", "Antalya", "Van"],
                    "email_recipients": ["email1@example.com", "email2@example.com"]
                },
                {
                    "group_id": "Grup_2",
                    "group_name": "MAHMUTBEY",
                    "cities": ["Adana", "Adıyaman", "Batman", "Bingöl", "Bitlis"],
                    "email_recipients": ["email3@example.com"]
                }
            ]
        }
        
        with open(config.GROUPS_DIR / "groups.json", 'w', encoding='utf-8') as f:
            json.dump(sample_groups, f, ensure_ascii=False, indent=2)
    
    def normalize_city_name(self, city_name: str) -> str:
        """
        Şehir ismini normalleştirir - Türkçe karakter sorununu çözer
        """
        if not city_name or not isinstance(city_name, str):
            return ""
        
        # Unicode normalize (NFD form) ve Türkçe karakter dönüşümü
        city_name = unicodedata.normalize('NFKD', city_name)
        
        # Türkçe karakterleri İngilizce karşılıklarına çevir
        turkish_to_english = {
            'ğ': 'g', 'Ğ': 'G',
            'ı': 'i', 'İ': 'I',
            'ö': 'o', 'Ö': 'O',
            'ü': 'u', 'Ü': 'U',
            'ş': 's', 'Ş': 'S',
            'ç': 'c', 'Ç': 'C',
            'â': 'a', 'Â': 'A',
            'î': 'i', 'Î': 'I',
            'û': 'u', 'Û': 'U'
        }
        
        normalized = ''.join(turkish_to_english.get(char, char) for char in city_name)
        
        # Büyük harfe çevir, boşlukları ve noktalamaları temizle
        normalized = normalized.upper().strip()
        normalized = re.sub(r'[^A-Z0-9\s]', '', normalized)  # Sadece harf, rakam ve boşluk
        normalized = re.sub(r'\s+', ' ', normalized)  # Çoklu boşlukları tekilleştir
        
        return normalized
    
    def build_city_mapping(self) -> Dict[str, List[str]]:
        """
        Şehir isimlerini grup ID'lerine eşleyen sözlük oluşturur
        Bir şehir birden fazla gruba ait olabilir
        """
        mapping = {}
        for group in self.groups.get("groups", []):
            group_id = group["group_id"]
            for city in group["cities"]:
                normalized_city = self.normalize_city_name(city)
                if normalized_city:
                    if normalized_city not in mapping:
                        mapping[normalized_city] = []
                    mapping[normalized_city].append(group_id)
        
        # Grup_0 için özel işlem
        mapping[""] = ["Grup_0"]
        mapping["UNKNOWN"] = ["Grup_0"]
        
        return mapping
    
    def get_groups_for_city(self, city_name: str) -> List[str]:
        """Bir şehir adına karşılık gelen grup ID'lerini döndürür"""
        if not city_name:
            return ["Grup_0"]
        
        normalized_city = self.normalize_city_name(city_name)
        return self.city_to_group.get(normalized_city, ["Grup_0"])
    
    def get_group_info(self, group_id: str) -> Dict:
        """Grup bilgilerini döndürür (cache'li)"""
        if group_id in self.group_cache:
            return self.group_cache[group_id]
        
        for group in self.groups.get("groups", []):
            if group["group_id"] == group_id:
                self.group_cache[group_id] = group
                return group
        
        # Varsayılan grup bilgisi
        default_group = {
            "group_id": "Grup_0",
            "group_name": "Eşleşmeyen Veriler",
            "cities": [],
            "email_recipients": config.DEFAULT_EMAIL_RECIPIENTS if hasattr(config, 'DEFAULT_EMAIL_RECIPIENTS') else []
        }
        self.group_cache[group_id] = default_group
        return default_group
    
    def refresh_groups(self):
        """Grupları yeniden yükler"""
        self.groups = self.load_groups()
        self.city_to_group = self.build_city_mapping()
        self.group_cache.clear()
        logger.info("Gruplar başarıyla yenilendi")

# Global group manager instance
group_manager = GroupManager()