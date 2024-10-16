import machine
import time
from mfrc522 import MFRC522

# Pines para el RFID
RST_PIN = 0  # Pin RST del RFID
SS_PIN = 2   # Pin SDA del RFID

# Crear objeto RFID
rfid = MFRC522(spi=machine.SPI(1, baudrate=1000000, polarity=0, phase=0), ss=machine.Pin(SS_PIN), rst=machine.Pin(RST_PIN))

# Pines del relé
relay_pins = [5, 4, 3, 1]  # Pines del relé
authorized_card = "C982253"  # Código autorizado

access_granted = False  # Estado de acceso

# Inicializar pines del relé
for pin in relay_pins:
    machine.Pin(pin, machine.Pin.OUT).value(0)  # Apagar relés al inicio

print("Iniciando...")
time.sleep(1)
print("RFID iniciado.")

while True:
    print("Esperando tarjeta...")
    # Revisar si hay nueva tarjeta
    (status, tag_type) = rfid.request(rfid.REQIDL)
    if status == rfid.OK:  # Si se detecta una tarjeta
        print("Tarjeta detectada.")
        
        # Leer el ID de la tarjeta
        (status, uid) = rfid.anticoll()
        if status == rfid.OK:
            card_id = ''.join([hex(x)[2:].upper() for x in uid])  # Convertir a hex y mayúsculas
            print("ID de la tarjeta:", card_id)  # Mostrar el ID leído

            # Verificar si la tarjeta es la autorizada
            if card_id == authorized_card:
                if not access_granted:
                    # Acceso permitido
                    print("Acceso")
                    access_granted = True
                    for pin in relay_pins:
                        machine.Pin(pin, machine.Pin.OUT).value(1)  # Encender luces del relé
                else:
                    # Salida
                    print("Salida")
                    access_granted = False
                    for pin in relay_pins:
                        machine.Pin(pin, machine.Pin.OUT).value(0)  # Apagar luces del relé
            else:
                # Tarjeta no autorizada
                print("No perteneces a esta casa")

            time.sleep(1)  # Esperar un segundo antes de permitir otra lectura lectura