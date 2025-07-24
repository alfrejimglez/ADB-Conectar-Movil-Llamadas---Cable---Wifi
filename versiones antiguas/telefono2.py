import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import threading
import time
import re
from datetime import datetime

class ADBPhoneApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("📱 Teléfono ADB")
        self.geometry("900x500")
        self.resizable(False, False)

        self.current_device = None
        self.en_llamada = False
        self.error_activo = False
        self.call_start_time = None
        self.call_timer_running = False

        self.create_widgets()
        self.cargar_dispositivos()
        self.update_loop()

    def create_widgets(self):
        left_frame = ttk.Frame(self)
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)

        ttk.Label(left_frame, text="Dispositivo conectado").pack(anchor='w')
        self.device_combo = ttk.Combobox(left_frame, state='readonly')
        self.device_combo.pack(fill=tk.X, pady=5)
        self.device_combo.bind("<<ComboboxSelected>>", self.on_device_change)

        ttk.Label(left_frame, text="Número de teléfono").pack(anchor='w')
        self.number_entry = ttk.Entry(left_frame)
        self.number_entry.pack(fill=tk.X, pady=5)
        self.number_entry.bind("<Return>", lambda e: self.llamar())

        btn_frame = ttk.Frame(left_frame)
        btn_frame.pack(pady=10, fill=tk.X)

        self.call_btn = ttk.Button(btn_frame, text="📞 Llamar", command=self.llamar)
        self.call_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)

        self.hangup_btn = ttk.Button(btn_frame, text="📴 Colgar", command=self.colgar)
        self.hangup_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
        self.hangup_btn.state(['disabled'])

        self.restart_adb_btn = ttk.Button(btn_frame, text="♻️ Reiniciar ADB", command=self.adb_restart)
        self.restart_adb_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)

        self.call_timer_label = ttk.Label(btn_frame, text="⏱️ Duración: 00:00", font=("Arial", 10))
        self.call_timer_label.pack(side=tk.BOTTOM, pady=5)

        ttk.Separator(left_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)

        ttk.Label(left_frame, text="🔌 Conexión WiFi ADB").pack(anchor='w')
        ttk.Label(left_frame, text="IP del dispositivo (ej: 192.168.1.50)").pack(anchor='w')
        self.wifi_ip_entry = ttk.Entry(left_frame)
        self.wifi_ip_entry.pack(fill=tk.X, pady=5)
        self.connect_wifi_btn = ttk.Button(left_frame, text="🔗 Conectar WiFi", command=self.conectar_wifi)
        self.connect_wifi_btn.pack(pady=5)

        self.wifi_status_label = ttk.Label(left_frame, text="", foreground="blue")
        self.wifi_status_label.pack(anchor='w')

        self.battery_label = ttk.Label(left_frame, text="🔋 Batería: --%")
        self.battery_label.pack(pady=5, anchor='w')

        self.error_label = ttk.Label(left_frame, text="❌ Error al obtener batería", foreground="red")
        self.error_label.pack(pady=5, anchor='w')
        self.error_label.pack_forget()

        right_frame = ttk.Frame(self)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        ttk.Label(right_frame, text="📂 Historial").pack(anchor='w')
        self.historial_text = tk.Text(right_frame, height=30, width=50, state='disabled',
                                      bg='white', relief=tk.SOLID, borderwidth=1)
        self.historial_text.pack(fill=tk.BOTH, expand=True)

    def run_adb_command(self, args, timeout=10):
        try:
            result = subprocess.run(args, capture_output=True, text=True,
                                    timeout=timeout, encoding='utf-8', errors='replace')
            return result.stdout.strip()
        except Exception:
            return None

    def cargar_dispositivos(self):
        output = self.run_adb_command(['adb', 'devices'])
        if not output:
            self.device_combo['values'] = []
            self.device_combo.set('No conectado')
            self.current_device = None
            self.mostrar_error()
            self.ocultar_botones()
            return

        devices = [line.split('\t')[0] for line in output.splitlines()[1:] if 'device' in line]
        if not devices:
            self.device_combo['values'] = []
            self.device_combo.set('No conectado')
            self.current_device = None
            self.mostrar_error()
            self.ocultar_botones()
            return

        self.device_combo['values'] = devices
        if self.current_device not in devices:
            self.current_device = devices[0]
        self.device_combo.set(self.current_device)
        self.mostrar_botones()
        self.error_label.pack_forget()
        self.obtener_bateria()
        self.after(200, self.cargar_historial)

    def on_device_change(self, event=None):
        self.current_device = self.device_combo.get()
        self.obtener_bateria()
        self.cargar_historial()

    def obtener_bateria(self):
        if not self.current_device:
            return

        def task():
            output = self.run_adb_command(['adb', '-s', self.current_device, 'shell', 'dumpsys', 'battery'])
            if not output:
                self.after(0, self.mostrar_error)
                return

            match = re.search(r'level:\s*(\d+)', output)
            if match:
                level = match.group(1)
                self.after(0, lambda: self.battery_label.config(text=f"🔋 Batería: {level}%"))
                self.after(0, self.battery_label.pack)
                self.after(0, self.error_label.pack_forget)
                self.error_activo = False
            elif not self.error_activo:
                self.after(0, self.mostrar_error)
                self.error_activo = True

        threading.Thread(target=task, daemon=True).start()

    def mostrar_error(self):
        self.battery_label.pack_forget()
        self.error_label.pack()

    def mostrar_botones(self):
        self.call_btn.state(['!disabled'])
        self.hangup_btn.state(['!disabled' if self.en_llamada else 'disabled'])

    def ocultar_botones(self):
        self.call_btn.state(['disabled'])
        self.hangup_btn.state(['disabled'])

    def llamar(self):
        if not self.current_device:
            messagebox.showerror("Error", "No hay dispositivo conectado.")
            return
        number = self.number_entry.get().strip()
        if not number:
            messagebox.showwarning("Aviso", "Introduce un número de teléfono.")
            return

        def task():
            subprocess.run(['adb', '-s', self.current_device, 'shell', 'am', 'start', '-a',
                            'android.intent.action.CALL', '-d', f'tel:{number}'],
                           capture_output=True, encoding='utf-8', errors='replace')
            self.en_llamada = True
            self.call_start_time = None
            self.call_timer_running = False
            self.after(0, self.mostrar_botones)
            self.monitorear_llamada()
            self.after(3000, self.cargar_historial)

        threading.Thread(target=task, daemon=True).start()

    def colgar(self):
        if not self.current_device:
            return

        def task():
            subprocess.run(['adb', '-s', self.current_device, 'shell', 'input', 'keyevent', 'KEYCODE_ENDCALL'],
                           capture_output=True, encoding='utf-8', errors='replace')
            self.en_llamada = False
            self.call_timer_running = False
            self.after(0, self.actualizar_cronometro)
            self.after(0, self.mostrar_botones)

        threading.Thread(target=task, daemon=True).start()

    def monitorear_llamada(self):
        def monitor():
            llamada_activa = False
            while self.en_llamada:
                salida = self.run_adb_command(['adb', '-s', self.current_device, 'shell', 'dumpsys', 'telephony.registry'])
                if "mCallState=2" in salida:
                    if not llamada_activa:
                        llamada_activa = True
                        self.call_start_time = time.time()
                        self.call_timer_running = True
                        self.after(0, self.actualizar_cronometro)
                elif "mCallState=0" in salida and llamada_activa:
                    llamada_activa = False
                    self.call_timer_running = False
                    self.en_llamada = False
                    self.after(0, self.mostrar_botones)
                    break
                time.sleep(1)

        threading.Thread(target=monitor, daemon=True).start()

    def actualizar_cronometro(self):
        if self.call_timer_running and self.call_start_time:
            elapsed = int(time.time() - self.call_start_time)
            minutos, segundos = divmod(elapsed, 60)
            self.call_timer_label.config(text=f"⏱️ Duración: {minutos:02}:{segundos:02}")
            self.after(1000, self.actualizar_cronometro)
        else:
            self.call_timer_label.config(text="⏱️ Duración: 00:00")

    def adb_restart(self):
        def task():
            subprocess.run(['taskkill', '/F', '/IM', 'adb.exe'], capture_output=True, encoding='utf-8')
            time.sleep(1)
            subprocess.run(['adb', 'start-server'], capture_output=True, encoding='utf-8')
            self.after(0, lambda: messagebox.showinfo("Info", "ADB reiniciado"))
            self.after(4000, self.cargar_dispositivos)

        threading.Thread(target=task, daemon=True).start()

    def conectar_wifi(self):
        ip = self.wifi_ip_entry.get().strip()
        if not ip:
            self.wifi_status_label.config(text="Por favor, introduce una IP válida.", foreground="red")
            return
        self.wifi_status_label.config(text="Conectando...", foreground="blue")

        def task():
            subprocess.run(['adb', 'tcpip', '5555'], capture_output=True, encoding='utf-8')
            time.sleep(1)
            result = subprocess.run(['adb', 'connect', f'{ip}:5555'],
                                    capture_output=True, text=True, encoding='utf-8')
            if 'connected to' in result.stdout:
                self.after(0, lambda: self.wifi_status_label.config(text=f'Conectado a {ip}:5555', foreground="green"))
                self.after(2000, self.cargar_dispositivos)
            else:
                self.after(0, lambda: self.wifi_status_label.config(text=f'Error: {result.stdout}', foreground="red"))

        threading.Thread(target=task, daemon=True).start()

    def cargar_historial(self):
        def task():
            if not self.current_device:
                self.actualizar_historial("No hay dispositivo conectado.")
                return

            output = self.run_adb_command(
                ['adb', '-s', self.current_device, 'shell', 'content', 'query', '--uri', 'content://call_log/calls'],
                timeout=5)

            if not output:
                self.actualizar_historial("❌ No se pudo obtener historial o está vacío.")
                return

            llamadas = []
            iconos = {1: '📥', 2: '📤', 3: '❌'}

            for line in output.splitlines():
                if not line.startswith("Row:"):
                    continue

                number = re.search(r"normalized_number=([^,\s]+)", line) or \
                         re.search(r"number='([^']*)'|number=([^,\s]+)", line)
                date = re.search(r'date=(\d+)', line)
                tipo = re.search(r'type=(\d+)', line)

                if number and date and tipo:
                    num = number.group(1) or number.group(2)
                    date_ts = int(date.group(1))
                    tipo_num = int(tipo.group(1))
                    fecha = datetime.fromtimestamp(date_ts / 1000).strftime('%Y-%m-%d %H:%M:%S')
                    llamadas.append({
                        'numero': num, 'fecha': fecha, 'tipo': tipo_num, 'icono': iconos.get(tipo_num, '❓'),
                        'timestamp': date_ts
                    })

            llamadas_ordenadas = sorted(llamadas, key=lambda x: x['timestamp'], reverse=True)[:10]
            texto_historial = "\n".join(
                f"{x['icono']} {x['numero']} ({['', 'Entrante', 'Saliente', 'Perdida'][x['tipo']]}) - {x['fecha']}"
                for x in llamadas_ordenadas
            )
            self.actualizar_historial(texto_historial)

        threading.Thread(target=task, daemon=True).start()

    def actualizar_historial(self, texto):
        self.historial_text.config(state='normal')
        self.historial_text.delete('1.0', tk.END)
        self.historial_text.insert(tk.END, texto)
        self.historial_text.config(state='disabled')

    def update_loop(self):
        self.cargar_dispositivos()
        self.obtener_bateria()
        self.after(5000, self.update_loop)


if __name__ == "__main__":
    app = ADBPhoneApp()
    app.mainloop()
