# ==========================================
# CONFIGURAÇÕES DE HARDWARE (Mapeamento de Pinos)
# ==========================================

# Sensor de Temperatura e Umidade do Ar (DHT11)
PIN_DHT = 4

# Sensor de Luminosidade (BH1750 - Barramento I2C)
PIN_I2C_SDA = 21
PIN_I2C_SCL = 22
BH1750_ADDR = 0x23

# Sensor de Umidade do Solo (Analógico)
PIN_SOIL_MOISTURE = 34

# Atuador: Módulo Relé (Bomba de Água)
PIN_RELAY_PUMP = 5


# ==========================================
# REGRAS DE NEGÓCIO E CALIBRAÇÃO (Edge Computing)
# ==========================================
SOIL_ADC_DRY = 4095     # Testado: Terra seca 
SOIL_ADC_WET = 0        # Testado: Água

# Limiar de Irrigação (Threshold)
IRRIGATION_THRESHOLD_PERCENT = 40.0 

# Tempo de rega em segundos (evita encharcar o substrato)
PUMP_ACTIVE_TIME_SEC = 5 


# ==========================================
# CONFIGURAÇÕES MQTT (Tópicos)
# ==========================================
MQTT_CLIENT_ID = "esp32_estufa_01"
MQTT_TOPIC_TELEMETRY = b"estufa/sensores" 
MQTT_TOPIC_COMMAND   = b"estufa/controle"