# 🛡️ PC Güvenlik & Nöbetçi Botu (Sentinel Pro)

Bilgisayarınızın başında olmadığınızda yetkisiz kullanımı, fiziksel teması, unutulma (1 saat boşta kalma) ve kritik pil durumlarını izleyen; olay anında **webcam fotoğrafı, ekran görüntüsü ve canlı Google Haritalar konumuyla birlikte Gmail adresinize alarm gönderen**, çevrimdışı (SQLite) destekli profesyonel masaüstü nöbetçi uygulaması.

---

## 🚀 Öne Çıkan Özellikler

1. **📚 Kütüphane Modu (Sıfır Yanlış Alarm):**
   * Kütüphanede veya kafede çalışırken arkanızdan/önünüzden geçen insanlar kamerayı boşuna tetiklemesin diye tek tıkla kamerayı devre dışı bırakabilirsiniz.
   * Yalnızca **birisi bilgisayara, klavyeye veya fareye fiziksel olarak dokunursa** sistem devreye girer.
2. **⌨️ Masaya Dönüş İptali ([F9] Tuşu):**
   * Siz masaya döndüğünüzde fareye dokunur dokunmaz alarm patlamaz!
   * 5 saniyelik sessiz bir bekleme süresi tanınır. Klavyeden **`F9`** tuşuna bastığınız an sistem sizin gerçek sahip olduğunuzu anlar, alarmı iptal eder ve sessizce nöbeti sonlandırır.
   * Eğer 5 saniye içinde `F9`'a basılmazsa yetkisiz erişim kabul edilip anında alarm mailleri gönderilir.
3. **🖥️ Çift Görsel: Webcam + Anlık Ekran Görüntüsü (Screenshot):**
   * Olay anında sadece kameradaki kişinin yüzünü değil, o an bilgisayar ekranında açık olan pencereyi/sekmenin ekran görüntüsünü de yakalar ve maile ekler.
4. **📍 Canlı Konum & Google Haritalar Linki:**
   * Kütüphanede bilgisayarı unuttuğunuzda, son bilinen ağ konumunu ve tek tıkla açılan Google Haritalar linkini iletir.
5. **🗄️ SQLite Veritabanı & Çevrimdışı Kuyruk:**
   * İnternet kesilse bile tüm olaylar `security.db` ve `captures/` klasörüne depolanır; internet geldiği anda otomatik olarak postalanır.
6. **🪟 Arka Plana / Sistem Tepsisine (System Tray) Gizlenme:**
   * Pencereyi sağ alttaki Windows saat simgelerinin yanına gizleyip arka planda tamamen görünmez şekilde çalıştırabilirsiniz.
7. **🔊 Opsiyonel Caydırıcı Siren:**
   * Kütüphane güvenliği için varsayılan olarak **KAPALI** gelir. Evde veya odanızdayken isterseniz açabilirsiniz.

---

## 🔑 Gmail 16 Haneli "Uygulama Şifresi" Nasıl Alınır?

1. [Google Hesap Güvenliği](https://myaccount.google.com/security) sayfasına gidin.
2. **2 Adımlı Doğrulama** açık olduğundan emin olun.
3. Arama kutusuna **"Uygulama şifreleri"** yazın.
4. Ad olarak **"PC Bot"** yazıp **Oluştur**'a tıklayın.
5. Verilen 16 haneli kodu programdaki şifre alanına yapıştırın.

---

## ▶️ Nasıl Çalıştırılır?
* Klasördeki **`baslat.bat`** dosyasına çift tıklayarak doğrudan çalıştırabilirsiniz.
* Veya komut satırından:
  ```bash
  python app.py
  ```

---

## 🤖 Yapay Zekalar İçin Teknik Doküman
Projenin modüler mimarisini, SQLite şemasını ve akış diyagramını diğer yapay zekalara aktarmak için [AI_SYSTEM_OVERVIEW.md](file:///c:/Users/ALİ/Desktop/python/pc_guvenlik_botu/AI_SYSTEM_OVERVIEW.md) dosyasını inceleyebilirsiniz.
