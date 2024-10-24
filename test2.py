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
HOME_SERIAL_KEY = 'A20241125RC522RF'
URL_FILTER_HOUSE = '&fields[0]=name&fields[1]=code&fields[2]=status'
API_TOKEN = 'b07dbc7cd57ce26801dea597c8f9a612ebe07fa7c501b8eecde0403b5a5449cd00d4314b2cdaf3dcbe845ba049dd431a218216e9dba57fda3960b8c69b0e7db169352df87081a0621c66906119fae740f62dfa3f992f3180d2ff9974e6139754d3053a283c1fcfff1529dbdad496df16505a31005d5c1aa752fd46a32405ab79'
URL_LOG = 'house-entry-logs'
URL_NOTIFICATION = 'house-notifications'

URL_FETCH_DEVICE = f"{BASE_API_URL}houses?filters[code][$eq]={HOME_SERIAL_KEY}{URL_FILTER_HOUSE}&populate[home_categories][fields][0]=home_devices&populate[home_categories][populate][home_devices][fields][0]=code&populate[home_categories][populate][home_devices][fields][1]=status"
URL_FETCH_ACCESS = f"{BASE_API_URL}houses?filters[code][$eq]={HOME_SERIAL_KEY}{URL_FILTER_HOUSE}&populate[house_access_controls][fields][0]=code&populate[house_access_controls][fields][1]=status&populate[house_access_controls][fields][2]=house_entry_logs&populate[house_access_controls][populate][house_entry_logs][fields][0]=status"

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
    
def extract_info(data, key):
    try:
        return data[key]
    except KeyError:
        return None
    
def house_access_control_status(data, code):
    try:
        for house in data:
            for access in house['attributes']['house_access_controls']['data']:
                attributes = access['attributes']
                
                # Verificar código y estado de activación
                if attributes['code'] == code and attributes['status'] == ACCESS_STATUS['ACTIVATED']:
                    log_api_url = f"{BASE_API_URL}{URL_LOG}"

                    # Verificar si existen logs y el último log
                    house_entry_logs = attributes['house_entry_logs']['data']
                    if house_entry_logs:
                        last_log = house_entry_logs[-1]

                        # Verificar el estado del último log
                        new_status = USER_STATUS['OUT_HOUSE'] if last_log['attributes']['status'] == USER_STATUS['IN_HOUSE'] else USER_STATUS['IN_HOUSE']
                        json_data = {
                            "data": {
                                "house_access_control": access['id'],
                                "status": new_status
                            }
                        }

                        # Determinar si el usuario está entrando o saliendo de la casa
                        action = "Saliendo de la casa" if new_status == USER_STATUS['OUT_HOUSE'] else "Entrando a la casa"
                        print(action)
                        api_request('POST', log_api_url, json_data)
                        return new_status
        return None

    except Exception as e:
        print("Error en la solicitud a la API access control:", str(e))
        return None

def house_device_control_status(data, access_status):
    try:
        for house in data:
            for category in house['attributes']['home_categories']['data']:
                for device in category['attributes']['home_devices']['data']:
                    attributes = device['attributes']

                    # Verificar código y estado de activación
                    if attributes['status'] == DEVICE_STATUS['ACTIVATED'] and attributes['code'] in RELAY_PIN_CODE:
                        relay_status = 0 if access_status == USER_STATUS['IN_HOUSE'] else 1
                        control_relay(attributes['code'], relay_status)
                        print(f"Dispositivo {attributes['code']} controlado con estado {'OFF' if relay_status else 'ON'}.")
                        return True
                
        return False

    except Exception as e:
        print("Error en la solicitud a la API device control:", str(e))
        return False

def control_relay(device_id, status):
    relay_pin = RELAY_PIN_CODE[device_id]
    relay = machine.Pin(relay_pin, machine.Pin.OUT)
    relay.value(status)

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
            print("No se obtuvieron datos de acceso")
            return

        extract_access = extract_info(access_data, 'data')

        access_status = house_access_control_status(extract_access, rfidInfo['uid'])

        if access_status is None:
            print("Acceso denegado")
            return
        
        device_data = api_request('GET', URL_FETCH_DEVICE)

        if device_data is None:
            print("No se obtuvieron datos de dispositivos")
            return
        
        extract_device = extract_info(device_data, 'data')

        if not house_device_control_status(extract_device, access_status):
            print("No se controló ningún dispositivo")
            return
            
    except Exception as e:
        print("Error en la solicitud a la API:", str(e))

main()
