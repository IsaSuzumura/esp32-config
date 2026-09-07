# Pinos dos sensores
PIN_DHT11 = 4          # D4 - GPIO comum, sem restrição de boot
PIN_SOLO = 34           # D34 - só serve como ENTRADA (ADC), perfeito pro sensor de solo
PIN_BH1750_SDA = 21     # D21 - padrão I2C do ESP32
PIN_BH1750_SCL = 22     # D22 - padrão I2C do ESP32
BH1750_ADDR = 0x23

# Pino do relé (mesmo sem acionar ainda, já deixa mapeado)
PIN_RELE = 5            # D5 - GPIO livre, sem função especial no boot