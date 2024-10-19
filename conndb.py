import network
import gc
import time
import urequests as requests
import read as rfid
import machine 

gc.collect()

SSID = 'SERVIEDUCA WIFI'
PASSWORD = ''
URL_API = 'https://1470-190-121-229-254.ngrok-free.app/api/'
URL_FILTER = 'houses?filters[code][$eq]='
HOME_SERIAL_KEY = 'A20241125RC522RF'
URL_FILTER_HOUSE = '&fields[0]=name&fields[1]=code&fields[2]=status&populate[user][fields][3]=user'
URL_RELATIONS_DEVICE = '&populate[home_categories][fields][0]=home_devices&populate[home_categories][populate][home_devices][fields][0]=name&populate[home_categories][populate][home_devices][fields][1]=code&populate[home_categories][populate][home_devices][fields][2]=status'
URL_RELATIONS_ACCESS = '&populate[house_access_controls][fields][0]=name&populate[house_access_controls][fields][1]=code&populate[house_access_controls][fields][2]=status&populate[house_access_controls][fields][3]=house_entry_logs&populate[house_access_controls][populate][house_entry_logs][fields][0]=entry_time&populate[house_access_controls][populate][house_entry_logs][fields][1]=exit_time&populate[house_access_controls][populate][house_entry_logs][fields][2]=status'
API_TOKEN = '50d184507fb4b18d5d964a8e4e4a9aabeccc7f82a0abf5583a8efae33d72c424f3b0f636e97394419c76466bb908ceabc48cb67b53de0bcfccbf9deb4277028b67e1e788d2d3f80548d7c2685f7e0bee0ba7f9a9598e26b7e46341c59d5b729b21460b533ca3dbab83570b6fd78ae432495cf304f9b6d921ff3124ec6794dbe5'
URL_LOG = 'house-entry-logs'
URL_NOTIFICATION = 'house-notifications'

URL_FETCH_DEVICE = URL_API + URL_FILTER + HOME_SERIAL_KEY + URL_FILTER_HOUSE + URL_RELATIONS_DEVICE
URL_FETCH_ACCESS = URL_API + URL_FILTER + HOME_SERIAL_KEY + URL_FILTER_HOUSE + URL_RELATIONS_ACCESS

ACCESS_STATUS = {
    "ACTIVATED": 1,
    "INACTIVE": 2,
    'DESACTIVATED': 0
}

DEVICE_STATUS = {
    "ACTIVATED": 1,
    "INACTIVE": 2,
    'DESACTIVATED': 0
}

HOUSE_STATUS = {
    "ACTIVATED": 1,
    "INACTIVE": 2,
    'DESACTIVATED': 0
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
    
#Conexión a la red wifi

def connectWifi(ssid, password):
    station = network.WLAN(network.STA_IF)
    station.active(True)
    station.connect(ssid, password)
    
    while not station.isconnected():
        print('Conectando...')
        time.sleep(1)
    
    print('Dirección IP:', station.ifconfig()[0])
    print(f'conexion exitosa a {ssid}')
    
#Función para obtener datos de la API

def fetchApi(api_url, timeout = 10):
    try:
        response = requests.get(url = api_url, timeout = timeout, headers = {'Authorization': 'Bearer ' + API_TOKEN})
        if response.status_code == 200:
            return response.json()
        else:
           print('Error en la solicitud. Codigo de repuesta HTTP=', response.status_code)
           return None
    except Exception as e:
        print('Error en la solicitud:', str(e))
        return None

#Función para enviar datos a la API

def sendApi(api_url, data, timeout = 10):
    try:
        response = requests.post(url = api_url, timeout = timeout, headers = {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + API_TOKEN}, json = data)
        if response.status_code == 200:
            return response.json() 
        else:
           print('Error en la solicitud. Codigo de repuesta HTTP=', response.status_code)
           return None
    except Exception as e:
        print('Error en la solicitud:', str(e))
        return None
    
#Función para actualizar datos en la API

def updateApi(api_url, data, timeout = 10):
    try:
        response = requests.put(url = api_url, timeout = timeout, headers = {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + API_TOKEN}, json = data)
        if response.status_code == 200:
            return response.json()
        else:
            print('Error en la solicitud. Codigo de repuesta HTTP=', response.status_code)
            return None
    except Exception as e:
        print('Error en la solicitud:', str(e))
        return None
    
#Funcion para extraer los datos json a variables de python

def extractAccess(json_data):
    if json_data is not None:
        data = json_data['data'][0] 
        attributes = data['attributes']
 
        name = attributes['name']
        code = attributes['code']
        status = attributes['status']
        house_access_controls = attributes['house_access_controls']
        data_access = [
            {
                'id': x['id'],
                'name': x['attributes']['name'],
                'code': x['attributes']['code'],
                'status': x['attributes']['status'],
                'house_entry_logs': x['attributes']['house_entry_logs']['data']
            } for x in house_access_controls['data']
        ]

        return {

            'name': name,
            'code': code,
            'status': status,
            'house_access_controls': data_access
        }
    else:
        print('No se obtuvieron datos')
        return None

def extractDevice(json_data):
    if json_data is not None:
        data = json_data['data'][0] 
        attributes = data['attributes']
        name = attributes['name']
        code = attributes['code']
        status = attributes['status']
        home_categories = attributes['home_categories']
        attributes_device = home_categories['data']
        data_device = [
            {
                'devices': x['attributes']['home_devices']['data'],
            } for x in attributes_device
        ]

        return {
            'name': name,
            'code': code,
            'status': status,
            'home_categories': data_device
        }
    else:
        print('No se obtuvieron datos')
        return None

#Gestion de acceso a la casa si el access_code es correcto y el estado del acceso es activo y el estado de la casa es activo 

def houseAccess(access_code, data):
    for access in data['house_access_controls']:
        if access['code'] == access_code:
            if access['status'] == ACCESS_STATUS['ACTIVATED'] and data['status'] == HOUSE_STATUS['ACTIVATED']:
                return True
            else:
                return False
        else:
            return False
    return False

#Gestion de dispositivos de la casa si el device_code es correcto y el estado del dispositivo es activo y el estado de la casa es activo

def deviceStatus(device_code, data):
    if data['attributes']['code'] == device_code:
        if data['attributes']['status'] == DEVICE_STATUS['ACTIVATED']:
            return True
        else:
            return False
    else:
        return False


#Gestionar que alla alguien en la casa 

def userStatus(data):
    for entry in data['house_access_controls']:
        if entry['house_entry_logs']:
            last_log = entry['house_entry_logs'][-1]
            if last_log['attributes']['status'] == USER_STATUS['IN_HOUSE']:
                return True
            else:
                return False
        else:
            return False
    return False

#Verifica el estado del usuario en especifico y cambialo al estado contrario

def changeUserStatus(data, code_user):
    for entry in data['house_access_controls']:
        if entry['code'] == code_user:
           if entry['house_entry_logs']:
                last_log = entry['house_entry_logs'][-1]
                URL_FETCH_LOG = f"{URL_API}{URL_LOG}/{last_log['id']}"
                URL_FETCH_POST_LOG = f"{URL_API}{URL_LOG}"
                if last_log['attributes']['status'] == USER_STATUS['IN_HOUSE']:
                    data = {
                        "data": {
                            "status": USER_STATUS['OUT_HOUSE'] 
                        }
                    }
                    response = updateApi(URL_FETCH_LOG, data)
                    if response is not None:
                        return True
                    else:
                        return False
                else:
                    data = {
                        "data": {
                            "house_access_control": entry['id'],
                            "status": USER_STATUS['IN_HOUSE']
                        }
                    }
                    response = sendApi(URL_FETCH_POST_LOG, data)
                    if response is not None:
                        return True
                    else:
                        return False
    return data

#Control de los dispositivos de la casa

def control_relay(device_id, status):
    relay_pin = RELAY_PIN_CODE[device_id]
    relay = machine.Pin(relay_pin, machine.Pin.OUT)
    relay.value(status)

#Enviar notificaciones a la app

def sendNotification(message):
    URL_FETCH_NOTIFICATION = f"{URL_API}{URL_NOTIFICATION}"
    data = {
        "data": {
            "description": message,
            'user' : 1
        }
    }
    response = sendApi(URL_FETCH_NOTIFICATION , data)
    if response is not None:
        return True
    else:
        return

connectWifi(SSID, PASSWORD)

#Funcion principal que ejecuta siempre espera una tarjeta y verifica si la tarjeta es valida para acceder a la casa asi como si la casa esta activa

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

            if rfidInfo['status'] == 'ok':
                print("Tarjeta detectada. Leyendo ID...")
                try:
                    data_access = fetchApi(URL_FETCH_ACCESS)
                    if data_access is not None:
                        extract_access = extractAccess(data_access)
                        if houseAccess(rfidInfo['uid'], extract_access):
                            data_device = fetchApi(URL_FETCH_DEVICE)
                            if data_device is not None:
                                extract_device = extractDevice(data_device)
                                if changeUserStatus(extract_access, rfidInfo['uid']):
                                    print("Estado de usuario cambiado")
                                    data_access = fetchApi(URL_FETCH_ACCESS)
                                    extract_access = extractAccess(data_access)
                                    if userStatus(extract_access):
                                        for device in extract_device['home_categories']:
                                            for devices in device['devices']:
                                                device_id = devices['attributes']['code']
                                                if deviceStatus(device_id, devices):
                                                    control_relay(device_id, 0)
                                                    print("Dispositivo encendido")
                                                else:
                                                    control_relay(device_id, 1)

                                                    print("Dispositivo apagado")
                                    else:
                                        for device in extract_device['home_categories']:
                                            for devices in device['devices']:
                                                device_id = devices['attributes']['code']
                                                control_relay(device_id, 1)
                                                print("Dispositivo apagado")
                                else:
                                    print("Error al cambiar el estado del usuario")
                            else:
                                print("No se obtuvieron datos del dispositivo")
                        else:
                            print("Acceso no permitido")
                    else:
                        print("No se obtuvieron datos de acceso")
                except Exception as e:
                    print("Error en la solicitud a la API:", str(e))
            else:
                print("Error al detectar la tarjeta")
            time.sleep(0.5)  # Espera corta para no bloquear el loop
    except KeyboardInterrupt:
        print("Programa detenido por el usuario.")

main()
