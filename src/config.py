# Configurações do Sistema
# Wi-Fi
WIFI_SSID = "RedeInferior"
WIFI_PASSWORD = "04121417"

# Broker MQTT
MQTT_BROKER = "c5f638bd9b894b7591b3df0cab6ee925.s1.eu.hivemq.cloud"
MQTT_PORT = 8883
MQTT_CLIENT_ID = "estufa_esp32_device"
MQTT_USER = "estufa_esp32"
MQTT_PASSWORD = "mqtt@estuf4"

# Tópicos MQTT
TOPICO_SENSORES = "estufa/sensores"
TOPICO_CONFIG = "estufa/config"
TOPICO_COMANDOS = "estufa/comandos"

# Pinos do ESP32
PINO_DHT11 = 4          # Temperatura/umidade do ar
PINO_SOLO_ADC = 34      # Umidade do solo (entrada analógica)
PINO_I2C_SDA = 21       # BH1750 (luminosidade) - I2C
PINO_I2C_SCL = 22
PINO_RELE_BOMBA = 26    # Relé da bomba

# Calibração sensor de umidade do solo
SOLO_VALOR_SECO = 3300
SOLO_VALOR_MOLHADO = 1200

INTERVALO_LEITURA_S = 10

LIMITES_PADRAO = {
    "nome": "Padrao",
    "temp_min": 15.0,
    "temp_max": 30.0,
    "umi_min": 30.0,
    "umi_max": 70.0,
}