from machine import Pin, ADC, I2C
import dht
import config
from lib.bh1750 import BH1750

_dht_sensor = dht.DHT11(Pin(config.PIN_DHT11))

_adc_solo = ADC(Pin(config.PIN_SOLO))
_adc_solo.atten(ADC.ATTN_11DB)
_adc_solo.width(ADC.WIDTH_12BIT)

_i2c = I2C(0, scl=Pin(config.PIN_BH1750_SCL), sda=Pin(config.PIN_BH1750_SDA))
_bh1750 = BH1750(_i2c, config.BH1750_ADDR)


def ler_temperatura_umidade():
    try:
        _dht_sensor.measure()
        return {"temp": _dht_sensor.temperature(), "umidade_ar": _dht_sensor.humidity()}
    except OSError as e:
        print("Erro ao ler DHT11:", e)
        return {"temp": None, "umidade_ar": None}


def ler_luminosidade():
    try:
        return round(_bh1750.luminosidade(), 1)
    except OSError as e:
        print("Erro ao ler BH1750:", e)
        return None


def ler_umidade_solo():
    bruto = _adc_solo.read()
    SECO, MOLHADO = 4095, 1500  # ajuste depois com calibração real
    pct = (SECO - bruto) / (SECO - MOLHADO) * 100
    return round(max(0, min(100, pct)), 1)