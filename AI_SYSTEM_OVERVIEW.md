# 🤖 AI SYSTEM OVERVIEW: PC Güvenlik & Nöbetçi Botu (Sentinel Pro)

> **Amaç:** Bu doküman, başka bir yapay zeka ajanının (LLM) veya geliştiricinin projeyi 1 dakikada anlayabilmesi, mimariyi kavraması ve doğrudan kod ekleyip geliştirebilmesi için hazırlanmıştır.

---

## 📌 Proje Özeti
* **Proje Adı:** PC Güvenlik & Nöbetçi Botu (Sentinel Pro)
* **Hedef Platform:** Windows 10/11 (Python 3.10+)
* **Temel İşlev:** Bilgisayar başında kullanıcı yokken yetkisiz fiziksel erişimleri (kamera hareketi, fare hareketi), unutulma durumlarını (1 saat boşta kalma / idle) ve sistem risklerini (kritik pil <= %10, aşırı CPU) izler.
* **Kütüphane Dostu Özellikler:**
  * **📚 Kütüphane Modu:** Etrafta dolaşan insanlardan ötürü kameranın boşuna tetiklenmesini önlemek için tek tıkla kamera devre dışı bırakılır, sadece doğrudan fare/klavye teması ve unutulma izlenir.
  * **⌨️ Masaya Dönüş İptali [F9]:** Biri fareye dokunduğunda anında alarm çalmaz! 5 saniyelik sessiz bir grace period başlar. Masaya oturan gerçek sahipse 5 sn içinde **F9** tuşuna basar, sistem doğrulanır ve hiçbir alarm/mail tetiklenmeden nöbet kapanır.
  * **🔕 Güvenli Sessiz Mod:** Siren varsayılan olarak kapalıdır; kütüphanede asla ses çıkarmaz.
* **Depolama & İletişim:** Olayları yerel **SQLite** veritabanına (`security.db`) ve diskteki `captures/` klasörüne kaydeder (Webcam fotoğrafı + Ekran görüntüsü). İnternet varsa anlık **Gmail** üzerinden webcam fotoğrafı, ekran görüntüsü ve Google Maps konum linkiyle birlikte e-posta atar. İnternet kesilirse çevrimdışı kuyruk devreye girer.
* **Arka Plan Modu:** `pystray` ile sağ alttaki sistem tepsisine (system tray) gizlenebilir.

---

## 🧱 Modül Haritası & Sorumluluklar

| Dosya | Görevi ve Sorumluluğu |
| :--- | :--- |
| **`app.py`** | **Grafik Arayüz (GUI) & Sistem Tepsisi:** `customtkinter` ve `pystray` ile yazılmıştır. İkonu (`icon.ico`/`icon.png`) yükler. Kütüphane modu, F9 doğrulama durumu, Gmail ayarları, canlı log konsolu ve tepsiye küçültme işlevlerini yönetir. |
| **`sentinel.py`** | **Ana Nöbetçi & Güvenlik Motoru:** Arka plan iş parçacığıdır (`threading`). Fare hareketini (`ctypes`), global `F9` tuş dinlemesini (`GetAsyncKeyState(VK_F9)`), 5 sn geri sayım süresini, ekran görüntüsü almayı (`ImageGrab`), kamera hareketini (`cv2`) ve pili (`psutil`) yönetir. |
| **`database.py`** | **Yerel Depolama (SQLite):** `security.db` ve `captures/` klasörünü yönetir. Olayları, webcam fotoğraflarını ve ekran görüntülerini diske yazar. Çevrimdışı kuyruk mantığını sağlar. |
| **`location.py`** | **Konum Servisi:** IP Geolocation API'lerinden (`ip-api.com`, `ipapi.co`) koordinat ve şehir bilgisini çeker. Tıklanabilir Google Maps linki üretir ve `last_location.json` içinde önbelleğe alır. |
| **`mailer.py`** | **Gmail SMTP Motoru:** `smtplib.SMTP_SSL` (Port 465) üzerinden HTML formatında şık alarm mailleri yollar. Hem webcam fotoğrafını hem de ekran görüntüsünü gömülü olarak postalar. |
| **`create_icon.py`** | Pillow ile 256x256 vektörel kalkan ikonu (`icon.ico` ve `icon.png`) üreten yardımcı araç. |
| **`baslat.bat`** | Tek tıkla uygulamayı başlatan Windows betiği. |

---

## 🗄️ SQLite Veritabanı Şeması (`security.db`)

```sql
CREATE TABLE IF NOT EXISTS security_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,         -- Örn: "2026-11-15 05:30:00"
    event_type TEXT NOT NULL,         -- Örn: "Yetkisiz Kullanıcı Teması (F9 Doğrulaması Başarısız)"
    image_path TEXT,                  -- Webcam fotoğrafı yolu: "captures/..._cam.jpg"
    screenshot_path TEXT,             -- Ekran görüntüsü yolu: "captures/..._screen.jpg"
    location_city TEXT,               -- Örn: "Ankara, Türkiye"
    location_maps_url TEXT,           -- Örn: "https://maps.google.com/?q=39.92,32.85"
    location_source TEXT,             -- "Canlı İnternet" veya "Son Bilinen Konum (Önbellek)"
    cpu_percent REAL,                 -- Örn: 15.2
    ram_percent REAL,                 -- Örn: 52.1
    battery_status TEXT,              -- Örn: "%8 (Pilde)"
    email_status TEXT DEFAULT 'QUEUED', -- 'SENT' veya 'QUEUED'
    sent_at TEXT                      -- Gönderilme zaman damgası
);
```

---

## 🛡️ Masaya Dönüş & Doğrulama Algoritması (Grace Period)

```
[Kullanıcı / Saldırgan Fareye Dokundu]
                 │
                 ▼
 5 Saniyelik Sessiz Doğrulama Süresi Başlar
 (Ekranda veya konsolda 'F9 bekleniyor' uyarısı)
                 │
        ┌────────┴────────┐
        ▼                 ▼
   [F9 Basıldı]      [5 sn Doldu & F9 Basılmadı]
        │                         │
   (Gerçek Sahip)          (Yetkisiz Kişi / Hırsız)
        │                         │
  • Nöbet sonlanır         • Ekran görüntüsü + Webcam alınır
  • Alarm iptal edilir     • SQLite'a yazılır
  • Ses/Mail çıkmaz        • Gmail'e konum & fotoğraflar gider
                           • (Açıksa) Siren çalar
```

---

## 🛠️ Gelecekte Kod Ekleyecek Yapay Zekalar İçin İpuçları

1. **Masaya Dönüş İptal Tuşunu Değiştirmek:**
   * `sentinel.py` içindeki `VK_F9 = 0x78` sanal tuş kodunu değiştirebilirsiniz (Örn: `VK_F8 = 0x77` veya `VK_ESCAPE = 0x1B`).
2. **Kütüphane Modunu Varsayılan Yapmak:**
   * `app.py` içinde `self.chk_library_mode.select()` satırını ekleyerek başlatabilirsiniz.
3. **Yeni Bir Alarm Türü Eklemek:**
   * `self._trigger_alert(reason="Yeni Alarm", image_bytes=cam, screenshot_bytes=screen)` çağrısı yapıldığında sistem otomatik olarak diske, SQLite'a ve Gmail'e çift görselle birlikte yollar.
