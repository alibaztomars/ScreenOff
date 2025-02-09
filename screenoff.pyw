import os
import sys
import ctypes
import json
import logging
import pystray
from pystray import MenuItem as item
from threading import Thread
from PIL import Image
import keyboard
import tkinter as tk
from tkinter import messagebox, ttk
import time

PROGRAM_NAME = "ScreenOff"
APPDATA_DIR = os.path.join(os.getenv('APPDATA'), PROGRAM_NAME)
CONFIG_FILE = os.path.join(APPDATA_DIR, "config.json")
LOG_FILE = os.path.join(APPDATA_DIR, "screenoff.log")

# Uygulama dizini yoksa oluşturuluyor
os.makedirs(APPDATA_DIR, exist_ok=True)

# Logging yapılandırması
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename=LOG_FILE,
    filemode='a'
)

class ScreenOffApp:
    def __init__(self):
        logging.info("Uygulama başlatılıyor.")
        self.hotkey_handle = None  # Eklenen hotkey kaydını tutmak için
        self.check_first_run()
        self.load_config()
        self.create_tray_icon()
        self.register_hotkey()
        # Periyodik hotkey kontrolü için monitor thread’i başlatılıyor
        Thread(target=self.monitor_hotkey, daemon=True).start()

    def check_first_run(self):
        firstrun_flag = os.path.join(APPDATA_DIR, ".firstrun")
        if not os.path.exists(firstrun_flag):
            self.show_info()
            open(firstrun_flag, 'w').close()
            logging.info("İlk çalışma tespit edildi; bilgilendirme gösterildi.")

    def show_info(self):
        root = tk.Tk()
        root.withdraw()
        messagebox.showinfo(
            PROGRAM_NAME,
            "ScreenOff - Ekran Kontrol Programı\n\n"
            "Bu program, belirlediğiniz bir tuş kombinasyonu ile ekranınızı kapatmanızı sağlar.\n"
            "Sistem tepsisinde çalışır ve minimum kaynak tüketir.\n\n"
            "Ayarlar menüsünden tuş kombinasyonunu değiştirebilirsiniz."
        )
        root.destroy()

    def load_config(self):
        # Varsayılan konfigürasyon
        self.config = {"hotkey": "f12"}
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    self.config = json.load(f)
                logging.info("Konfigürasyon başarıyla yüklendi: %s", self.config)
            except Exception as e:
                logging.error("Konfigürasyon yükleme hatası: %s", e)

    def save_config(self):
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(self.config, f)
            logging.info("Konfigürasyon kaydedildi: %s", self.config)
        except Exception as e:
            logging.error("Konfigürasyon kaydetme hatası: %s", e)

    def create_tray_icon(self):
        # Tray ikonu için basit bir beyaz resim oluşturuluyor.
        image = Image.new('RGB', (64, 64), color='white')
        menu = (
            item('Ayarlar', self.show_settings),
            item('Çıkış', self.quit_app)
        )
        self.tray = pystray.Icon(PROGRAM_NAME, image, PROGRAM_NAME, menu)
        Thread(target=self.tray.run, daemon=True).start()
        logging.info("Sistem tepsi ikonu oluşturuldu ve çalıştırıldı.")

    def show_settings(self, icon, item):
        # Ayarlar penceresi ayrı bir Tk penceresi olarak oluşturuluyor.
        settings_window = tk.Tk()
        settings_window.title("Ayarlar - " + PROGRAM_NAME)
        settings_window.resizable(False, False)
        settings_window.geometry("300x150")
        
        # Pencere ortalanıyor
        settings_window.update_idletasks()
        x = (settings_window.winfo_screenwidth() - settings_window.winfo_reqwidth()) // 2
        y = (settings_window.winfo_screenheight() - settings_window.winfo_reqheight()) // 2
        settings_window.geometry(f"+{x}+{y}")

        # Modern görünümlü ttk widget'ları kullanılıyor.
        frame = ttk.Frame(settings_window, padding="10")
        frame.pack(expand=True, fill="both")

        # Başlık ve açıklama
        ttk.Label(frame, text="Kısayol Tuşunu Belirleyin", font=("Segoe UI", 10, "bold")).grid(row=0, column=0, columnspan=2, pady=(0,10))
        
        ttk.Label(frame, text="Kısayol Tuşu:").grid(row=1, column=0, padx=5, pady=5, sticky="e")
        self.key_entry = ttk.Entry(frame, width=20)
        self.key_entry.insert(0, self.config['hotkey'])
        self.key_entry.grid(row=1, column=1, padx=5, pady=5)
        self.key_entry.bind("<KeyPress>", self.update_hotkey_preview)

        # Butonlar
        button_frame = ttk.Frame(frame)
        button_frame.grid(row=2, column=0, columnspan=2, pady=10)
        save_btn = ttk.Button(button_frame, text="Kaydet", command=lambda: self.save_settings(settings_window))
        save_btn.pack(side="left", padx=(0,5))
        cancel_btn = ttk.Button(button_frame, text="İptal", command=settings_window.destroy)
        cancel_btn.pack(side="left", padx=(5,0))
        
        settings_window.mainloop()

    def update_hotkey_preview(self, event):
        # Girilen tuşu yakalayıp entry alanını güncelliyoruz.
        self.key_entry.delete(0, tk.END)
        self.key_entry.insert(0, event.keysym.lower())

    def save_settings(self, window):
        new_hotkey = self.key_entry.get().lower()
        if new_hotkey != self.config['hotkey']:
            self.config['hotkey'] = new_hotkey
            self.save_config()
            self.register_hotkey()
            logging.info("Yeni kısayol tuşu ayarlandı: %s", new_hotkey)
        window.destroy()

    def register_hotkey(self):
        # Sadece kendi kaydımızı kaldırıp, yeniden tanımlıyoruz.
        try:
            if self.hotkey_handle is not None:
                keyboard.remove_hotkey(self.hotkey_handle)
                logging.info("Önceki hotkey kaldırıldı.")
            self.hotkey_handle = keyboard.add_hotkey(self.config['hotkey'], self.turn_off_screen)
            logging.info("Hotkey '%s' kaydedildi.", self.config['hotkey'])
        except Exception as e:
            logging.error("Hotkey kaydı sırasında hata: %s", e)

    def monitor_hotkey(self):
        # Her 5 dakikada bir hotkey kaydını yenileyerek olası aksaklıkları önlüyoruz.
        while True:
            time.sleep(300)  # 300 saniye = 5 dakika
            self.register_hotkey()
            logging.info("Periyodik hotkey yenileme yapıldı.")

    def turn_off_screen(self):
        # Tuşa basıldığında kısa bir gecikme ekleyip ekran kapatma işlemini ayrı iş parçacığında çalıştırıyoruz.
        Thread(target=self._delayed_turn_off, daemon=True).start()
        logging.info("Turn off screen tetiklendi.")

    def _delayed_turn_off(self):
        time.sleep(0.3)  # 300 milisaniye gecikme
        try:
            # Windows API kullanarak ekran kapatma:
            ctypes.windll.user32.SendMessageW(0xFFFF, 0x0112, 0xF170, 2)
            logging.info("Ekran kapatma komutu gönderildi.")
        except Exception as e:
            logging.error("Ekran kapatma hatası: %s", e)

    def quit_app(self, icon, item):
        logging.info("Uygulama kapatılıyor.")
        self.tray.stop()
        os._exit(0)

if __name__ == "__main__":
    # Yönetici izni kontrolü (Admin olmadan çalışmaz)
    try:
        if not ctypes.windll.shell32.IsUserAnAdmin():
            logging.info("Yönetici izni mevcut değil. Yeniden yönetici olarak başlatılıyor...")
            ctypes.windll.shell32.ShellExecuteW(
                None, "runas", sys.executable, " ".join(sys.argv), None, 1
            )
            sys.exit()
    except Exception as e:
        logging.error("Yönetici kontrolü sırasında hata: %s", e)
        sys.exit()
    
    app = ScreenOffApp()
    # Program ana thread'i, keyboard modülü sayesinde aktif kalır.
    keyboard.wait()
