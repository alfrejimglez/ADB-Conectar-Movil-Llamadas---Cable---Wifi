import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import threading
import time
import re
from datetime import datetime
import sys

#permite minimizar al abrirlo
if sys.platform == "win32":
    import ctypes
    ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
    
    #inicio intefaz y llamada de defs
class ADBPhoneApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("📱 Teléfono ADB")
        self.geometry("960x600")

        self.current_device = None
        self.en_llamada = False
        self.error_activo = False
        self.call_start_time = None
        self.call_timer_running = False
        self.ventana_llamada = None
        self.llamada_entrante_activa = False
        self.dialogo_abierto = False

        self.create_widgets()
        self.cargar_dispositivos()
        self.update_loop()
        self.monitorear_llamadas()  # Llama a la función unificada de monitoreo
        self.after(2000, self.verificar_bluetooth)  # Verifica automáticamente

#secciones de la UI con su tamaño y fuentes
    def create_widgets(self):
        # Panel izquierdo
        left_frame = ttk.Frame(self)
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)

        # Dispositivo conectado
        ttk.Label(left_frame, text="Dispositivo conectado").pack(anchor='w')
        self.device_combo = ttk.Combobox(left_frame, state='readonly')
        self.device_combo.pack(fill=tk.X, pady=5)
        self.device_combo.bind("<<ComboboxSelected>>", self.on_device_change)

       # Número de teléfono
        ttk.Label(left_frame, text="Número de teléfono").pack(anchor='w')
        number_frame = ttk.Frame(left_frame)  # ✅ Definir contenedor primero
        number_frame.pack(fill=tk.X, pady=5)
        self.number_entry = ttk.Entry(number_frame, font=("Arial", 14))
        self.number_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=6)
        clear_btn = ttk.Button(number_frame, text="❌", width=3, command=lambda: self.number_entry.delete(0, tk.END))
        clear_btn.pack(side=tk.LEFT, padx=2)
        self.number_entry.bind("<Return>", lambda e: self.llamar())
    

        # Botones
        btn_frame = ttk.Frame(left_frame)
        btn_frame.pack(pady=10, fill=tk.X)

        self.call_btn = ttk.Button(btn_frame, text="📞 Llamar", command=self.llamar)
        self.call_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)

        self.hangup_btn = ttk.Button(btn_frame, text="📴 Colgar", command=self.colgar)
        self.hangup_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
        self.hangup_btn.state(['disabled'])
        #mutear
        self.mute_state = False  # Estado de mute: False = no silenciado

        self.mute_btn = ttk.Button(btn_frame, text="🔇 Silenciar", command=self.toggle_mute)
        self.mute_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)


        self.restart_adb_btn = ttk.Button(btn_frame, text="♻️ Reiniciar ADB", command=self.adb_restart)
        self.restart_adb_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
        
        # Variable para controlar topmost
        self.topmost_var = tk.BooleanVar(value=False)

        # Checkbutton para "Siempre en primer plano"
        self.topmost_check = ttk.Checkbutton(
            left_frame,
            text="📌 Siempre en primer plano",
            variable=self.topmost_var,
            command=self.toggle_topmost
        )
        self.topmost_check.pack(pady=5, anchor='w')


        self.call_timer_label = ttk.Label(btn_frame, text="⏱️ Duración: 00:00", font=("Arial", 10))
        self.call_timer_label.pack(side=tk.BOTTOM, pady=5)

        # Separador
        ttk.Separator(left_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)

        # Conexión WiFi ADB
        ttk.Label(left_frame, text="🔌 Conexión WiFi ADB").pack(anchor='w')
        ttk.Label(left_frame, text="IP del dispositivo (ej: 192.168.1.50)").pack(anchor='w')
        self.wifi_ip_entry = ttk.Entry(left_frame)
        self.wifi_ip_entry.pack(fill=tk.X, pady=5)
        self.connect_wifi_btn = ttk.Button(left_frame, text="🔗 Conectar WiFi", command=self.conectar_wifi)
        self.connect_wifi_btn.pack(pady=5)

        self.wifi_status_label = ttk.Label(left_frame, text="", foreground="blue")
        self.wifi_status_label.pack(anchor='w')

        # Estado de batería
        self.battery_label = ttk.Label(left_frame, text="🔋 Batería: --%")
        self.battery_label.pack(pady=5, anchor='w')

        self.error_label = ttk.Label(left_frame, text="❌ Error al obtener batería", foreground="red")
        self.error_label.pack(pady=5, anchor='w')
        self.error_label.pack_forget()
        
        ttk.Separator(left_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)
        
        #bluetooth
        ttk.Label(left_frame, text="🎧 Estado Bluetooth y Dispositivo").pack(anchor='w')

        self.bluetooth_status_label = ttk.Label(left_frame, text="(sin verificar)", foreground="blue")
        self.bluetooth_status_label.pack(anchor='w')

        self.bluetooth_device_label = ttk.Label(left_frame, text="", foreground="black")
        self.bluetooth_device_label.pack(anchor='w')

        bt_button_frame = ttk.Frame(left_frame)
        bt_button_frame.pack(fill=tk.X, pady=5)

        self.bt_on_btn = ttk.Button(bt_button_frame, text="🟢 Encender", command=self.encender_bluetooth)
        self.bt_on_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)

        self.bt_off_btn = ttk.Button(bt_button_frame, text="🔴 Apagar", command=self.apagar_bluetooth)
        self.bt_off_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)

        self.check_bt_button = ttk.Button(left_frame, text="🔍 Verificar Bluetooth", command=self.verificar_bluetooth)
        self.check_bt_button.pack(pady=5, fill=tk.X)

        # Panel derecho (Historial)
        right_frame = ttk.Frame(self)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        ttk.Label(right_frame, text="📂 Historial").pack(anchor='w')
        self.historial_text = tk.Text(
            right_frame, height=30, width=50,
            state='disabled', bg='white',
            relief=tk.SOLID, borderwidth=1
        )
        self.historial_text.pack(fill=tk.BOTH, expand=True)



#funcion comando adb

    def run_adb_command(self, args, timeout=10):
        try:
            result = subprocess.run(args, capture_output=True, text=True,
                                    timeout=timeout, encoding='utf-8', errors='replace')
            return result.stdout.strip()
        except Exception:
            return None
#funcion carga dispostivio si adb esta okey en el equipo
    def cargar_dispositivos(self):
        output = self.run_adb_command(['adb', 'devices'])
        devices = []
        if output:
            # Filtra solo las líneas con dispositivos conectados
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

#func si cambia de device
    def on_device_change(self, event=None):
        self.current_device = self.device_combo.get()
        self.obtener_bateria()
        self.cargar_historial()
#obtener bateria
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
#funcion llamar 

    def llamar(self):
        if not self.current_device:
            messagebox.showerror("Error", "No hay dispositivo conectado.")
            return
        number = self.number_entry.get().strip()
        if not number:
            messagebox.showwarning("Aviso", "Introduce un número de teléfono.")
            return

        # Normaliza el número: si empieza por 34 y no tiene '+', añade el '+'
        if number.startswith("34") and not number.startswith("+") and len(number) > 9:
            number = "+" + number

        def task():
            subprocess.run(['adb', '-s', self.current_device, 'shell', 'am', 'start', '-a',
                            'android.intent.action.CALL', '-d', f'tel:{number}'],
                        capture_output=True, encoding='utf-8', errors='replace')
            self.en_llamada = True  # ✅ Solo aquí, una vez
            self.call_start_time = None
            self.call_timer_running = False
            self.after(0, self.mostrar_botones)
            self.after(3000, self.cargar_historial)

        threading.Thread(target=task, daemon=True).start()
#funcion colgar

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
            self.after(0, lambda: self.hangup_btn.state(['!disabled']))

        threading.Thread(target=task, daemon=True).start()
#func diferentes estados 1 es q llamo , 2 activa
    def monitorear_llamadas(self):
        def monitor():
            llamada_activa = False
            llamada_entrante_activa = False

            while True:
                salida = self.run_adb_command(['adb', '-s', self.current_device, 'shell', 'dumpsys', 'telephony.registry'])

                if not salida:
                    time.sleep(1)
                    continue

                # Llamada entrante detectada
                # Llamada entrante
                if "mCallState=1" in salida and not self.en_llamada:
                    if not self.llamada_entrante_activa:
                        self.llamada_entrante_activa = True

                        numero_match = re.search(r'mCallIncomingNumber=([\d+]+)', salida)
                        numero = numero_match.group(1) if numero_match else "Desconocido"

                        self.after(0, lambda: self.mostrar_dialogo_llamada(numero))


                # Llamada activa
                elif "mCallState=2" in salida:
                    if not llamada_activa:
                        llamada_activa = True
                        llamada_entrante_activa = False
                        self.llamada_entrante_activa = False
                        self.call_start_time = time.time()
                        self.call_timer_running = True
                        self.en_llamada = True
                        self.after(0, self.actualizar_cronometro)
                        self.after(0, lambda: self.hangup_btn.state(['!disabled']))

                        # Cerrar ventana llamada entrante si abierta
                        self.after(0, self.cerrar_ventana_llamada)

                # Llamada finalizada
                elif "mCallState=0" in salida:
                    llamada_activa = False
                    llamada_entrante_activa = False
                    self.llamada_entrante_activa = False
                    self.en_llamada = False
                    self.call_timer_running = False
                    self.call_start_time = None
                    self.after(0, self.actualizar_cronometro)
                    self.after(0, self.mostrar_botones)
                    self.after(0, lambda: self.hangup_btn.state(['disabled']))
                    self.after(0, self.cerrar_ventana_llamada)

                time.sleep(1)

        threading.Thread(target=monitor, daemon=True).start()

       

#moco para ver si me llaman
    def mostrar_dialogo_llamada(self, numero):
        if self.dialogo_abierto:
            return


        self.dialogo_abierto = True
        self.ventana_llamada = tk.Toplevel(self)
        self.ventana_llamada.title("📞 Llamada entrante")
        self.ventana_llamada.geometry("300x150")
        self.ventana_llamada.resizable(False, False)
        self.ventana_llamada.protocol("WM_DELETE_WINDOW", self.cerrar_ventana_llamada)

        ttk.Label(self.ventana_llamada, text=f"📲 Llamada de: {numero}", font=("Arial", 12)).pack(pady=10)

        btn_frame = ttk.Frame(self.ventana_llamada)
        btn_frame.pack(pady=10)

        ttk.Button(btn_frame, text="✅ Contestar", command=self.accion_contestar).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="❌ Rechazar", command=self.accion_rechazar).pack(side=tk.LEFT, padx=10)



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
            tipos_texto = {1: 'Entrante', 2: 'Saliente', 3: 'Perdida'}

            for line in output.splitlines():
                if not line.startswith("Row:"):
                    continue

                # Extraer número
                number_match = re.search(r"normalized_number=([^,\s]+)", line) or \
                            re.search(r"number='([^']*)'|number=([^,\s]+)", line)
                # Extraer fecha
                date_match = re.search(r'date=(\d+)', line)

                # Extraer tipo manualmente para evitar problemas con regex
                tipo_str = ""
                for campo in line.split(","):
                    if campo.strip().startswith("type="):
                        tipo_str = campo.strip().split("=")[1]
                        break
                if not tipo_str:
                    continue
                tipo_num = int(tipo_str)

                if number_match and date_match:
                    num = number_match.group(1) or number_match.group(2)
                    date_ts = int(date_match.group(1))
                    fecha = datetime.fromtimestamp(date_ts / 1000).strftime('%Y-%m-%d %H:%M:%S')

                    texto_extra = ""
                    if tipo_num == 1:
                        texto_extra = f" CMD: Llamada entrante detectada al {num}"
                    elif tipo_num == 2:
                        texto_extra = f" CMD: Llamada saliente realizada al {num}"

                    llamadas.append({
                        'numero': num,
                        'fecha': fecha,
                        'tipo': tipo_num,
                        'icono': iconos.get(tipo_num, '❓'),
                        'timestamp': date_ts,
                        'extra': texto_extra
                    })

            llamadas_ordenadas = sorted(llamadas, key=lambda x: x['timestamp'], reverse=True)[:10]

            texto_historial = "\n".join(
                f"{x['icono']} {x['numero']} ({tipos_texto.get(x['tipo'], 'Desconocido')}) - {x['fecha']}{x['extra']}"
                for x in llamadas_ordenadas
            )

            self.actualizar_historial(texto_historial)

        threading.Thread(target=task, daemon=True).start()


        

    def contestar_llamada(self):
        if not self.current_device:
            return

        def task():
            subprocess.run(['adb', '-s', self.current_device, 'shell', 'input', 'keyevent', 'KEYCODE_CALL'],
                        capture_output=True, encoding='utf-8', errors='replace')
            self.en_llamada = True
            self.call_start_time = time.time()
            self.call_timer_running = True
            self.after(0, self.actualizar_cronometro)
            self.after(0, self.mostrar_botones)
            self.monitorear_llamadas()  # 🧠

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
        
    def cerrar_ventana_llamada(self):
        if self.ventana_llamada:
            self.ventana_llamada.destroy()
            self.ventana_llamada = None
            self.dialogo_abierto = False
            self.llamada_entrante_activa = False

            
    def accion_contestar(self):
        self.contestar_llamada()
        self.cerrar_ventana_llamada()
        self.llamada_entrante_activa = False

    def accion_rechazar(self):  
        self.colgar()
        self.cerrar_ventana_llamada()
        self.llamada_entrante_activa = False
        
    def toggle_mute(self):
        if not self.current_device:
            messagebox.showwarning("Sin dispositivo", "No hay dispositivo conectado.")
            return

        if not self.en_llamada:
            messagebox.showinfo("Sin llamada", "No hay una llamada en curso para silenciar.")
            return

        # Encender pantalla (asegura que la UI esté visible)
        self.run_adb_command(['adb', '-s', self.current_device, 'shell', 'input', 'keyevent', '224'])  # KEYCODE_WAKEUP

        # Espera muy breve para asegurar visibilidad
        time.sleep(0.5)

        # Alternar estado
        self.mute_state = not getattr(self, "mute_state", False)

        # Coordenadas del botón 'Silenciar'
        x, y = 268, 1093

        # Ejecutar toque
        self.run_adb_command(['adb', '-s', self.current_device, 'shell', 'input', 'tap', str(x), str(y)])

        # Actualizar texto del botón
        nuevo_texto = "🔈 Activar micrófono" if self.mute_state else "🔇 Silenciar"
        self.mute_btn.config(text=nuevo_texto)



            
        
        
    def verificar_bluetooth(self):
        if not self.current_device:
            self.bluetooth_status_label.config(text="❌ No hay dispositivo conectado", foreground="red")
            return

        def task():
            bt_on = self.run_adb_command(['adb', '-s', self.current_device, 'shell', 'settings', 'get', 'global', 'bluetooth_on'])
            if bt_on.strip() != '1':
                self.after(0, lambda: (
                    self.bluetooth_status_label.config(text="📴 Bluetooth apagado", foreground="red"),
                    self.bluetooth_device_label.config(text="")
                ))
                return

            salida = self.run_adb_command(['adb', '-s', self.current_device, 'shell', 'dumpsys', 'bluetooth_manager'])

            if not salida:
                self.after(0, lambda: self.bluetooth_status_label.config(text="❌ Error al obtener estado", foreground="red"))
                return

            conectado = "Connected: true" in salida or "state: CONNECTED" in salida or "ConnectionState: 2" in salida

            # Extraer nombre del dispositivo conectado
            nombre = ""
            for linea in salida.splitlines():
                if "Device:" in linea and "name" in linea.lower():
                    nombre = linea.strip().split()[-1]
                    break

            if conectado:
                self.after(0, lambda: (
                    self.bluetooth_status_label.config(text="✅ Bluetooth ACTIVADO y conectado", foreground="green"),
                    self.bluetooth_device_label.config(text=f"🔗 Dispositivo: {nombre}" if nombre else "")
                ))
            else:
                self.after(0, lambda: (
                    self.bluetooth_status_label.config(text="⚠️ Bluetooth ACTIVADO pero sin conexión", foreground="orange"),
                    self.bluetooth_device_label.config(text="")
                ))

        threading.Thread(target=task, daemon=True).start()  
        
    def encender_bluetooth(self):
        if not self.current_device:
            return

        self.run_adb_command(['adb', '-s', self.current_device, 'shell', 'svc', 'bluetooth', 'enable'])
        self.agregar_a_historial("🟢 Bluetooth encendido")

        # Primera verificación rápida (estado general)
        self.after(2400, self.verificar_bluetooth)

        # Segunda verificación más tarde (para comprobar si ya se conectó)
        self.after(5000, self.verificar_bluetooth)  # espera 5 segundos extra para chequear conexión



    def apagar_bluetooth(self):
        if not self.current_device:
            return
        self.run_adb_command(['adb', '-s', self.current_device, 'shell', 'svc', 'bluetooth', 'disable'])
        self.agregar_a_historial("🔴 Bluetooth apagado")
        self.verificar_bluetooth()  
        
        
    def agregar_a_historial(self, mensaje):
        timestamp = time.strftime("%H:%M:%S")
        self.historial_text.configure(state='normal')
        self.historial_text.insert(tk.END, f"[{timestamp}] {mensaje}\n")
        self.historial_text.configure(state='disabled')
        self.historial_text.see(tk.END)
   
    def toggle_topmost(self):
        self.attributes("-topmost", self.topmost_var.get())

    



if __name__ == "__main__":
    app = ADBPhoneApp()
    app.mainloop()
