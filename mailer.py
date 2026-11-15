import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
import datetime

class GmailNotifier:
    """Gmail SMTP (SSL 465) üzerinden HTML formatlı güvenlik bildirimleri gönderir."""

    def __init__(self, sender_email="", app_password="", receiver_email=""):
        self.sender_email = sender_email.strip()
        self.app_password = app_password.replace(" ", "").strip()
        self.receiver_email = receiver_email.strip() if receiver_email.strip() else self.sender_email

    def update_credentials(self, sender_email, app_password, receiver_email=None):
        self.sender_email = sender_email.strip()
        self.app_password = app_password.replace(" ", "").strip()
        self.receiver_email = receiver_email.strip() if receiver_email and receiver_email.strip() else self.sender_email

    def send_test_email(self, location_info=None):
        """Bağlantı ve kimlik doğrulama testi için e-posta gönderir."""
        now_str = datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        subject = "🛡️ PC Nöbetçi Botu - Test Bildirimi"
        
        loc_html = ""
        if location_info and location_info.get("maps_url"):
            loc_html = f"""
            <div style="background: #e7f5ff; border: 1px solid #a5d8ff; padding: 12px; margin-top: 15px; border-radius: 6px; font-size: 14px;">
                <b>📍 Tespit Edilen Konum:</b> {location_info.get('city', '')}, {location_info.get('country', '')} ({location_info.get('source', '')})<br>
                <a href="{location_info.get('maps_url')}" target="_blank" style="display: inline-block; margin-top: 8px; background: #1c7ed6; color: white; padding: 6px 14px; text-decoration: none; border-radius: 4px; font-size: 13px;">🗺️ Google Haritalar'da Aç</a>
            </div>
            """

        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; background-color: #f4f6f9; padding: 20px;">
            <div style="max-width: 550px; margin: auto; background: #ffffff; border-radius: 10px; padding: 25px; box-shadow: 0 4px 10px rgba(0,0,0,0.1);">
                <h2 style="color: #2b8a3e; margin-top: 0;">✅ Gmail Bağlantısı Başarılı!</h2>
                <p>Tebrikler! <b>PC Güvenlik & Nöbetçi Botu</b> Gmail ayarlarınız başarıyla bağlandı ve test edildi.</p>
                <div style="background: #f1f3f5; padding: 12px; border-radius: 6px; font-size: 14px;">
                    <b>🕒 Test Zamanı:</b> {now_str}<br>
                    <b>💻 Gönderen:</b> {self.sender_email}<br>
                    <b>📩 Alıcı:</b> {self.receiver_email}
                </div>
                {loc_html}
                <p style="color: #666; font-size: 13px; margin-top: 20px;">
                    Artık botunuz herhangi bir hareket veya alarm algıladığında bu adrese anlık fotoğraf, ekran görüntüsü, konum ve sistem raporu gönderecektir.
                </p>
            </div>
        </body>
        </html>
        """
        return self._send(subject, html_body)

    def send_security_alert(self, reason, system_stats=None, location_info=None, image_bytes=None, screenshot_bytes=None, is_delayed=False):
        """Güvenlik ihlali veya sistem uyarısı olduğunda zengin HTML e-postası gönderir."""
        now_str = datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        prefix = "🚨 ACİL ALARM" if not is_delayed else "📬 KUYRUKTAN GECİKMELİ ALARM"
        subject = f"{prefix}: {reason} ({now_str})"
        
        stats_html = ""
        if system_stats:
            stats_html = f"""
            <div style="background: #fff3bf; border-left: 4px solid #f59f00; padding: 12px; margin: 15px 0; border-radius: 4px; font-size: 14px;">
                <b>🖥️ Sistem Durumu:</b><br>
                • CPU Kullanımı: <b>%{system_stats.get('cpu', 'N/A')}</b><br>
                • RAM Kullanımı: <b>%{system_stats.get('ram', 'N/A')}</b><br>
                • Pil / Şarj Durumu: <b>{system_stats.get('battery', 'N/A')}</b>
            </div>
            """

        location_html = ""
        if location_info and location_info.get("maps_url"):
            maps_url = location_info.get("maps_url")
            city = location_info.get("city", "Bilinmiyor")
            country = location_info.get("country", "")
            source = location_info.get("source", "")
            location_html = f"""
            <div style="background: #e7f5ff; border: 1px solid #74c0fc; padding: 14px; margin: 15px 0; border-radius: 6px; font-size: 14px;">
                <b style="color: #1971c2; font-size: 15px;">📍 Bilgisayarın Konumu:</b><br>
                • Bölge: <b>{city}, {country}</b> ({source})<br>
                <div style="margin-top: 10px;">
                    <a href="{maps_url}" target="_blank" style="background-color: #1c7ed6; color: white; padding: 8px 16px; text-decoration: none; border-radius: 5px; font-weight: bold; font-size: 13px; display: inline-block;">
                        🗺️ Google Haritalar'da Canlı Konumu Gör
                    </a>
                </div>
            </div>
            """

        image_html = ""
        if image_bytes:
            image_html = """
            <div style="margin-top: 20px; text-align: center;">
                <h3 style="color: #c92a2a; margin-bottom: 8px;">📸 Olay Anında Çekilen Webcam Görüntüsü:</h3>
                <img src="cid:security_snapshot" style="max-width: 100%; border: 3px solid #fa5252; border-radius: 8px;" />
            </div>
            """

        screenshot_html = ""
        if screenshot_bytes:
            screenshot_html = """
            <div style="margin-top: 20px; text-align: center;">
                <h3 style="color: #1971c2; margin-bottom: 8px;">🖥️ Olay Anında Açık Olan Ekran Görüntüsü:</h3>
                <img src="cid:security_screenshot" style="max-width: 100%; border: 3px solid #4dabf7; border-radius: 8px;" />
            </div>
            """

        delayed_badge = ""
        if is_delayed:
            delayed_badge = """
            <div style="background-color: #fff4e6; border: 1px solid #ffd8a8; color: #d9480f; padding: 8px 12px; border-radius: 4px; margin-bottom: 15px; font-size: 13px;">
                ℹ️ <b>Çevrimdışı Kayıt:</b> Bu olay internet kesintisi anında gerçekleşmiş ve yerel SQLite veritabanına kaydedilmişti. İnternet bağlantısı sağlandığı için şimdi iletildi.
            </div>
            """

        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; background-color: #1a1a1a; padding: 20px; color: #333;">
            <div style="max-width: 650px; margin: auto; background: #ffffff; border-radius: 10px; padding: 25px; box-shadow: 0 4px 20px rgba(0,0,0,0.5);">
                {delayed_badge}
                <div style="background-color: #e03131; color: white; padding: 12px 18px; border-radius: 8px; margin-bottom: 20px;">
                    <h2 style="margin: 0; font-size: 20px;">🚨 PC GÜVENLİK ALARMI</h2>
                </div>
                <p style="font-size: 16px;">
                    Bilgisayarınızda aşağıdaki güvenlik / konum olayı tespit edildi:
                </p>
                <div style="background: #ffe3e3; border: 1px solid #ffa8a8; padding: 12px; border-radius: 6px; font-size: 15px; color: #c92a2a;">
                    <b>⚠️ Olay Türü:</b> {reason}<br>
                    <b>🕒 Zaman:</b> {now_str}
                </div>
                {location_html}
                {stats_html}
                {image_html}
                {screenshot_html}
                <hr style="border: none; border-top: 1px solid #e9ecef; margin: 25px 0;">
                <p style="color: #868e96; font-size: 12px; text-align: center;">
                    Bu e-posta PC Güvenlik & Nöbetçi Botu tarafından otomatik oluşturulmuştur.
                </p>
            </div>
        </body>
        </html>
        """
        return self._send(subject, html_body, image_bytes, screenshot_bytes)

    def _send(self, subject, html_content, image_bytes=None, screenshot_bytes=None):
        if not self.sender_email or not self.app_password:
            return False, "Gönderici e-posta veya Uygulama Şifresi boş bırakılamaz!"
        
        target = self.receiver_email if self.receiver_email else self.sender_email

        msg = MIMEMultipart()
        msg['From'] = f"PC Nöbetçi Bot <{self.sender_email}>"
        msg['To'] = target
        msg['Subject'] = subject

        msg.attach(MIMEText(html_content, 'html', 'utf-8'))

        if image_bytes:
            img_part = MIMEImage(image_bytes, name="guvenlik_snapshot.jpg")
            img_part.add_header('Content-ID', '<security_snapshot>')
            img_part.add_header('Content-Disposition', 'inline', filename="guvenlik_snapshot.jpg")
            msg.attach(img_part)

        if screenshot_bytes:
            screen_part = MIMEImage(screenshot_bytes, name="ekran_goruntusu.jpg")
            screen_part.add_header('Content-ID', '<security_screenshot>')
            screen_part.add_header('Content-Disposition', 'inline', filename="ekran_goruntusu.jpg")
            msg.attach(screen_part)

        try:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context, timeout=10) as server:
                server.login(self.sender_email, self.app_password)
                server.send_message(msg)
            return True, "E-posta başarıyla gönderildi!"
        except smtplib.SMTPAuthenticationError:
            return False, "Gmail Giriş Başarısız! Lütfen 16 haneli 'Google Uygulama Şifrenizi' kontrol edin."
        except Exception as e:
            return False, f"E-posta gönderme hatası (İnternet yok veya zaman aşımı): {str(e)}"
