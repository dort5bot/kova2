#Grup Yöneticisi (utils/group_manager.py)
import json
from typing import Dict, List, Set
from pathlib import Path
from config import config
from utils.logger import logger

class GroupManager:
    def __init__(self):
        self.groups = self.load_groups()
        self.city_to_group = self.build_city_mapping()
    
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
    
    def build_city_mapping(self) -> Dict[str, str]:
        """Şehir isimlerini grup ID'lerine eşleyen sözlük oluşturur"""
        mapping = {}
        for group in self.groups.get("groups", []):
            group_id = group["group_id"]
            for city in group["cities"]:
                # Hem büyük hem küçük harf duyarlılığını kaldır
                normalized_city = city.upper().strip()
                mapping[normalized_city] = group_id
        return mapping
    
    def get_group_for_city(self, city_name: str) -> str:
        """Bir şehir adına karşılık gelen grup ID'sini döndürür"""
        if not city_name:
            return "Grup_0"
        
        normalized_city = str(city_name).upper().strip()
        return self.city_to_group.get(normalized_city, "Grup_0")
    
    def get_group_info(self, group_id: str) -> Dict:
        """Grup bilgilerini döndürür"""
        for group in self.groups.get("groups", []):
            if group["group_id"] == group_id:
                return group
        return {
            "group_id": "Grup_0",
            "group_name": "Grup_0",
            "cities": [],
            "email_recipients": []
        }

# Global group manager instance
group_manager = GroupManager()
