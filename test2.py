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

def servo_move(angulo, servo=machine.PWM(machine.Pin(15), freq=50)):
    if angulo < 0:
        angulo = 0
    elif angulo > 180:
        angulo = 180
    duty = int(40 + (angulo / 180) * 115)  # Conversión a ciclo de trabajo
    servo.duty(duty)

# Lógica para mover el servo al verificar acceso
def servo_control():
    print("Moviendo servo a 90 grados")
    servo_move(90)
    time.sleep(7)
    print("Regresando servo a 0 grados")
    servo_move(0)
    time.sleep(1)

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
        users_in_house = 0  # Contador para usuarios dentro de la casa
        for house in data:
            for access in house['attributes']['house_access_controls']['data']:
                attributes = access['attributes']

                # Obtener los logs de entrada de la casa
                house_entry_logs = attributes['house_entry_logs']['data']
                
                # Verificar si existen logs
                if house_entry_logs:
                    last_log = house_entry_logs[-1]
                    # Verificar el estado del último log
                    if last_log['attributes']['status'] == USER_STATUS['IN_HOUSE']:
                        users_in_house += 1  # Incrementar contador de usuarios en casa
                
                # Verificar código y estado de activación
                if attributes['code'] == code and attributes['status'] == ACCESS_STATUS['ACTIVATED'] and house['attributes']['status'] == HOUSE_STATUS['ACTIVATED']:
                    log_api_url = f"{BASE_API_URL}{URL_LOG}"

                    # Determinar el nuevo estado
                    new_status = USER_STATUS['IN_HOUSE'] if not house_entry_logs else (
                        USER_STATUS['OUT_HOUSE'] if last_log['attributes']['status'] == USER_STATUS['IN_HOUSE'] else USER_STATUS['IN_HOUSE']
                    )

                    json_data = {
                        "data": {
                            "house_access_control": access['id'],
                            "status": new_status
                        }
                    }

                    # Determinar si el usuario está entrando o saliendo de la casa
                    action = "Saliendo de la casa" if new_status == USER_STATUS['OUT_HOUSE'] else "Entrando a la casa"
                    print(action)
                    servo_control()

                    api_request('POST', log_api_url, json_data)

                    if new_status == USER_STATUS['IN_HOUSE']:
                        users_in_house += 1
                    elif new_status == USER_STATUS['OUT_HOUSE']:
                        users_in_house -= 1

                    # Retornar True si hay alguien en casa o el nuevo estado es IN_HOUSE
                    sendNotification(f"Un usuario esta {action}.", house['id'], STATE_STATUS['SUCCESS'])
                    return True if users_in_house > 0 else False

        # Si ninguna tarjeta coincide
        print("Tarjeta no registrada o no activada", house['id'])
        sendNotification("Una tarjeta no registrada intento acceder a la casa.", house['id'], STATE_STATUS['WARNING'])
        return None  # Cambié el retorno aquí a False para mayor claridad

    except Exception as e:
        print("Error en la solicitud a la API access control:", str(e))
        return None  # También retorné False en caso de error

def house_device_control_status(data, access_status):
    try:
        # Iterar sobre cada casa en los datos, verificando que data no sea None y tenga la estructura esperada
        for house in data or []:
            house_attributes = house.get('attributes', {})
            
            # Verificar que 'home_categories' está presente en 'house_attributes'
            home_categories = house_attributes.get('home_categories', {}).get('data', [])
            for category in home_categories:
                category_attributes = category.get('attributes', {})
                
                # Verificar que 'home_devices' está presente en 'category_attributes'
                home_devices = category_attributes.get('home_devices', {}).get('data', [])
                for device in home_devices:
                    attributes = device.get('attributes', {})

                    # Verificar el estado y el código del dispositivo
                    if attributes.get('status') == DEVICE_STATUS['ACTIVATED'] and attributes.get('code') in RELAY_PIN_CODE and house_attributes.get('status') == HOUSE_STATUS['ACTIVATED']:
                        # Determinar el estado del relay basado en access_status
                        relay_status = 0 if access_status else 1
                        # Controlar el relay del dispositivo
                        control_relay(attributes['code'], relay_status)
                        print(f"Dispositivo {attributes['code']} controlado con estado {'OFF' if relay_status else 'ON'}.")
                        time.sleep(1)

                    else:
                        print(f"Dispositivo {attributes.get('code')} no controlado.")


        return True

    except Exception as e:
        print("Error en la solicitud a la API device control:", str(e))
        return False 


def control_relay(device_id, status):
    relay_pin = RELAY_PIN_CODE[device_id]
    relay = machine.Pin(relay_pin, machine.Pin.OUT)
    relay.value(status)

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

        access_status = house_access_control_status(extract_access, rfidInfo['uid'])

        if access_status is None:
            print("Acceso denegado")
            return
        
        device_data = api_request('GET', URL_FETCH_DEVICE)

        if device_data is None:
            sendNotification("No se obtuvieron datos de dispositivos.", extract_access[0]['id'], STATE_STATUS['ERROR'])
            print("No se obtuvieron datos de dispositivos")
            return
        
        extract_device = extract_info(device_data, 'data')
        
        if not house_device_control_status(extract_device, access_status):
            print("No se controló ningún dispositivo")
        
    except Exception as e:
        print("Error en la solicitud a la API:", str(e))

main()
