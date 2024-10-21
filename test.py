import network 
import gc
import time
import urequests as requests
import read as rfid
import machine 

gc.collect()

SSID = 'SERVIEDUCA WIFI'
PASSWORD = ''
BASE_API_URL = 'https://c841-38-171-144-49.ngrok-free.app/api/'
HOME_SERIAL_KEY = 'A20241125RC522RF'
URL_FILTER_HOUSE = '&fields[0]=name&fields[1]=code&fields[2]=status&populate[user][fields][3]=user'
API_TOKEN = 'b07dbc7cd57ce26801dea597c8f9a612ebe07fa7c501b8eecde0403b5a5449cd00d4314b2cdaf3dcbe845ba049dd431a218216e9dba57fda3960b8c69b0e7db169352df87081a0621c66906119fae740f62dfa3f992f3180d2ff9974e6139754d3053a283c1fcfff1529dbdad496df16505a31005d5c1aa752fd46a32405ab79'
URL_LOG = 'house-entry-logs'
URL_NOTIFICATION = 'house-notifications'

URL_FETCH_DEVICE = f"{BASE_API_URL}houses?filters[code][$eq]={HOME_SERIAL_KEY}{URL_FILTER_HOUSE}&populate[home_categories][fields][0]=home_devices&populate[home_categories][populate][home_devices][fields][0]=name&populate[home_categories][populate][home_devices][fields][1]=code&populate[home_categories][populate][home_devices][fields][2]=status"
URL_FETCH_ACCESS = f"{BASE_API_URL}houses?filters[code][$eq]={HOME_SERIAL_KEY}{URL_FILTER_HOUSE}&populate[house_access_controls][fields][0]=name&populate[house_access_controls][fields][1]=code&populate[house_access_controls][fields][2]=status&populate[house_access_controls][fields][3]=house_entry_logs&populate[house_access_controls][populate][house_entry_logs][fields][0]=entry_time&populate[house_access_controls][populate][house_entry_logs][fields][1]=exit_time&populate[house_access_controls][populate][house_entry_logs][fields][2]=status"

HEADERS = {
    'Authorization': f'Bearer {API_TOKEN}',
    'Content-Type': 'application/json'
}

ACCESS_STATUS = {
    "ACTIVATED": 1,
    "INACTIVE": 2,
    'DEACTIVATED': 0
}

DEVICE_STATUS = {
    "ACTIVATED": 1,
    "INACTIVE": 2,
    'DEACTIVATED': 0
}

HOUSE_STATUS = {
    "ACTIVATED": 1,
    "INACTIVE": 2,
    'DEACTIVATED': 0
}

USER_STATUS = {
    "IN_HOUSE": 1,
    "OUT_HOUSE": 2,
}

RELAY_PIN_CODE = {
    "A23R1": 5,
    "A23R2": 4,
    "A23R3": 3,
    "A23R4": 1
}

STATE_STATUS = {
    "ERROR": -1,
    "LOADING": 0,
    "SUCCESS": 1,
    "WARNING": 2
}

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

def extract_data(json_data, attributes):
    if json_data is not None and 'data' in json_data:
        data = json_data['data'][0]
        result = {'id': data['id']}
        result.update({attr: data['attributes'].get(attr) for attr in attributes})
        return result
    print('No data received')
    return None

def houseAccess(access_code, data):
    for access in data['house_access_controls']:
        if access['code'] == access_code:
            return access['status'] == ACCESS_STATUS['ACTIVATED'] and data['status'] == HOUSE_STATUS['ACTIVATED']
    return False

def deviceStatus(device_code, data):
    return data['attributes']['code'] == device_code and data['attributes']['status'] == DEVICE_STATUS['ACTIVATED']

def userStatus(data):
    inhouse_count = sum(1 for entry in data['house_access_controls'] if entry['house_entry_logs'] and 
                        any(log['attributes']['status'] == USER_STATUS['IN_HOUSE'] for log in entry['house_entry_logs'])
    )
    return inhouse_count > 0

def changeUserStatus(data, code_user):
    for entry in data['house_access_controls']:
        if entry['code'] == code_user:
            logs = entry['house_entry_logs']
            last_log = logs[-1] if logs else None

            if last_log:
                URL_FETCH_LOG = f"{BASE_API_URL}{URL_LOG}/{last_log['id']}"
                data_update = {
                    "data": {
                        "status": USER_STATUS['OUT_HOUSE'] if last_log['attributes']['status'] == USER_STATUS['IN_HOUSE'] else USER_STATUS['IN_HOUSE']
                    }
                }
                response = api_request('PUT' if last_log['attributes']['status'] == USER_STATUS['IN_HOUSE'] else 'POST', URL_FETCH_LOG if last_log['attributes']['status'] == USER_STATUS['IN_HOUSE'] else f"{BASE_API_URL}{URL_LOG}", data_update)
                return response is not None
            else:
                data_post = {
                    "data": {
                        "house_access_control": entry['id'],
                        "status": USER_STATUS['IN_HOUSE']
                    }
                }
                response = api_request('POST', f"{BASE_API_URL}{URL_LOG}", data_post)
                return response is not None
    return False

def control_relay(device_id, status):
    relay_pin = RELAY_PIN_CODE.get(device_id)
    if relay_pin is not None:
        relay = machine.Pin(relay_pin, machine.Pin.OUT)
        relay.value(status)

def send_notification(message, house_id, feedback):
    data = {
        "data": {
            "description": message,
            'house': house_id,
            'feedback': feedback
        }
    }
    return api_request('POST', f"{BASE_API_URL}{URL_NOTIFICATION}", data)

def notify_user_entry(extract_access, rfid_uid):
    for entry in extract_access['house_access_controls']:
        if entry['code'] == rfid_uid:
            send_notification(f"Usuario {entry['name']} ha ingresado a la casa.", extract_access['id'], STATE_STATUS['SUCCESS'])

def control_devices(extract_device, turn_on):
    for device in extract_device['home_categories']:
        for devices in device['devices']:
            device_id = devices['attributes']['code']
            control_relay(device_id, 0 if turn_on else 1)
            print(f"Dispositivo {'encendido' if turn_on else 'apagado'}")

connectWifi(SSID, PASSWORD)

def main():
    try:
        while True:
            print("Esperando tarjeta...")
            try:
                rfidInfo = rfid.do_read()
            except Exception as e:
                print("Error al leer la tarjeta:", str(e))
                time.sleep(1)
                continue

            if rfidInfo['status'] != 'ok':
                print("Error al detectar la tarjeta")
                continue

            print("Tarjeta detectada. Leyendo ID...")
            handle_access(rfidInfo)
            time.sleep(0.5)

    except KeyboardInterrupt:
        print("Programa detenido por el usuario.")

def handle_access(rfidInfo):
    try:
        access_data = api_request('GET', URL_FETCH_ACCESS)
        if access_data is None:
            print("No se obtuvieron datos de acceso")
            return

        extract_access = extract_data(access_data, ['name', 'code', 'status', 'house_access_controls'])
        if not houseAccess(rfidInfo['uid'], extract_access):
            send_notification("Acceso no permitido, tarjeta no registrada.", extract_access['id'], STATE_STATUS['WARNING'])
            print("Acceso no permitido")
            return

        data_device = api_request('GET', URL_FETCH_DEVICE)
        if data_device is None:
            send_notification("No se obtuvieron datos del dispositivo.", extract_access['id'], STATE_STATUS['ERROR'])
            print("No se obtuvieron datos del dispositivo")
            return

        extract_device = extract_data(data_device, ['name', 'code', 'status'])
        if not changeUserStatus(extract_access, rfidInfo['uid']):
            send_notification("Error al cambiar el estado del usuario, intente de nuevo.", extract_access['id'], STATE_STATUS['ERROR'])
            print("Error al cambiar el estado del usuario")
            return

        print("Estado de usuario cambiado")
        access_data = api_request('GET', URL_FETCH_ACCESS)
        extract_access = extract_data(access_data, ['name', 'code', 'status'])
        
        if userStatus(extract_access):
            notify_user_entry(extract_access, rfidInfo['uid'])
            control_devices(extract_device, True)
        else:
            send_notification("No hay nadie en la casa, se apagaron los dispositivos.", extract_access['id'], STATE_STATUS['WARNING'])
            control_devices(extract_device, False)

    except Exception as e:
        print("Error en la solicitud a la API:", str(e))

main()
