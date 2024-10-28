import network 
import gc
import time
import urequests as requests
import read as rfid
import machine

gc.collect()

SSID = 'Mickey'
PASSWORD = 'Alejandra2.'
BASE_API_URL = 'https://8863-38-171-96-11.ngrok-free.app/api/'
API_TOKEN = 'b07dbc7cd57ce26801dea597c8f9a612ebe07fa7c501b8eecde0403b5a5449cd00d4314b2cdaf3dcbe845ba049dd431a218216e9dba57fda3960b8c69b0e7db169352df87081a0621c66906119fae740f62dfa3f992f3180d2ff9974e6139754d3053a283c1fcfff1529dbdad496df16505a31005d5c1aa752fd46a32405ab79'
URL_NOTIFICATION = 'house-notifications'

URL_FETCH_ACCESS = f"{BASE_API_URL}house-access-controls?fields[0]=code&fields[1]=status&populate[house][fields][0]=id&populate[house][fields][1]=status"

HEADERS = {
    'Authorization': f'Bearer {API_TOKEN}',
    'Content-Type': 'application/json'
}

ACCESS_STATUS = {
    "ACTIVATED": 1,
    "INACTIVE": 2,
    'DEACTIVATED': 0
}

STATE_STATUS = {
    "ERROR": -1,
    "LOADING": 0,
    "SUCCESS": 1,
    "WARNING": 2
}

def servo_move(angle, servo=machine.PWM(machine.Pin(15), freq=50)):
    if angle < 0:
        angle = 0
    elif angle > 180:
        angle = 180
    duty = int(40 + (angle / 180) * 115)  # Conversión a ciclo de trabajo
    servo.duty(duty)

# Lógica para mover el servo al verificar acceso
def servo_control():
    print("Abriendo portón...")
    servo_move(180)
    time.sleep(6)
    print("Cerrando portón...")
    servo_move(0)
    time.sleep(2)

def connectWifi(ssid, password):
    station = network.WLAN(network.STA_IF)
    station.active(True)
    station.connect(ssid, password)
    
    while not station.isconnected():
        print('Conectando...')
        time.sleep(1)
    
    print('Dirección IP:', station.ifconfig()[0])
    print(f'Conexión exitosa a {ssid}')
    
def api_request(method, api_url, data=None, timeout=10):
    try:
        if method == 'GET':
            response = requests.get(url=api_url, headers=HEADERS, timeout=timeout)
        elif method == 'POST':
            response = requests.post(url=api_url, headers=HEADERS, json=data, timeout=timeout)
        elif method == 'PUT':
            response = requests.put(url=api_url, headers=HEADERS, json=data, timeout=timeout)
        else:
            raise ValueError('Unsupported HTTP method')
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f'Error: HTTP {response.status_code}')
            return None
    except Exception as e:
        print('Request error:', str(e))
        return None
    
def extract_info(data, key):
    try:
        return data[key]
    except KeyError:
        return None
    
def house_access_control_status(data, code):
    try:
        for access in data:
                if access['attributes']['code'] == code:
                    if access['attributes']['status'] == ACCESS_STATUS['ACTIVATED'] and access['attributes']['house']['data']['attributes']['status'] == ACCESS_STATUS['ACTIVATED']:
                        print("Acceso permitido")
                        sendNotification("Acceso permitido en porteria.", access['attributes']['house']['data']['id'], STATE_STATUS['SUCCESS'])
                        servo_control()
                        return True
                    else:
                        print("Acceso denegado")
                        sendNotification("Acceso denegado en porteria.", access['attributes']['house']['data']['id'], STATE_STATUS['WARNING'])
                        return False
        # Si ninguna tarjeta coincide
        print("Tarjeta no registrada o no activada", access['attributes']['house']['data']['id'])
        sendNotification("Una tarjeta no registrada intento acceder a la casa.", access['attributes']['house']['data']['id'], STATE_STATUS['WARNING'])
        return None  # Cambié el retorno aquí a False para mayor claridad

    except Exception as e:
        print("Error en la solicitud a la API access control:", str(e))
        return None  # También retorné False en caso de error


def sendNotification(message, id, feedback):
    URL_FETCH_NOTIFICATION = f"{BASE_API_URL}{URL_NOTIFICATION}"
    data = {
        "data": {
            "description": message,
            "house" : id,
            "feedback" : feedback
        }
    }
    response = api_request('POST', URL_FETCH_NOTIFICATION, data)
    if response is not None:
        return True
    else:
        return

connectWifi(SSID, PASSWORD)

def main():
    try:
        while True:
            print("Esperando tarjeta...")

            rfidInfo = rfid.do_read()

            if rfidInfo['status'] != 'ok':
                print("Error al detectar la tarjeta")
                break

            print("Tarjeta detectada. Leyendo ID...")
            handle_access(rfidInfo)
            time.sleep(2)

    except KeyboardInterrupt:
        print("Programa detenido por el usuario.")

def handle_access(rfidInfo):
    try:
        access_data = api_request('GET', URL_FETCH_ACCESS)

        if access_data is None:
            sendNotification("No se obtuvieron datos de acceso.", access_data['data'][0]['id'], STATE_STATUS['ERROR'])
            print("No se obtuvieron datos de acceso")
            return

        extract_access = extract_info(access_data, 'data')

        house_access_control_status(extract_access, rfidInfo['uid'])

    except Exception as e:
        print("Error en la solicitud a la API:", str(e))

main()
