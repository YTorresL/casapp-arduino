import network
import gc
import time
import urequests as requests

gc.collect()

SSID = 'Note10'
PASSWORD = 'vfeo2261'
URL_API = 'https://7008-190-121-229-254.ngrok-free.app/api/'
URL_FILTER = 'houses?filters[code][$eq]='
HOME_SERIAL_KEY = 'A20241125RC522RF'
URL_RELATIONS = '&populate[home_categories][populate]=home_categories,home_devices'
API_TOKEN = '3c140cfc299089dd58270268ac60bd3fc887c234b4b18d5de80644de5f13647ffc39111ce4b4a777747a658d3ce4ba94d8019f8b314278743eb068561037fde181b8b118f2094ab8c9f7ca395f14bb9407c898a6983206375dbc2780260f38f784472095cb5dc0680fbdf06dcf7e9b1239621dc8901dde38b5d0dda49355feec'

URL_FETCH = URL_API + URL_FILTER + HOME_SERIAL_KEY + URL_RELATIONS

def connectWifi(ssid, password):
    station = network.WLAN(network.STA_IF)
    station.active(True)
    station.connect(ssid, password)
    
    while not station.isconnected():
        print('Conectando...')
        time.sleep(1)
    
    print('Dirección IP:', station.ifconfig()[0])
    print(f'conexion exitosa a {ssid}')
    
def fetchApi(api_url, timeout = 10):
    try:
        response = requests.get(url = api_url, timeout = timeout, headers = {'Authorization': 'Bearer ' + API_TOKEN})
        if response.status_code == 200:
            return response.text
        else:
           print('Error en la solicitud. Codigo de repuesta HTTP=', response.status_code)
           return None
    except Exception as e:
        print('Error en la solicitud:', str(e))
        return None

connectWifi(SSID, PASSWORD)

data = fetchApi(URL_FETCH)
print(data)
        