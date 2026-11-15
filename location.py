import json
import os
import requests

CACHE_FILE = os.path.join(os.path.dirname(__file__), "last_location.json")

class LocationService:
    """Ağ ve IP üzerinden anlık coğrafi konum sorgulama ve önbellekleme servisi."""

    def __init__(self):
        self.last_location = self._load_cached_location()

    def _load_cached_location(self):
        if os.path.exists(CACHE_FILE):
            try:
                with open(CACHE_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return None

    def _save_cache(self, loc_data):
        try:
            with open(CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(loc_data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def fetch_current_location(self):
        """İnternet üzerinden koordinatları sorgular, çevrimdışı ise önbellekten döner."""
        endpoints = [
            "http://ip-api.com/json/?fields=status,country,city,regionName,lat,lon,query",
            "https://ipapi.co/json/"
        ]

        for url in endpoints:
            try:
                resp = requests.get(url, timeout=4)
                if resp.status_code == 200:
                    data = resp.json()
                    
                    if "lat" in data and "lon" in data and data.get("status") != "fail":
                        lat = data["lat"]
                        lon = data["lon"]
                        loc_info = {
                            "lat": lat,
                            "lon": lon,
                            "city": data.get("city", "Bilinmiyor"),
                            "region": data.get("regionName", data.get("region", "")),
                            "country": data.get("country", "Türkiye"),
                            "ip": data.get("query", data.get("ip", "")),
                            "maps_url": f"https://maps.google.com/?q={lat},{lon}",
                            "source": "Canlı İnternet"
                        }
                        self.last_location = loc_info
                        self._save_cache(loc_info)
                        return loc_info
            except Exception:
                continue

        if self.last_location:
            cached = self.last_location.copy()
            cached["source"] = "Son Bilinen Konum (Çevrimdışı Önbellek)"
            return cached

        return {
            "lat": None,
            "lon": None,
            "city": "Bilinmiyor (Çevrimdışı)",
            "region": "",
            "country": "",
            "ip": "",
            "maps_url": "",
            "source": "Konum Alınamadı"
        }
