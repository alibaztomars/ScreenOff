import os
import sys
import ctypes
import json
import pystray
from pystray import MenuItem as item
from threading import Thread
from PIL import Image
import keyboard
import tkinter as tk
from tkinter import messagebox
import time  # Gecikme için

PROGRAM_NAME = "ScreenOff"
CONFIG_FILE = os.path.join(os.getenv('APPDATA'), PROGRAM_NAME, "config.json")

class ScreenOffApp:
    def __init__(self):
        self.check_first_run()
        self.load_config()
        self.create_tray_icon()
        self.register_hotkey()

    def check_first_run(self):
        app_dir = os.path.join(os.getenv('APPDATA'), PROGRAM_NAME)
        if not os.path.exists(os.path.join(app_dir, ".firstrun")):
            self.show_info()
            os.makedirs(app_dir, exist_ok=True)
            open(os.path.join(app_dir, ".firstrun"), 'w').close()

    def show_info(self):
        root = tk.Tk()
        root.withdraw()
        messagebox.showinfo(
            PROGRAM_NAME,
            "ScreenOff - Ekran Kontrol Programı\n\n"
            "Bu program belirlediğiniz bir tuş kombinasyonu ile ekranınızı kapatmanızı sağlar.\n"
            "Sistem tepsisinde çalışır ve minimum kaynak tüketir.\n\n"
            "Ayarlara sağ tıklayarak ulaşabilirsiniz."
        )
        root.destroy()

    def load_config(self):
        self.config = {"hotkey": "f12"}
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    self.config = json.load(f)
            except Exception as e:
                print("Config yükleme hatası:", e)

    def save_config(self):
        with open(CONFIG_FILE, 'w') as f:
            json.dump(self.config, f)

    def create_tray_icon(self):
        image = Image.new('RGB', (64, 64), color='white')
        menu = (
            item('Ayarlar', self.show_settings),
            item('Çıkış', self.quit_app)
        )
        self.tray = pystray.Icon(PROGRAM_NAME, image, PROGRAM_NAME, menu)
        Thread(target=self.tray.run, daemon=True).start()

    def show_settings(self, icon, item):
        self.settings_window = tk.Tk()
        self.settings_window.title("Ayarlar")
        
        tk.Label(self.settings_window, text="Kısayol Tuşu:").grid(row=0, column=0, padx=10, pady=10)
        self.key_entry = tk.Entry(self.settings_window, width=20)
        self.key_entry.insert(0, self.config['hotkey'])
        self.key_entry.grid(row=0, column=1, padx=10, pady=10)
        
        self.key_entry.bind("<KeyPress>", self.update_hotkey_preview)
        tk.Button(self.settings_window, text="Kaydet", command=self.save_settings).grid(row=1, column=1, pady=10)
        
        self.settings_window.mainloop()

    def update_hotkey_preview(self, event):
        self.key_entry.delete(0, tk.END)
        self.key_entry.insert(0, event.keysym.lower())

    def save_settings(self):
        new_hotkey = self.key_entry.get().lower()
        if new_hotkey != self.config['hotkey']:
            self.config['hotkey'] = new_hotkey
            self.save_config()
            self.register_hotkey()
        self.settings_window.destroy()

    def register_hotkey(self):
        keyboard.unhook_all()
        keyboard.add_hotkey(self.config['hotkey'], self.turn_off_screen)

    def turn_off_screen(self):
        # Tuşa basıldığında kısa bir gecikme ekleyip ekran kapatma işlemini ayrı iş parçacığında çalıştırıyoruz.
        Thread(target=self._delayed_turn_off, daemon=True).start()

    def _delayed_turn_off(self):
        time.sleep(0.3)  # 300 milisaniye gecikme; sistemin tuş basımından kaynaklı uyandırma etkisini azaltır.
        # Windows API kullanarak ekran kapatma:
        ctypes.windll.user32.SendMessageW(0xFFFF, 0x0112, 0xF170, 2)

    def quit_app(self, icon, item):
        self.tray.stop()
        os._exit(0)

if __name__ == "__main__":
    # Yönetici izni kontrolü (Admin olmadan çalışmaz)
    if not ctypes.windll.shell32.IsUserAnAdmin():
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, " ".join(sys.argv), None, 1
        )
        sys.exit()
    
    ScreenOffApp()
    keyboard.wait()
