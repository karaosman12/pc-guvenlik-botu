import os
import json
import time
import io
import threading
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
from PIL import Image, ImageTk
import pystray
from pystray import MenuItem as item

from mailer import GmailNotifier
from sentinel import SentinelGuard
from database import SecurityDatabase
from location import LocationService

BASE_DIR = os.path.dirname(__file__)
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
ICON_ICO = os.path.join(BASE_DIR, "icon.ico")
ICON_PNG = os.path.join(BASE_DIR, "icon.png")

class SentinelApp(ctk.CTk):
    """Masaüstü Grafik Arayüzü (CustomTkinter tabanlı)."""

    def __init__(self):
        super().__init__()

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.title("PC Güvenlik & Nöbetçi Botu (Sentinel Pro)")
        self.geometry("980x820")
        self.minsize(920, 740)

        if os.path.exists(ICON_ICO):
            try:
                self.iconbitmap(ICON_ICO)
            except Exception:
                pass

        self.db = SecurityDatabase()
        self.notifier = GmailNotifier()
        self.location_service = LocationService()

        self.guard = SentinelGuard(
            notifier=self.notifier,
            log_callback=self.add_log,
            preview_callback=self.update_preview,
            queue_callback=self.update_queue_badge,
            disarm_callback=self._on_disarm_success
        )

        self.is_running = False
        self.password_visible = False
        self.tray_icon = None
        self._current_ctk_preview = None

        self._build_ui()
        self._load_config()
        self._check_initial_status()

        self.protocol("WM_DELETE_WINDOW", self._on_window_close)

    def _build_ui(self):
        header_frame = ctk.CTkFrame(self, corner_radius=10, fg_color="#182234")
        header_frame.pack(fill="x", padx=15, pady=(12, 8))

        top_row = ctk.CTkFrame(header_frame, fg_color="transparent")
        top_row.pack(fill="x", padx=15, pady=(8, 2))

        title_lbl = ctk.CTkLabel(
            top_row, 
            text="🛡️ PC GÜVENLİK & NÖBETÇİ BOTU (PRO)", 
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="#4dabf7"
        )
        title_lbl.pack(side="left")

        right_btns = ctk.CTkFrame(top_row, fg_color="transparent")
        right_btns.pack(side="right")

        self.lbl_queue_badge = ctk.CTkLabel(
            right_btns,
            text="💾 Kuyruk: 0",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#ced4da",
            fg_color="#2b303c",
            corner_radius=6,
            padx=10,
            pady=4
        )
        self.lbl_queue_badge.pack(side="left", padx=(0, 8))

        self.btn_hide_tray = ctk.CTkButton(
            right_btns,
            text="🔽 Tepsiye Gizle",
            width=130,
            height=28,
            fg_color="#343a40",
            hover_color="#495057",
            command=self._minimize_to_tray
        )
        self.btn_hide_tray.pack(side="left")

        self.lbl_loc_banner = ctk.CTkLabel(
            header_frame, 
            text="📍 Konum: Tespit ediliyor...",
            font=ctk.CTkFont(size=12),
            text_color="#74c0fc"
        )
        self.lbl_loc_banner.pack(anchor="w", padx=15, pady=(0, 8))

        main_container = ctk.CTkFrame(self, fg_color="transparent")
        main_container.pack(fill="both", expand=True, padx=15, pady=4)

        # Sol Panel (Ayarlar)
        left_panel = ctk.CTkFrame(main_container, width=430, corner_radius=10)
        left_panel.pack(side="left", fill="both", padx=(0, 10), pady=0)

        gmail_card = ctk.CTkFrame(left_panel, corner_radius=8, fg_color="#1e1e24")
        gmail_card.pack(fill="x", padx=10, pady=(10, 8))

        ctk.CTkLabel(
            gmail_card, 
            text="✉️ Gmail Bildirim Ayarları", 
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#ffd43b"
        ).pack(anchor="w", padx=10, pady=(8, 6))

        ctk.CTkLabel(gmail_card, text="Gönderen Gmail:", font=ctk.CTkFont(size=11)).pack(anchor="w", padx=10)
        self.entry_sender = ctk.CTkEntry(gmail_card, placeholder_text="ornek@gmail.com", height=28)
        self.entry_sender.pack(fill="x", padx=10, pady=(2, 6))

        ctk.CTkLabel(gmail_card, text="16 Haneli Google Uygulama Şifresi:", font=ctk.CTkFont(size=11)).pack(anchor="w", padx=10)
        
        pass_row = ctk.CTkFrame(gmail_card, fg_color="transparent")
        pass_row.pack(fill="x", padx=10, pady=(2, 6))
        
        self.entry_password = ctk.CTkEntry(pass_row, placeholder_text="abcd efgh ijkl mnop", show="*", height=28)
        self.entry_password.pack(side="left", fill="x", expand=True, padx=(0, 6))

        self.btn_toggle_pass = ctk.CTkButton(pass_row, text="👁️", width=34, height=28, command=self._toggle_password)
        self.btn_toggle_pass.pack(side="right")

        ctk.CTkLabel(gmail_card, text="Alıcı Gmail (Boşsa kendine atar):", font=ctk.CTkFont(size=11)).pack(anchor="w", padx=10)
        self.entry_receiver = ctk.CTkEntry(gmail_card, placeholder_text="alici@gmail.com (Opsiyonel)", height=28)
        self.entry_receiver.pack(fill="x", padx=10, pady=(2, 8))

        btn_row = ctk.CTkFrame(gmail_card, fg_color="transparent")
        btn_row.pack(fill="x", padx=10, pady=(0, 8))

        self.btn_test_mail = ctk.CTkButton(
            btn_row, 
            text="🧪 Test Maili At", 
            height=28,
            fg_color="#3b5bdb", 
            hover_color="#2f49b0", 
            command=self._on_test_mail
        )
        self.btn_test_mail.pack(side="left", fill="x", expand=True, padx=(0, 4))

        self.btn_save_config = ctk.CTkButton(
            btn_row, 
            text="💾 Kaydet", 
            height=28,
            fg_color="#2b8a3e", 
            hover_color="#237032", 
            command=self._save_config
        )
        self.btn_save_config.pack(side="right", fill="x", expand=True, padx=(4, 0))

        # Tetikleyiciler
        trigger_card = ctk.CTkFrame(left_panel, corner_radius=8, fg_color="#1e1e24")
        trigger_card.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        ctk.CTkLabel(
            trigger_card, 
            text="⚙️ Alarm & Kütüphane Modu", 
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#ffd43b"
        ).pack(anchor="w", padx=10, pady=(8, 6))

        self.chk_library_mode = ctk.CTkCheckBox(
            trigger_card, 
            text="📚 Kütüphane Modu (Kamerayı Kapat, Sadece Teması İzle)",
            text_color="#74c0fc",
            font=ctk.CTkFont(weight="bold"),
            command=self._on_library_mode_toggle
        )
        self.chk_library_mode.pack(anchor="w", padx=10, pady=4)

        self.chk_webcam = ctk.CTkCheckBox(trigger_card, text="📸 Webcam Hareket Sensörü (Fotoğraflı)")
        self.chk_webcam.pack(anchor="w", padx=10, pady=4)
        self.chk_webcam.select()

        self.chk_mouse = ctk.CTkCheckBox(trigger_card, text="🖱️ Yetkisiz Fare / İmleç Hareketi")
        self.chk_mouse.pack(anchor="w", padx=10, pady=4)
        self.chk_mouse.select()

        self.chk_screenshot = ctk.CTkCheckBox(trigger_card, text="🖥️ Ekran Görüntüsü (Screenshot) Al ve Maile Ekle")
        self.chk_screenshot.pack(anchor="w", padx=10, pady=4)
        self.chk_screenshot.select()

        self.chk_idle = ctk.CTkCheckBox(trigger_card, text="⏰ 1 Saat Boşta Kalma (Unutulma / Kayıp)")
        self.chk_idle.pack(anchor="w", padx=10, pady=4)
        self.chk_idle.select()

        self.chk_battery = ctk.CTkCheckBox(trigger_card, text="🔋 Kritik Düşük Şarj (%10 Altı ve Prizde Değilken)")
        self.chk_battery.pack(anchor="w", padx=10, pady=4)
        self.chk_battery.select()

        self.chk_siren = ctk.CTkCheckBox(
            trigger_card, 
            text="🔊 Sesli Siren Çal (Varsayılan: Kapalı - Kütüphane Güvenliği)",
            text_color="#ff8787"
        )
        self.chk_siren.pack(anchor="w", padx=10, pady=4)

        info_box = ctk.CTkFrame(trigger_card, fg_color="#182234", corner_radius=6)
        info_box.pack(fill="x", padx=10, pady=(6, 8))

        ctk.CTkLabel(
            info_box,
            text="⌨️ Masaya Dönüş İptal Tuşu: [ F9 ]",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#51cf66"
        ).pack(anchor="w", padx=8, pady=(4, 2))

        ctk.CTkLabel(
            info_box,
            text="Masaya dönünce 5 sn içinde [F9]'a basarsanız alarm iptal edilir.",
            font=ctk.CTkFont(size=11),
            text_color="#adb5bd"
        ).pack(anchor="w", padx=8, pady=(0, 4))

        time_row = ctk.CTkFrame(trigger_card, fg_color="transparent")
        time_row.pack(fill="x", padx=10, pady=(2, 6))

        ctk.CTkLabel(time_row, text="Hazırlık Gecikmesi (sn):", font=ctk.CTkFont(size=11)).grid(row=0, column=0, sticky="w", pady=2)
        self.entry_countdown = ctk.CTkEntry(time_row, width=50, height=24)
        self.entry_countdown.insert(0, "5")
        self.entry_countdown.grid(row=0, column=1, padx=6, pady=2)

        ctk.CTkLabel(time_row, text="Mail Bekleme Aralığı (sn):", font=ctk.CTkFont(size=11)).grid(row=1, column=0, sticky="w", pady=2)
        self.entry_cooldown = ctk.CTkEntry(time_row, width=50, height=24)
        self.entry_cooldown.insert(0, "45")
        self.entry_cooldown.grid(row=1, column=1, padx=6, pady=2)

        # Sağ Panel (Kontrol, Log & Önizleme)
        right_panel = ctk.CTkFrame(main_container, corner_radius=10)
        right_panel.pack(side="right", fill="both", expand=True, pady=0)

        status_box = ctk.CTkFrame(right_panel, corner_radius=8, fg_color="#182234")
        status_box.pack(fill="x", padx=10, pady=(10, 8))

        self.lbl_status = ctk.CTkLabel(
            status_box, 
            text="● DURUM: PASİF", 
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#fa5252"
        )
        self.lbl_status.pack(pady=(10, 4))

        self.btn_main_action = ctk.CTkButton(
            status_box, 
            text="🛡️ NÖBETİ BAŞLAT", 
            font=ctk.CTkFont(size=16, weight="bold"),
            height=44,
            fg_color="#2b8a3e", 
            hover_color="#237032",
            command=self._toggle_guard
        )
        self.btn_main_action.pack(fill="x", padx=12, pady=(0, 10))

        mid_frame = ctk.CTkFrame(right_panel, fg_color="transparent")
        mid_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        log_box = ctk.CTkFrame(mid_frame, corner_radius=8)
        log_box.pack(side="left", fill="both", expand=True, padx=(0, 8))

        ctk.CTkLabel(
            log_box, 
            text="📋 Canlı Olay & Depolama Günlüğü", 
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#ced4da"
        ).pack(anchor="w", padx=10, pady=(6, 4))

        self.txt_log = ctk.CTkTextbox(log_box, wrap="word", font=ctk.CTkFont(family="Consolas", size=11))
        self.txt_log.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        self.preview_box = ctk.CTkFrame(mid_frame, width=220, corner_radius=8, fg_color="#18181b")
        self.preview_box.pack(side="right", fill="y", padx=(0, 0))
        self.preview_box.pack_propagate(False)

        ctk.CTkLabel(
            self.preview_box, 
            text="📸 Son Alarm Görseli", 
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#adb5bd"
        ).pack(pady=(8, 4))

        self.lbl_preview = ctk.CTkLabel(
            self.preview_box, 
            text="(Henüz tetiklenmedi)", 
            text_color="#6c757d",
            font=ctk.CTkFont(size=11)
        )
        self.lbl_preview.pack(expand=True, fill="both", padx=8, pady=8)

    def _on_library_mode_toggle(self):
        if self.chk_library_mode.get():
            self.chk_webcam.deselect()
            self.chk_webcam.configure(state="disabled")
            self.chk_siren.deselect()
            self.add_log("📚 Kütüphane Modu devrede: Kamera kapatıldı, etraftaki hareketler yoksayılacak.")
        else:
            self.chk_webcam.configure(state="normal")
            self.chk_webcam.select()
            self.add_log("📷 Tam Nöbetçi Modu: Kamera hareket sensörü aktif edildi.")

    def _minimize_to_tray(self):
        self.withdraw()
        if not self.tray_icon:
            self._start_tray()
        else:
            self.tray_icon.visible = True
        self.add_log("🔽 Uygulama arka plana (sistem tepsisine) gizlendi.")

    def _show_from_tray(self):
        self.after(0, self.deiconify)
        self.after(0, self.lift)
        self.after(0, self.focus_force)

    def _start_tray(self):
        try:
            image = Image.open(ICON_PNG) if os.path.exists(ICON_PNG) else Image.new("RGB", (64, 64), color="blue")
            menu = (
                item("Pencereyi Göster", lambda: self._show_from_tray()),
                item("Nöbeti Başlat/Durdur", lambda: self.after(0, self._toggle_guard)),
                item("Tamamen Çıkış", lambda: self.after(0, self._quit_app))
            )
            self.tray_icon = pystray.Icon("PC Sentinel", image, "PC Güvenlik & Nöbetçi Botu", menu)
            threading.Thread(target=self.tray_icon.run, daemon=True).start()
        except Exception as e:
            self.add_log(f"Tepsi simgesi başlatılamadı: {e}")

    def _on_window_close(self):
        if self.is_running:
            res = messagebox.askyesno("PC Nöbetçi", "Nöbet halen aktif!\n\nProgramı arka planda (sistem tepsisinde) çalıştırmaya devam etmek ister misiniz?\n(Hayır derseniz tamamen kapanır)")
            if res:
                self._minimize_to_tray()
                return
        self._quit_app()

    def _quit_app(self):
        if self.is_running:
            self.guard.stop()
        if self.tray_icon:
            try:
                self.tray_icon.stop()
            except Exception:
                pass
        self.destroy()

    def _on_disarm_success(self):
        def _update():
            self.is_running = False
            self.lbl_status.configure(text="● DURUM: PASİF (F9 İle Çözüldü)", text_color="#51cf66")
            self.btn_main_action.configure(text="🛡️ NÖBETİ BAŞLAT", fg_color="#2b8a3e", hover_color="#237032")
        self.after(0, _update)

    def _check_initial_status(self):
        self.update_queue_badge(self.db.get_unsent_count())
        def _fetch_loc():
            loc = self.location_service.fetch_current_location()
            if loc and loc.get("city"):
                txt = f"📍 Konum: {loc.get('city')}, {loc.get('country')} ({loc.get('source')})"
                self.after(0, lambda: self.lbl_loc_banner.configure(text=txt))
        threading.Thread(target=_fetch_loc, daemon=True).start()

    def update_queue_badge(self, count):
        def _update():
            if count > 0:
                self.lbl_queue_badge.configure(
                    text=f"💾 Kuyruk: {count}", 
                    fg_color="#e8590c",
                    text_color="#ffffff"
                )
            else:
                self.lbl_queue_badge.configure(
                    text="💾 SQLite: Eşitlendi", 
                    fg_color="#2b303c",
                    text_color="#ced4da"
                )
        self.after(0, _update)

    def _toggle_password(self):
        self.password_visible = not self.password_visible
        if self.password_visible:
            self.entry_password.configure(show="")
            self.btn_toggle_pass.configure(text="🔒")
        else:
            self.entry_password.configure(show="*")
            self.btn_toggle_pass.configure(text="👁️")

    def add_log(self, text):
        def _append():
            try:
                self.txt_log.insert("end", text + "\n")
                self.txt_log.see("end")
            except Exception:
                pass
        self.after(0, _append)

    def update_preview(self, image_bytes):
        def _update():
            try:
                img = Image.open(io.BytesIO(image_bytes))
                img.thumbnail((200, 160))
                ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=img.size)
                self._current_ctk_preview = ctk_img
                self.lbl_preview.configure(image=ctk_img, text="")
            except Exception as e:
                self.add_log(f"Önizleme yüklenemedi: {e}")
        self.after(0, _update)

    def _save_config(self, show_msg=True):
        config_data = {
            "sender_email": self.entry_sender.get().strip(),
            "app_password": self.entry_password.get().strip(),
            "receiver_email": self.entry_receiver.get().strip(),
            "library_mode": bool(self.chk_library_mode.get()),
            "enable_webcam": bool(self.chk_webcam.get()),
            "enable_mouse": bool(self.chk_mouse.get()),
            "enable_screenshot": bool(self.chk_screenshot.get()),
            "enable_idle": bool(self.chk_idle.get()),
            "enable_battery": bool(self.chk_battery.get()),
            "enable_siren": bool(self.chk_siren.get()),
            "countdown": self.entry_countdown.get().strip(),
            "cooldown": self.entry_cooldown.get().strip()
        }
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(config_data, f, indent=4, ensure_ascii=False)
            if show_msg:
                messagebox.showinfo("Başarılı", "Ayarlar başarıyla kaydedildi!")
            self.add_log("💾 Ayarlar dosyaya kaydedildi.")
        except Exception as e:
            if show_msg:
                messagebox.showerror("Hata", f"Ayarlar kaydedilemedi: {e}")

    def _load_config(self):
        if not os.path.exists(CONFIG_FILE):
            self.add_log("ℹ️ Kayıtlı ayar bulunamadı. Lütfen bilgilerinizi giriniz.")
            return

        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)

            self.entry_sender.delete(0, "end")
            self.entry_sender.insert(0, cfg.get("sender_email", ""))

            self.entry_password.delete(0, "end")
            self.entry_password.insert(0, cfg.get("app_password", ""))

            self.entry_receiver.delete(0, "end")
            self.entry_receiver.insert(0, cfg.get("receiver_email", ""))

            if cfg.get("library_mode", False):
                self.chk_library_mode.select()
                self._on_library_mode_toggle()
            else:
                self.chk_library_mode.deselect()
                if cfg.get("enable_webcam", True):
                    self.chk_webcam.select()
                else:
                    self.chk_webcam.deselect()

            if cfg.get("enable_mouse", True):
                self.chk_mouse.select()
            else:
                self.chk_mouse.deselect()

            if cfg.get("enable_screenshot", True):
                self.chk_screenshot.select()
            else:
                self.chk_screenshot.deselect()

            if cfg.get("enable_idle", True):
                self.chk_idle.select()
            else:
                self.chk_idle.deselect()

            if cfg.get("enable_battery", True):
                self.chk_battery.select()
            else:
                self.chk_battery.deselect()

            if cfg.get("enable_siren", False):
                self.chk_siren.select()
            else:
                self.chk_siren.deselect()

            self.entry_countdown.delete(0, "end")
            self.entry_countdown.insert(0, cfg.get("countdown", "5"))

            self.entry_cooldown.delete(0, "end")
            self.entry_cooldown.insert(0, cfg.get("cooldown", "45"))

            self.add_log("✅ Kayıtlı ayarlar başarıyla yüklendi.")
        except Exception as e:
            self.add_log(f"⚠️ Ayarlar yüklenirken hata: {e}")

    def _apply_settings_to_guard(self):
        sender = self.entry_sender.get().strip()
        pwd = self.entry_password.get().strip()
        receiver = self.entry_receiver.get().strip()

        self.notifier.update_credentials(sender, pwd, receiver)

        if self.chk_library_mode.get():
            self.guard.enable_webcam = False
        else:
            self.guard.enable_webcam = bool(self.chk_webcam.get())

        self.guard.enable_mouse = bool(self.chk_mouse.get())
        self.guard.enable_screenshot = bool(self.chk_screenshot.get())
        self.guard.enable_idle_alert = bool(self.chk_idle.get())
        self.guard.enable_battery_alert = bool(self.chk_battery.get())
        self.guard.enable_siren = bool(self.chk_siren.get())
        self.guard.enable_system = True

        try:
            self.guard.cooldown_seconds = int(self.entry_cooldown.get().strip())
        except ValueError:
            self.guard.cooldown_seconds = 45

    def _on_test_mail(self):
        self._apply_settings_to_guard()
        if not self.notifier.sender_email or not self.notifier.app_password:
            messagebox.showwarning("Eksik Bilgi", "Lütfen önce Gönderen Gmail ve 16 haneli Uygulama Şifrenizi girin!")
            return

        self.add_log("📤 Test e-postası ve konum gönderiliyor, lütfen bekleyin...")
        self.btn_test_mail.configure(state="disabled", text="Gönderiliyor...")

        def _do_test():
            loc = self.location_service.fetch_current_location()
            success, msg = self.notifier.send_test_email(location_info=loc)
            self.btn_test_mail.configure(state="normal", text="🧪 Test Maili At")
            if success:
                self.add_log("🎉 Test maili başarıyla gönderildi! Gelen kutunuzu kontrol edin.")
                messagebox.showinfo("Başarılı", "Test maili başarıyla gönderildi!\nGelen kutunuzu (veya Spam klasörünü) kontrol edin.")
            else:
                self.add_log(f"❌ Test maili başarısız: {msg}")
                messagebox.showerror("Hata", f"Test maili gönderilemedi:\n{msg}")

        threading.Thread(target=_do_test, daemon=True).start()

    def _toggle_guard(self):
        if not self.is_running:
            self._apply_settings_to_guard()
            if not self.notifier.sender_email or not self.notifier.app_password:
                messagebox.showwarning("Eksik Bilgi", "Nöbeti başlatmadan önce Gmail ve Uygulama Şifrenizi girmelisiniz!")
                return

            self._save_config(show_msg=False)

            try:
                countdown_val = int(self.entry_countdown.get().strip())
            except ValueError:
                countdown_val = 5

            self.is_running = True
            self.lbl_status.configure(text="● DURUM: NÖBETTE - AKTİF", text_color="#51cf66")
            self.btn_main_action.configure(text="🛑 NÖBETİ DURDUR", fg_color="#e03131", hover_color="#c92a2a")

            self.guard.start(countdown=countdown_val)
        else:
            self.is_running = False
            self.guard.stop()
            self.lbl_status.configure(text="● DURUM: PASİF", text_color="#fa5252")
            self.btn_main_action.configure(text="🛡️ NÖBETİ BAŞLAT", fg_color="#2b8a3e", hover_color="#237032")

if __name__ == "__main__":
    app = SentinelApp()
    app.mainloop()
