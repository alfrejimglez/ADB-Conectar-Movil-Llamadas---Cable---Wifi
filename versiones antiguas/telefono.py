from flask import Flask, request, jsonify, Response
import subprocess
import threading
import webbrowser
import time
import re

app = Flask(__name__)

def abrir_navegador():
    time.sleep(1)
    webbrowser.open("http://127.0.0.1:3000")

@app.route("/")
def index():
    html = """
    <!DOCTYPE html>
    <html lang='es'>
    <head>
        <meta charset='UTF-8'>
        <title>Teléfono ADB</title>
        <link href='https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css' rel='stylesheet'>
        <style>
            body { background-color: #f8f9fa; }
            .container { margin-top: 40px; }
            .hidden { display: none; }
            .call-history { background: #fff; border-radius: 10px; padding: 15px; height: 300px; overflow-y: auto; box-shadow: 0 0 10px rgba(0,0,0,0.1); }
        </style>
    </head>
    <body>
        <div class='container'>
            <h1 class='text-center mb-4'>📱 Teléfono ADB</h1>
            <div class='row'>
                <div class='col-md-8'>
                    <div class='mb-3'>
                        <label class='form-label'>Dispositivo conectado</label>
                        <select id='device' class='form-select'></select>
                    </div>

                    <div class='mb-3'>
                        <label class='form-label'>Número de teléfono</label>
                        <input type='text' id='number' class='form-control' placeholder='Introduce el número y pulsa Enter o usa el botón'>
                    </div>

                    <div class='mb-3 text-center'>
                        <button id='call' class='btn btn-success me-2'>📞 Llamar</button>
                        <button id='hangup' class='btn btn-danger me-2 hidden'>📴 Colgar</button>
                        <button id='restart-adb' class='btn btn-warning me-2'>♻️ Reiniciar ADB</button>
                    </div>

                    <hr>

                    <h5>🔌 Conexión WiFi ADB</h5>
                    <div class='mb-3'>
                        <label class='form-label'>IP del dispositivo (ejemplo: 192.168.1.50)</label>
                        <input type='text' id='wifi-ip' class='form-control' placeholder='Introduce IP para conectar por WiFi'>
                    </div>
                    <div class='mb-3 text-center'>
                        <button id='connect-wifi' class='btn btn-primary'>🔗 Conectar WiFi</button>
                        <div id="wifi-status" class="mt-2"></div>
                    </div>

                    <div class='alert alert-info' id='battery'>🔋 Batería: --%</div>
                    <div class='alert alert-danger d-none' id='error'>❌ Error al obtener batería</div>
                </div>

                <div class='col-md-4'>
                    <h5>📂 Historial</h5>
                    <div class='call-history' id='historial'>Cargando...</div>
                </div>
            </div>
        </div>

        <script>
            let currentDevice = null;
            let enLlamada = false;
            let errorActivo = false;

            async function cargarDispositivos() {
                try {
                    const res = await fetch('/devices');
                    const devices = await res.json();
                    const select = document.getElementById('device');
                    select.innerHTML = '';
                    if (devices.length === 0) {
                        currentDevice = null;
                        select.innerHTML = '<option selected>No conectado</option>';
                        mostrarError();
                        ocultarBotones();
                        return;
                    }

                    devices.forEach(dev => {
                        const opt = document.createElement('option');
                        opt.value = dev;
                        opt.text = dev;
                        select.appendChild(opt);
                    });

                    currentDevice = select.value;
                    obtenerBateria();
                    cargarHistorial();
                    mostrarBotones();
                } catch (e) {
                    mostrarError();
                    ocultarBotones();
                }
            }

            async function obtenerBateria() {
                if (!currentDevice) return;
                try {
                    const res = await fetch(`/battery?device=${currentDevice}`);
                    const data = await res.json();
                    if (data.level !== undefined) {
                        document.getElementById('battery').textContent = `🔋 Batería: ${data.level}%`;
                        document.getElementById('battery').classList.remove('d-none');
                        document.getElementById('error').classList.add('d-none');
                        errorActivo = false;
                    } else {
                        throw new Error();
                    }
                } catch {
                    if (!errorActivo) {
                        mostrarError();
                        errorActivo = true;
                    }
                }
            }

            function mostrarError() {
                document.getElementById('battery').classList.add('d-none');
                document.getElementById('error').classList.remove('d-none');
            }

            function mostrarBotones() {
                document.getElementById('call').classList.remove('hidden');
                if (enLlamada) {
                    document.getElementById('hangup').classList.remove('hidden');
                } else {
                    document.getElementById('hangup').classList.add('hidden');
                }
            }

            function ocultarBotones() {
                document.getElementById('call').classList.add('hidden');
                document.getElementById('hangup').classList.add('hidden');
            }

            async function llamar() {
                const number = document.getElementById('number').value;
                if (number && currentDevice) {
                    const fd = new FormData();
                    fd.append('number', number);
                    fd.append('device', currentDevice);
                    await fetch('/call', { method: 'POST', body: fd });
                    enLlamada = true;
                    mostrarBotones();
                    setTimeout(cargarHistorial, 3000);
                }
            }

            async function colgar() {
                if (!currentDevice) return;
                const fd = new FormData();
                fd.append('device', currentDevice);
                await fetch('/hangup', { method: 'POST', body: fd });
                enLlamada = false;
                mostrarBotones();
            }

            async function cargarHistorial() {
                if (!currentDevice) return;
                try {
                    const res = await fetch(`/history?device=${currentDevice}`);
                    const data = await res.json();
                    const div = document.getElementById('historial');
                    div.innerHTML = '';
                    data.forEach(item => {
                        const el = document.createElement('div');
                        el.innerText = `${item.icono} ${item.numero} (${item.tipo})`;
                        div.appendChild(el);
                    });
                } catch {
                    document.getElementById('historial').innerText = '❌ Error al cargar historial';
                }
            }

            async function conectarWifi() {
                const ip = document.getElementById('wifi-ip').value.trim();
                const statusDiv = document.getElementById('wifi-status');
                if (!ip) {
                    statusDiv.textContent = 'Por favor, introduce una IP válida.';
                    statusDiv.className = 'text-danger';
                    return;
                }
                statusDiv.textContent = 'Conectando...';
                statusDiv.className = 'text-info';

                const fd = new FormData();
                fd.append('ip', ip);
                try {
                    const res = await fetch('/adb-wifi-connect', { method: 'POST', body: fd });
                    const text = await res.text();
                    if (res.ok) {
                        statusDiv.textContent = text;
                        statusDiv.className = 'text-success';
                        setTimeout(() => {
                            cargarDispositivos();
                        }, 2000);
                    } else {
                        statusDiv.textContent = text;
                        statusDiv.className = 'text-danger';
                    }
                } catch (e) {
                    statusDiv.textContent = 'Error al conectar: ' + e.message;
                    statusDiv.className = 'text-danger';
                }
            }

            document.addEventListener('DOMContentLoaded', () => {
                cargarDispositivos();
                setInterval(() => {
                    cargarDispositivos();
                    obtenerBateria();
                }, 5000);

                document.getElementById('device').addEventListener('change', e => {
                    currentDevice = e.target.value;
                    obtenerBateria();
                    cargarHistorial();
                });

                document.getElementById('number').addEventListener('keypress', async e => {
                    if (e.key === 'Enter') {
                        e.preventDefault();
                        await llamar();
                    }
                });

                document.getElementById('call').addEventListener('click', llamar);
                document.getElementById('hangup').addEventListener('click', colgar);
                document.getElementById('restart-adb').addEventListener('click', async () => {
                    await fetch('/adb-restart', { method: 'POST' });
                    setTimeout(cargarDispositivos, 4000);
                });
                document.getElementById('connect-wifi').addEventListener('click', conectarWifi);
            });
        </script>
    </body>
    </html>
    """
    return Response(html, mimetype='text/html')


@app.route('/devices')
def devices():
    try:
        result = subprocess.run(['adb', 'devices'], capture_output=True, text=True)
        lines = result.stdout.strip().split('\n')[1:]
        dispositivos = [line.split('\t')[0] for line in lines if 'device' in line]
        return jsonify(dispositivos)
    except Exception:
        return jsonify([])


@app.route('/battery')
def battery():
    device = request.args.get('device')
    if not device:
        return jsonify({'error': 'Falta dispositivo'}), 400
    try:
        result = subprocess.run(['adb', '-s', device, 'shell', 'dumpsys', 'battery'],
                                capture_output=True, text=True, timeout=5)
        for line in result.stdout.splitlines():
            if 'level:' in line:
                level = int(line.split(':')[1].strip())
                return jsonify({'level': level})
        return jsonify({'error': 'No se encontró nivel de batería'}), 500
    except Exception:
        return jsonify({'error': 'Error al obtener batería'}), 500


@app.route('/call', methods=['POST'])
def call():
    number = request.form.get('number')
    device = request.form.get('device')
    if not number or not device:
        return 'Faltan datos', 400
    try:
        subprocess.run(['adb', '-s', device, 'shell', 'am', 'start', '-a',
                        'android.intent.action.CALL', '-d', f'tel:{number}'],
                        capture_output=True)
        return 'Llamando'
    except Exception:
        return 'Error', 500


@app.route('/hangup', methods=['POST'])
def hangup():
    device = request.form.get('device')
    if not device:
        return 'Falta dispositivo', 400
    try:
        subprocess.run(['adb', '-s', device, 'shell', 'input', 'keyevent', 'KEYCODE_ENDCALL'],
                       capture_output=True)
        return 'Colgado'
    except Exception:
        return 'Error', 500


@app.route('/adb-restart', methods=['POST'])
def adb_restart():
    try:
        subprocess.run(['taskkill', '/F', '/IM', 'adb.exe'], capture_output=True)
        time.sleep(1)
        subprocess.run(['adb', 'start-server'], capture_output=True)
        return 'ADB reiniciado'
    except Exception:
        return 'Error reiniciando ADB', 500


@app.route('/adb-wifi-connect', methods=['POST'])
def adb_wifi_connect():
    ip = request.form.get('ip')
    if not ip:
        return 'Falta IP', 400
    try:
        # Reinicia adb en modo tcpip (necesita cable conectado)
        subprocess.run(['adb', 'tcpip', '5555'], capture_output=True)
        time.sleep(1)
        # Conecta a la IP del dispositivo
        result = subprocess.run(['adb', 'connect', f'{ip}:5555'], capture_output=True, text=True)
        if 'connected to' in result.stdout:
            return f'Conectado a {ip}:5555'
        else:
            return f'Error conectando: {result.stdout}', 500
    except Exception as e:
        return f'Error: {str(e)}', 500


from datetime import datetime
@app.route('/history')
def history():
    device = request.args.get('device')
    if not device:
        return jsonify({'error': 'Falta dispositivo'}), 400
    try:
        result = subprocess.run(
            ['adb', '-s', device, 'shell', 'content', 'query', '--uri', 'content://call_log/calls'],
            capture_output=True,
            text=True,
            timeout=5,
            encoding='utf-8',
            errors='replace'
        )

        if result.returncode != 0 or not result.stdout.strip():
            return jsonify({'error': 'No se pudo obtener historial o está vacío'}), 500

        llamadas = []

        iconos = {
            1: '📥',  # Entrante
            2: '📤',  # Saliente
            3: '❌'   # Perdida
        }

        for line in result.stdout.splitlines():
            line = line.strip()
            if not line.startswith("Row:"):
                continue

            normalized_match = re.search(r"normalized_number=([^,\s]+)", line)
            number_match = re.search(r"number='([^']*)'|number=([^,\s]+)", line)

            if normalized_match:
                number = normalized_match.group(1)
            elif number_match:
                number = number_match.group(1) or number_match.group(2)
            else:
                print(f"No se encontró número en la línea: {line}")
                continue

            date_match = re.search(r'date=(\d+)', line)
            type_match = re.search(r'type=(\d+)', line)

            if not (date_match and type_match):
                print(f"No se encontró fecha o tipo en la línea: {line}")
                continue

            date_ts = int(date_match.group(1))
            tipo_num = int(type_match.group(1))

            fecha = datetime.fromtimestamp(date_ts / 1000).strftime('%Y-%m-%d %H:%M:%S')

            tipo = {
                1: 'Entrante',
                2: 'Saliente',
                3: 'Perdida'
            }.get(tipo_num, 'Desconocida')

            icono = iconos.get(tipo_num, '❓')

            llamadas.append({
                'numero': number,
                'fecha': fecha,
                'tipo': tipo,
                'icono': icono,
                'timestamp': date_ts
            })

        llamadas_ordenadas = sorted(llamadas, key=lambda x: x['timestamp'], reverse=True)
        ultimas_10 = llamadas_ordenadas[:10]
        for llamada in ultimas_10:
            llamada.pop('timestamp')

        return jsonify(ultimas_10)

    except Exception as e:
        print("Error al obtener historial:", e)
        return jsonify({'error': 'Error al obtener historial'}), 500

if __name__ == '__main__':
    threading.Thread(target=abrir_navegador).start()
    app.run(port=3000)