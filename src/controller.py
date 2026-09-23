import time
import ujson
import network
import machine
from umqttsimple import MQTTClient
import config
import sensors
import actuators
import config_manager

_limites_atuais = {}
_mqtt = None


def _on_mensagem(topic, msg):
    global _limites_atuais
    
    topico = topic.decode()
    print("Mensagem recebida em '%s': %s" % (topico, msg))
    
    if topico == config.TOPICO_CONFIG:
        _processar_config(msg)
    elif topico == config.TOPICO_COMANDOS:
        _processar_comando(msg)


def _processar_config(msg):
    global _limites_atuais
    try:
        dados = ujson.loads(msg)
        novos_limites = {
            "nome": dados.get("nome", _limites_atuais.get("nome", "")),
            "temp_min": float(dados.get("temp_min", 0)),
            "temp_max": float(dados.get("temp_max", 0)),
            "umi_min": float(dados.get("umi_min", 0)),
            "umi_max": float(dados.get("umi_max", 0)),
        }
        _limites_atuais = novos_limites
        config_manager.salvar_limites(_limites_atuais)
        print("Nova configuracao de cultura aplicada:", _limites_atuais)
    except Exception as e:
        print("Erro ao interpretar JSON de estufa/config:", e)
     
        
def _processar_comando(msg):
    comando = msg.decode().strip()
    if comando == "LIGAR_BOMBA":
        print("Comando manual recebido: ligar bomba")
        actuators.ligar_bomba()
    elif comando == "DESLIGAR_BOMBA":
        print("Comando manual recebido: desligar bomba")
        actuators.desligar_bomba()
    else:
        print("Comando desconhecido:", comando)
    
        
def _conectar_mqtt():
    import machine
    import ubinascii
    mac = ubinascii.hexlify(machine.unique_id()).decode()
    client_id_unico = config.MQTT_CLIENT_ID + "_" + mac

    cliente = MQTTClient(
        client_id=client_id_unico,           
        server=config.MQTT_BROKER,
        port=config.MQTT_PORT,
        user=config.MQTT_USER,
        password=config.MQTT_PASSWORD,
        keepalive=60,                        
        ssl=True,
        ssl_params={"server_hostname": config.MQTT_BROKER},
    )
    cliente.set_callback(_on_mensagem)
    
    try:
        cliente.connect()
        cliente.subscribe(config.TOPICO_CONFIG)
        cliente.subscribe(config.TOPICO_COMANDOS)
        print("MQTT conectado e inscrito em '%s' e '%s'" % (
            config.TOPICO_CONFIG, config.TOPICO_COMANDOS))
        return cliente
    except Exception as e:
        print("Falha ao conectar ao broker MQTT:", e)
        return None
    
    
def _publicar_sensores(cliente, leituras: dict):
    global _mqtt
    if cliente is None:
        return
    try:
        payload = ujson.dumps(leituras)
        cliente.publish(config.TOPICO_SENSORES, payload)
        print("Publicado em estufa/sensores:", payload)
    except Exception as e:
        print("Erro ao publicar leituras (provavelmente offline):", e)
        try:
            cliente.sock.close() 
        except:
            pass
        _mqtt = None
       
        
def _executar_edge_computing(leituras: dict):
    umidade_solo = leituras.get("umidade_solo")
    umi_min = _limites_atuais.get("umi_min")

    if umidade_solo is None or umi_min is None:
        return

    if umidade_solo < umi_min:
        actuators.ligar_bomba()
    else:
        actuators.desligar_bomba()
        
        
def iniciar():
    global _limites_atuais, _mqtt
    _limites_atuais = config_manager.carregar_limites()
    _mqtt = _conectar_mqtt()
    
    
def executar_loop():
    global _mqtt

    if not network.WLAN(network.STA_IF).isconnected():
        print("Wi-Fi desconectado! Reiniciando a placa em 3 segundos para restaurar rede...")
        time.sleep(3)
        machine.reset()

    if _mqtt is None:
        _mqtt = _conectar_mqtt()

    if _mqtt is not None:
        try:
            _mqtt.check_msg()
        except Exception as e:
            print("Conexao MQTT perdida no check_msg:", e)
            try:
                _mqtt.sock.close() 
            except:
                pass
            _mqtt = None
            return 

    leituras = sensors.ler_todos_sensores()

    _executar_edge_computing(leituras)
    _publicar_sensores(_mqtt, leituras)

    time.sleep(config.INTERVALO_LEITURA_S)