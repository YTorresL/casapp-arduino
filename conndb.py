import network
import gc
import time
import urequests as requests
import read as rfid

gc.collect()

SSID = 'SERVIEDUCA WIFI'
PASSWORD = ''
URL_API = 'https://e2f8-190-121-229-254.ngrok-free.app/api/'
URL_FILTER = 'houses?filters[code][$eq]='
HOME_SERIAL_KEY = 'A20241125RC522RF'
URL_FILTER_HOUSE = '&fields[0]=name&fields[1]=code&fields[2]=status'
URL_RELATIONS_DEVICE = '&populate[home_categories][fields][0]=home_devices&populate[home_categories][populate][home_devices][fields][0]=name&populate[home_categories][populate][home_devices][fields][1]=code&populate[home_categories][populate][home_devices][fields][2]=status'
URL_RELATIONS_ACCESS = '&populate[house_access_controls][fields][0]=name&populate[house_access_controls][fields][1]=code&populate[house_access_controls][fields][2]=status&populate[house_access_controls][fields][3]=house_entry_logs&populate[house_access_controls][populate][house_entry_logs][fields][0]=entry_time&populate[house_access_controls][populate][house_entry_logs][fields][1]=exit_time&populate[house_access_controls][populate][house_entry_logs][fields][2]=status'
API_TOKEN = 'ec271c4dacc695cf081eab99b76e933ef18dadfd5af969506db73bda8fb1f2ce5444c690632956025080a0771499a3dd7e9fded12cce9f18ce82053f749aed7c4a12c3cc0e967f486b00652e8046537f358ee70a82a790108e8ca03cb29d5822cdaf4db0d5c2b32469161524aaf5df272c43155e002ed901fb07b715fbccca80'


URL_FETCH_DEVICE = URL_API + URL_FILTER + HOME_SERIAL_KEY + URL_FILTER_HOUSE + URL_RELATIONS_DEVICE
URL_FETCH_ACCESS = URL_API + URL_FILTER + HOME_SERIAL_KEY + URL_FILTER_HOUSE + URL_RELATIONS_ACCESS

ACCESS_STATUS = {
    "ACTIVED": 1,
    "INACTIVED": 2,
    'DESACTIVATED': 0
}

DEVICE_STATUS = {
    "ACTIVED": 1,
    "INACTIVED": 2,
    'DESACTIVATED': 0
}

HOUSE_STATUS = {
    "ACTIVED": 1,
    "INACTIVED": 2,
    'DESACTIVATED': 0
}

USER_STATUS = {
    "IN_HOUSE": 1,
    "OUT_HOUSE": 2,
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
        response = requests.post(url = api_url, timeout = timeout, headers = {'Authorization': 'Bearer ' + API_TOKEN}, json = data)
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
        response = requests.put(url = api_url, timeout = timeout, headers = {'Authorization': 'Bearer ' + API_TOKEN}, json = data)
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
                'name': x['attributes']['name'],
                'code': x['attributes']['code'],
                'status': x['attributes']['status']
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
            if access['status'] == ACCESS_STATUS['ACTIVED'] and data['status'] == HOUSE_STATUS['ACTIVED']:
                return True
            else:
                return False
        else:
            return False
    return False

#Gestion de dispositivos de la casa si el device_code es correcto y el estado del dispositivo es activo y el estado de la casa es activo

def deviceStatus(device_code, data):
    for device in data['home_categories']:
        for devices in device['devices']:
            if devices['attributes']['code'] == device_code:
                if devices['attributes']['status'] == DEVICE_STATUS['ACTIVED'] and data['status'] == HOUSE_STATUS['ACTIVED']:
                    return True
                else:
                    return False
            else:
                return False
    return False

#Gestionar que alla alguien en la casa 

def userStatus(data):
    for entry in data['house_access_controls']:
        if entry['status'] == USER_STATUS['IN_HOUSE']:
            return True
        else:
            return False   
    return False

#Gestionar si esa tarjeta en especifico estaba de entrada o salida

def entryStatus(data, access_code):
    for entry in data['house_access_controls']:
        if entry['code'] == access_code:
            if entry['status'] == USER_STATUS['IN_HOUSE']:
                return True
            else:
                return False
        else:
            return False
    return False



connectWifi(SSID, PASSWORD)

#Funcion principal que ejecuta siempre espera una tarjeta y verifica si la tarjeta es valida para acceder a la casa asi como si la casa esta activa

def main():  
    while True:
        print("Esperando tarjeta...")
        rfidInfo = rfid.do_read()
        if rfidInfo['status'] == 'ok':
            print("Tarjeta detectada. Leyendo ID...")
            if rfidInfo['status'] == 'ok':
                data_access = fetchApi(URL_FETCH_ACCESS)
                if data_access is not None:
                    access_data = extractAccess(data_access)
                    if houseAccess(rfidInfo['uid'], access_data):
                        device_data = fetchApi(URL_FETCH_DEVICE)
                        if device_data is not None:
                            device_data = extractDevice(device_data)
                            if userStatus(access_data):
                                for device in device_data['home_categories']:
                                    for devices in device['devices']:
                                        device_id = devices['attributes']['code']
                                        if deviceStatus(device_id, device_data):
                                            print("Dispositivo encendido")
                                        else:
                                            print("Dispositivo apagado")
                            else:
                                for device in device_data['home_categories']:
                                    for devices in device['devices']:
                                        device_id = devices['attributes']['code']
                                        if deviceStatus(device_id, devices):
                                            print("Dispositivo apagado")
                                        else:
                                            print("Dispositivo apagado")
                        else:
                            print("No se obtuvieron datos")
                    else:
                        print("Acceso no permitido")
                else:
                    print("No se obtuvieron datos")
                    pass
            else:
                print("Error al leer la tarjeta")
                pass
        else:
            print("Error al detectar la tarjeta")
            pass
        time.sleep(1)

main()