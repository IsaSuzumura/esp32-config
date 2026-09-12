import dht
import time
from machine import Pin, ADC, I2C
from config import (
    PINO_DHT11,
    PINO_SOLO_ADC,
    PINO_I2C_SDA,
    PINO_I2C_SCL,
    SOLO_VALOR_SECO,
    SOLO_VALOR_MOLHADO,
)

# Inicializacao dos sensores
_dht_sensor = dht.DHT11(Pin(PINO_DHT11))

_solo_adc = ADC(Pin(PINO_SOLO_ADC))
_solo_adc.atten(ADC.ATTN_11DB)   
_solo_adc.width(ADC.WIDTH_12BIT)  

_i2c = I2C(0, scl=Pin(PINO_I2C_SCL), sda=Pin(PINO_I2C_SDA), freq=100000)


_BH1750_ADDR = 0x23
_BH1750_CONTINUOUS_HIGH_RES = 0x10


def ler_temperatura_umidade_ar():
    try:
        _dht_sensor.measure()
        return _dht_sensor.temperature(), _dht_sensor.humidity()
    except Exception as e:
        print("Erro ao ler DHT11:", e)
        return None, None


def ler_umidade_solo():
    try:
        leitura_bruta = _solo_adc.read()
        faixa = SOLO_VALOR_SECO - SOLO_VALOR_MOLHADO
        if faixa == 0:
            return None
        percentual = (SOLO_VALOR_SECO - leitura_bruta) / faixa * 100
        return max(0, min(100, round(percentual, 1)))
    except Exception as e:
        print("Erro ao ler sensor de umidade do solo:", e)
        return None


def ler_luminosidade():
    try:
        _i2c.writeto(_BH1750_ADDR, bytes([_BH1750_CONTINUOUS_HIGH_RES]))
        time.sleep_ms(180) 
        dados = _i2c.readfrom(_BH1750_ADDR, 2)
        bruto = (dados[0] << 8) | dados[1]
        return round(bruto / 1.2, 1)
    except Exception as e:
        print("Erro ao ler BH1750:", e)
        return None


def ler_todos_sensores():
    temperatura, umidade_ar = ler_temperatura_umidade_ar()
    return {
        "temperatura": temperatura,
        "umidade_ar": umidade_ar,
        "umidade_solo": ler_umidade_solo(),
        "luminosidade": ler_luminosidade(),
    }