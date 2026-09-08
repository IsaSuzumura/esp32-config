import time
import machine
import config
import sensors

# ==========================================
# CONFIGURAÇÃO DO ATUADOR (Relé)
# ==========================================
rele_bomba = machine.Pin(config.PIN_RELAY_PUMP, machine.Pin.OUT)
rele_bomba.value(1) 

def acionar_irrigacao():
    """Liga a bomba, aguarda o tempo definido e desliga."""
    print(f"💧 Iniciando irrigação por {config.PUMP_ACTIVE_TIME_SEC} segundos...")
    rele_bomba.value(0) # Liga a bomba
    time.sleep(config.PUMP_ACTIVE_TIME_SEC)
    rele_bomba.value(1) # Desliga a bomba
    print("✅ Irrigação finalizada. A bomba foi desligada.")

# ==========================================
# LOOP PRINCIPAL (Edge Computing)
# ==========================================
def loop_principal():
    print("🚀 Sistema de Estufa Autônoma Iniciado!")
    
    while True:
        print("\n--- Analisando Sensores ---")
        dados = sensors.obter_dados_completos()
        print("Status atual:", dados)
        
        umidade_atual = dados.get("umidade_solo")
        
        # Inteligência Local: Toma a decisão de irrigar ou não
        if umidade_atual is not None:
            if umidade_atual < config.IRRIGATION_THRESHOLD_PERCENT:
                print(f"⚠️ Alerta: Umidade ({umidade_atual}%) abaixo do limite ideal ({config.IRRIGATION_THRESHOLD_PERCENT}%).")
                acionar_irrigacao()
            else:
                print(f"🌱 Solo adequadamente úmido ({umidade_atual}%). Nenhuma ação necessária.")
        else:
            print("❌ Erro ao ler a umidade do solo. Pulando verificação por segurança.")
        
        # Pausa antes da próxima checagem (10 segundos para testes rápidos)
        print("⏳ Aguardando próximo ciclo...")
        time.sleep(10)

if __name__ == "__main__":
    try:
        loop_principal()
    except KeyboardInterrupt:
        # Permite parar o código no VS Code (Ctrl+C) sem deixar a bomba ligada direto
        print("\n🛑 Sistema interrompido pelo usuário.")
        rele_bomba.value(1)