import time
import sensors

print("=== Teste de sensores - Biotika ===")

while True:
    ar = sensors.ler_temperatura_umidade()
    lux = sensors.ler_luminosidade()
    solo = sensors.ler_umidade_solo()

    print("Temp: {} C | Umid. ar: {} % | Luz: {} lux | Umid. solo: {} %".format(
        ar["temp"], ar["umidade_ar"], lux, solo
    ))

    time.sleep(2)