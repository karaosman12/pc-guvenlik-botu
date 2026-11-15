import time
import math
import os
import io
import ctypes
import threading
import datetime
import psutil
import winsound
from PIL import ImageGrab

try:
    import cv2
except ImportError:
    cv2 = None

from database import SecurityDatabase
from location import LocationService

VK_F9 = 0x78

class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]

class SentinelGuard:
    """Sistem nöbetçi motoru: Hareket, temas, boşta kalma ve pil takibi sağlar."""

    def __init__(self, notifier, log_callback=None, preview_callback=None, queue_callback=None, disarm_callback=None):
        self.notifier = notifier
        self.db = SecurityDatabase()
        self.location_service = LocationService()

        self.log_callback = log_callback or (lambda msg: None)
        self.preview_callback = preview_callback or (lambda img_bytes: None)
        self.queue_callback = queue_callback or (lambda count: None)
        self.disarm_callback = disarm_callback or (lambda: None)

        self.enable_webcam = True
        self.enable_mouse = True
        self.enable_screenshot = True
        self.enable_siren = False
        self.enable_idle_alert = True
        self.enable_battery_alert = True
        self.enable_system = True

        self.disarm_grace_seconds = 5
        self.idle_limit_seconds = 3600
        self.battery_limit_percent = 10
        self.cooldown_seconds = 45
        self.motion_threshold = 4000

        self._running = False
        self._thread = None
        self._queue_thread = None
        self._last_alert_time = 0
        self._last_mouse_pos = None

        self._idle_alert_sent = False
        self._battery_alert_sent = False
        self._in_grace_period = False

    def start(self, countdown=5):
        """Nöbetçi döngüsünü başlatır."""
        if self._running:
            return
        
        self._running = True
        self._idle_alert_sent = False
        self._battery_alert_sent = False
        self._in_grace_period = False

        self._queue_thread = threading.Thread(target=self._queue_flush_worker, daemon=True)
        self._queue_thread.start()

        self._thread = threading.Thread(target=self._run_loop, args=(countdown,), daemon=True)
        self._thread.start()

    def stop(self):
        """Nöbetçi döngüsünü durdurur."""
        self._running = False
        self._in_grace_period = False
        self.log("🛑 Nöbet sonlandırıldı.")

    def log(self, message):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.log_callback(f"[{timestamp}] {message}")

    def _is_f9_pressed(self):
        return bool(ctypes.windll.user32.GetAsyncKeyState(VK_F9) & 0x8000)

    def _get_mouse_position(self):
        pt = POINT()
        ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
        return (pt.x, pt.y)

    def _get_idle_seconds(self):
        try:
            lii = LASTINPUTINFO()
            lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
            if ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii)):
                current_ticks = ctypes.windll.kernel32.GetTickCount()
                millis = current_ticks - lii.dwTime
                return max(0, millis / 1000.0)
        except Exception:
            pass
        return 0

    def _get_system_stats(self):
        try:
            cpu = psutil.cpu_percent(interval=None)
            ram = psutil.virtual_memory().percent
            battery = psutil.sensors_battery()
            battery_str = "Masaüstü / Şarjda"
            is_plugged = True
            percent = 100
            if battery:
                is_plugged = battery.power_plugged
                percent = battery.percent
                plugged_str = "Prizde" if is_plugged else "Pilde"
                battery_str = f"%{percent} ({plugged_str})"
            return {"cpu": cpu, "ram": ram, "battery": battery_str, "battery_percent": percent, "is_plugged": is_plugged}
        except Exception:
            return {"cpu": "N/A", "ram": "N/A", "battery": "N/A", "battery_percent": 100, "is_plugged": True}

    def _capture_webcam_frame(self, cap):
        if not self.enable_webcam or cap is None or not cap.isOpened():
            return None
        try:
            ret, frame = cap.read()
            if not ret or frame is None:
                return None
            success, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            if success:
                return buffer.tobytes()
        except Exception:
            pass
        return None

    def _capture_screen_bytes(self):
        if not self.enable_screenshot:
            return None
        try:
            screen = ImageGrab.grab()
            screen.thumbnail((1280, 720))
            buf = io.BytesIO()
            screen.save(buf, format="JPEG", quality=80)
            return buf.getvalue()
        except Exception:
            return None

    def _play_siren(self):
        if not self.enable_siren:
            return
        def _beep():
            try:
                for _ in range(5):
                    winsound.Beep(2500, 300)
                    winsound.Beep(1800, 300)
            except Exception:
                pass
        threading.Thread(target=_beep, daemon=True).start()

    def _handle_mouse_with_grace_period(self, cap):
        now = time.time()
        if now - self._last_alert_time < self.cooldown_seconds:
            self._last_mouse_pos = self._get_mouse_position()
            return

        if self._in_grace_period:
            return
        self._in_grace_period = True

        self.log(f"⚠️ Bilgisayara dokunuldu! Sahip doğrulaması için [F9] tuşuna basın! ({self.disarm_grace_seconds} sn)...")

        start_time = time.time()
        disarmed = False

        while time.time() - start_time < self.disarm_grace_seconds:
            if not self._running:
                self._in_grace_period = False
                return
            
            if self._is_f9_pressed():
                disarmed = True
                break

            time.sleep(0.08)

        self._in_grace_period = False
        self._last_mouse_pos = self._get_mouse_position()

        if disarmed:
            self.log("✅ SAHİP DOĞRULANDI (F9 tuşuna basıldı). Nöbet güvenle kapatıldı.")
            self.stop()
            self.disarm_callback()
            return
        
        self.log("🚨 DOĞRULAMA YAPILMADI (F9 basılmadı)! Yetkisiz erişim alarmı tetiklendi!")
        cam_bytes = self._capture_webcam_frame(cap)
        screen_bytes = self._capture_screen_bytes()
        self._trigger_alert("Yetkisiz Kullanıcı Teması (F9 Doğrulaması Başarısız)", cam_bytes, screen_bytes)

    def _trigger_alert(self, reason, image_bytes=None, screenshot_bytes=None, force=False):
        now = time.time()
        if not force and (now - self._last_alert_time < self.cooldown_seconds):
            remaining = int(self.cooldown_seconds - (now - self._last_alert_time))
            self.log(f"⚠️ Olay algılandı ({reason}) ancak cooldown devrede ({remaining}s).")
            return

        self._last_alert_time = now
        self.log(f"🚨 ALARM TETİKLENDİ: {reason}!")

        if image_bytes:
            self.preview_callback(image_bytes)
        elif screenshot_bytes:
            self.preview_callback(screenshot_bytes)

        self._play_siren()

        stats = self._get_system_stats()
        loc = self.location_service.fetch_current_location()

        event_id, _, _ = self.db.save_event(
            event_type=reason,
            image_bytes=image_bytes,
            screenshot_bytes=screenshot_bytes,
            location_info=loc,
            system_stats=stats,
            email_status="QUEUED"
        )
        self.log(f"💾 Olay ve görseller yerel SQLite'a kaydedildi (Olay ID: #{event_id}).")
        self.queue_callback(self.db.get_unsent_count())

        def _dispatch():
            ok, msg = self.notifier.send_security_alert(
                reason=reason,
                system_stats=stats,
                location_info=loc,
                image_bytes=image_bytes,
                screenshot_bytes=screenshot_bytes
            )
            if ok:
                self.db.mark_event_sent(event_id)
                self.log(f"📧 Gmail bildirimi, görseller ve konum başarıyla iletildi! (#{event_id})")
            else:
                self.log(f"⚠️ İnternet/Gönderim sorunu ({msg}). Olay çevrimdışı kuyruğa alındı.")
            self.queue_callback(self.db.get_unsent_count())

        threading.Thread(target=_dispatch, daemon=True).start()

    def _queue_flush_worker(self):
        while self._running:
            time.sleep(30)
            unsent = self.db.get_unsent_events()
            if not unsent:
                continue

            self.log(f"🔄 Çevrimdışı kuyruk kontrol ediliyor ({len(unsent)} bekleyen alarm)...")
            for item in unsent:
                if not self._running:
                    break

                img_bytes = None
                img_path = item.get("image_path")
                if img_path and os.path.exists(img_path):
                    try:
                        with open(img_path, "rb") as f:
                            img_bytes = f.read()
                    except Exception:
                        pass

                screen_bytes = None
                screen_path = item.get("screenshot_path")
                if screen_path and os.path.exists(screen_path):
                    try:
                        with open(screen_path, "rb") as f:
                            screen_bytes = f.read()
                    except Exception:
                        pass

                stats = {
                    "cpu": item.get("cpu_percent"),
                    "ram": item.get("ram_percent"),
                    "battery": item.get("battery_status")
                }
                loc = {
                    "city": item.get("location_city"),
                    "maps_url": item.get("location_maps_url"),
                    "source": item.get("location_source")
                }

                ok, _ = self.notifier.send_security_alert(
                    reason=item.get("event_type"),
                    system_stats=stats,
                    location_info=loc,
                    image_bytes=img_bytes,
                    screenshot_bytes=screen_bytes,
                    is_delayed=True
                )
                if ok:
                    self.db.mark_event_sent(item["id"])
                    self.log(f"✅ Kuyruktaki olay #{item['id']} internet gelince başarıyla iletildi!")
                    self.queue_callback(self.db.get_unsent_count())
                    time.sleep(2)
                else:
                    break

    def _run_loop(self, countdown):
        for i in range(countdown, 0, -1):
            if not self._running:
                return
            self.log(f"⏳ Nöbet başlıyor... ({i} saniye içinde ayrılın)")
            time.sleep(1)

        mode_str = "KÜTÜPHANE MODU (Kamera Kapalı)" if not self.enable_webcam else "TAM NÖBETÇİ MODU (Kamera Açık)"
        self.log(f"🛡️ NÖBET DEVREDE! [{mode_str}] İptal tuşu: [F9]")
        self._last_mouse_pos = self._get_mouse_position()

        cap = None
        prev_gray = None
        if self.enable_webcam and cv2 is not None:
            try:
                cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
                if not cap.isOpened():
                    self.log("⚠️ Webcam bulunamadı. Yalnızca temas ve ekran takibi devrede.")
                    cap = None
                else:
                    self.log("📷 Webcam hareket sensörü hazır.")
            except Exception as e:
                self.log(f"⚠️ Kamera hatası: {e}")
                cap = None

        system_check_interval = 8
        last_system_check = time.time()
        last_location_cache_time = time.time()

        threading.Thread(target=self.location_service.fetch_current_location, daemon=True).start()

        while self._running:
            if self._is_f9_pressed():
                self.log("✅ [F9] kısayoluna basıldı! Nöbet güvenle sonlandırıldı.")
                self.stop()
                self.disarm_callback()
                break

            idle_secs = self._get_idle_seconds()
            if self.enable_idle_alert:
                if idle_secs >= self.idle_limit_seconds:
                    if not self._idle_alert_sent:
                        self._idle_alert_sent = True
                        hours = round(idle_secs / 3600, 1)
                        self.log(f"⏰ PC {hours} saattir kullanılmıyor! Unutulma alarmı veriliyor.")
                        cam_bytes = self._capture_webcam_frame(cap)
                        screen_bytes = self._capture_screen_bytes()
                        self._trigger_alert(f"PC {hours} Saattir Kullanılmadı (Kayıp/Unutulma Alarmı)", cam_bytes, screen_bytes, force=True)
                else:
                    if idle_secs < 10 and self._idle_alert_sent:
                        self._idle_alert_sent = False

            if self.enable_mouse and not self._in_grace_period:
                cur_mouse = self._get_mouse_position()
                if self._last_mouse_pos:
                    dx = cur_mouse[0] - self._last_mouse_pos[0]
                    dy = cur_mouse[1] - self._last_mouse_pos[1]
                    dist = math.sqrt(dx * dx + dy * dy)
                    if dist > 35:
                        self._handle_mouse_with_grace_period(cap)
                        if not self._running:
                            break
                self._last_mouse_pos = cur_mouse

            if self.enable_webcam and cap is not None and cv2 is not None:
                ret, frame = cap.read()
                if ret and frame is not None:
                    resized = cv2.resize(frame, (640, 480))
                    gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
                    gray = cv2.GaussianBlur(gray, (21, 21), 0)

                    if prev_gray is None:
                        prev_gray = gray
                    else:
                        frame_delta = cv2.absdiff(prev_gray, gray)
                        thresh = cv2.threshold(frame_delta, 25, 255, cv2.THRESH_BINARY)[1]
                        thresh = cv2.dilate(thresh, None, iterations=2)
                        
                        contours, _ = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                        motion_detected = any(cv2.contourArea(c) > self.motion_threshold for c in contours)

                        if motion_detected:
                            self.log("👤 Kamera Önünde Hareket Algılandı!")
                            _, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                            cam_bytes = buffer.tobytes()
                            screen_bytes = self._capture_screen_bytes()
                            self._trigger_alert("Webcam Hareket Sensörü Tetiklendi", cam_bytes, screen_bytes)

                        prev_gray = gray

            now_time = time.time()
            if now_time - last_system_check > system_check_interval:
                last_system_check = now_time
                stats = self._get_system_stats()

                if self.enable_battery_alert:
                    if not stats["is_plugged"] and stats["battery_percent"] <= self.battery_limit_percent:
                        if not self._battery_alert_sent:
                            self._battery_alert_sent = True
                            self.log(f"🔋 Kritik Şarj: %{stats['battery_percent']}! Konum iletiliyor.")
                            cam_bytes = self._capture_webcam_frame(cap)
                            screen_bytes = self._capture_screen_bytes()
                            self._trigger_alert(f"Kritik Düşük Şarj (%{stats['battery_percent']}) - PC Kapanmak Üzere!", cam_bytes, screen_bytes, force=True)
                    elif stats["is_plugged"] or stats["battery_percent"] > (self.battery_limit_percent + 5):
                        self._battery_alert_sent = False

                if self.enable_system and isinstance(stats.get('cpu'), (int, float)) and stats['cpu'] > 95:
                    self.log(f"🔥 Aşırı Yüksek CPU: %{stats['cpu']}")
                    cam_bytes = self._capture_webcam_frame(cap)
                    screen_bytes = self._capture_screen_bytes()
                    self._trigger_alert(f"Aşırı Yüksek CPU Kullanımı (%{stats['cpu']})", cam_bytes, screen_bytes)

            if now_time - last_location_cache_time > 300:
                last_location_cache_time = now_time
                threading.Thread(target=self.location_service.fetch_current_location, daemon=True).start()

            time.sleep(0.15)

        if cap is not None:
            cap.release()
