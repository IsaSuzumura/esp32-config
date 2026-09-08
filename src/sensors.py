import machine
import dht
import time
import config

# ==========================================
# INICIALIZAÇÃO DOS SENSORES
# ==========================================

# 1. DHT11
sensor_dht = dht.DHT11(machine.Pin(config.PIN_DHT))

# 2. BH1750 (Comunicação Direta I2C - Sem bibliotecas externas!)
i2c = machine.SoftI2C(scl=machine.Pin(config.PIN_I2C_SCL), sda=machine.Pin(config.PIN_I2C_SDA))

# 3. Sensor de Umidade do Solo
adc_solo = machine.ADC(machine.Pin(config.PIN_SOIL_MOISTURE))
adc_solo.atten(machine.ADC.ATTN_11DB) 


# ==========================================
# FUNÇÕES DE LEITURA
# ==========================================

def ler_umidade_solo_percentual():
    valor_bruto = adc_solo.read()
    
    if valor_bruto > config.SOIL_ADC_DRY:
        valor_bruto = config.SOIL_ADC_DRY
    elif valor_bruto < config.SOIL_ADC_WET:
        valor_bruto = config.SOIL_ADC_WET
        
    diferenca_total = config.SOIL_ADC_DRY - config.SOIL_ADC_WET
    leitura_atual = config.SOIL_ADC_DRY - valor_bruto
    
    if diferenca_total == 0: return 0.0 # Previne erros matemáticos
    
    porcentagem = (leitura_atual / diferenca_total) * 100.0
    return round(porcentagem, 1)


def ler_clima():
    """Lê temperatura e umidade com um pequeno atraso para o sensor acordar."""
    try:
        time.sleep(0.5) # Dá tempo para o DHT11 processar a leitura
        sensor_dht.measure()
        return sensor_dht.temperature(), sensor_dht.humidity()
    except OSError:
        return None, None


def ler_luminosidade():
    """Comunicação nível de máquina direto com o chip BH1750."""
    try:
        # Envia o comando 0x10 (Continuous High-Resolution Mode)
        i2c.writeto(config.BH1750_ADDR, b'\x10')
        
        # O manual do BH1750 pede 120ms para a luz ser calculada
        time.sleep_ms(150) 
        
        # Recebe os 2 bytes de resposta
        dados = i2c.readfrom(config.BH1750_ADDR, 2)
        
        # Matemática oficial do datasheet para converter os bytes em Lux
        lux = ((dados[0] << 8) | dados[1]) / 1.2
        return round(lux, 1)
    except Exception as e:
        print("Erro de comunicação I2C:", e)
        return None


def obter_dados_completos():
    temp, umid_ar = ler_clima()
    solo_pct = ler_umidade_solo_percentual()
    luminosidade = ler_luminosidade()
    
    return {
        "temperatura": temp,
        "umidade_ar": umid_ar,
        "umidade_solo": solo_pct,
        "luminosidade": luminosidade
    }

# ==========================================
# TESTE LOCAL
# ==========================================
if __name__ == "__main__":
    print("Aguardando sensores estabilizarem...")
    time.sleep(2)
    dados = obter_dados_completos()
    print("Dados gerados:", dados)