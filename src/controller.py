import time
import ujson
import network
import machine
import ubinascii
from umqttsimple import MQTTClient
import config
import sensors
import actuators
import config_manager

# Valores com padrão, caso ainda não existam no config.py
_TOPICO_BOMBA = getattr(config, "TOPICO_BOMBA", "estufa/bomba")
_DURACAO_REGA_MS = int(getattr(config, "DURACAO_REGA_MANUAL_S", 5) * 1000)
_INTERVALO_LEITURA_MS = int(config.INTERVALO_LEITURA_S * 1000)
_RECONEXAO_MIN_MS = 5000       # espera entre tentativas de conectar ao broker...
_RECONEXAO_MAX_MS = 60000      # ...que dobra a cada falha, até 1 min
_INTERVALO_WIFI_MS = 30000     # sem Wi-Fi: tenta reconectar a cada 30 s, sem parar a estufa
_PAUSA_LOOP_MS = 100  # o loop gira a cada 0,1 s para responder rápido aos comandos
# DESLIGADO de propósito: o HiveMQ derruba a conexão do ESP toda vez que ele
# publica em estufa/bomba (a credencial do ESP não tem permissão nesse tópico).
# Para religar: libere estufa/# para a credencial do ESP no HiveMQ e troque para True.
_PUBLICAR_ESTADO_BOMBA = False
_INTERVALO_PING_MS = 10000       # pergunta "você está aí?" ao broker a cada 10 s...
_LIMITE_SEM_RESPOSTA_MS = 25000  # ...e se ele não responder em 25 s, a conexão morreu

_limites_atuais = {}
_mqtt = None
_fim_rega_manual = None          # ticks_ms em que a rega manual termina (None = sem rega manual)
_proxima_leitura = 0
_proxima_tentativa_mqtt = 0
_espera_reconexao_ms = _RECONEXAO_MIN_MS
_wlan = network.WLAN(network.STA_IF)
_wifi_estava_online = None
_proxima_tentativa_wifi = 0
_estado_bomba_publicado = None   # último estado da bomba enviado ao broker
_proximo_ping = 0
_ultima_resposta_broker = 0


# ---------------------------------------------------------------------------
# Mensagens recebidas
# ---------------------------------------------------------------------------

def _on_mensagem(topic, msg):
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
        if novos_limites == _limites_atuais:
            return  # mesma cultura (ex.: mensagem retida reenviada na reconexão)
        _limites_atuais = novos_limites
        config_manager.salvar_limites(_limites_atuais)
        print("Nova configuracao de cultura aplicada:", _limites_atuais)
    except Exception as e:
        print("Erro ao interpretar JSON de estufa/config:", e)


def _processar_comando(msg):
    global _fim_rega_manual
    comando = msg.decode().strip().upper()

    if comando == "LIGAR_BOMBA":
        # A rega manual tem duração fixa e, enquanto dura, a lógica automática NÃO desliga a bomba
        _fim_rega_manual = time.ticks_add(time.ticks_ms(), _DURACAO_REGA_MS)
        print("Rega manual: bomba ligada por %d s" % (_DURACAO_REGA_MS // 1000))
        actuators.ligar_bomba()
    elif comando == "DESLIGAR_BOMBA":
        _fim_rega_manual = None
        print("Comando manual recebido: desligar bomba")
        actuators.desligar_bomba()
    else:
        print("Comando desconhecido:", comando)


def _atualizar_rega_manual():
    """Desliga a bomba quando o tempo da rega manual acaba."""
    global _fim_rega_manual
    if _fim_rega_manual is None:
        return
    if time.ticks_diff(time.ticks_ms(), _fim_rega_manual) >= 0:
        _fim_rega_manual = None
        actuators.desligar_bomba()
        print("Rega manual concluida.")


# ---------------------------------------------------------------------------
# Conexão e publicação MQTT
# ---------------------------------------------------------------------------

def _descartar_mqtt():
    global _mqtt
    if _mqtt is not None:
        try:
            _mqtt.sock.close()
        except Exception:
            pass
    _mqtt = None


def _conectar_mqtt():
    global _estado_bomba_publicado, _proximo_ping, _ultima_resposta_broker
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
        for topico in (config.TOPICO_CONFIG, config.TOPICO_COMANDOS):
            rc = cliente.subscribe(topico)
            if rc == 0x80:
                print("ATENCAO: o broker RECUSOU a inscricao em '%s' "
                      "(a credencial do ESP32 nao tem permissao nesse topico)" % topico)
            else:
                print("Inscrito em '%s'" % topico)
        print("MQTT conectado.")
        _estado_bomba_publicado = None  # força reenviar o estado da bomba
        _ultima_resposta_broker = time.ticks_ms()
        _proximo_ping = time.ticks_add(time.ticks_ms(), _INTERVALO_PING_MS)
        return cliente
    except Exception as e:
        print("Falha ao conectar ao broker MQTT:", e)
        try:
            cliente.sock.close()
        except Exception:
            pass
        return None


def _tentar_reconectar_mqtt():
    global _mqtt, _proxima_tentativa_mqtt, _espera_reconexao_ms
    if _mqtt is not None:
        return
    if time.ticks_diff(time.ticks_ms(), _proxima_tentativa_mqtt) < 0:
        return  # espera entre tentativas para não travar o loop
    _mqtt = _conectar_mqtt()
    if _mqtt is None:
        # Wi-Fi sem internet ou broker fora: cada tentativa trava o loop alguns
        # segundos, então espaçamos cada vez mais (5 s, 10 s, 20 s... até 60 s)
        _espera_reconexao_ms = min(_espera_reconexao_ms * 2, _RECONEXAO_MAX_MS)
    else:
        _espera_reconexao_ms = _RECONEXAO_MIN_MS
    _proxima_tentativa_mqtt = time.ticks_add(time.ticks_ms(), _espera_reconexao_ms)


def _manter_wifi():
    """Retorna True se há Wi-Fi. Sem Wi-Fi, tenta reconectar em segundo plano
    (o wlan.connect do ESP32 não bloqueia) e a estufa continua funcionando."""
    global _wifi_estava_online, _proxima_tentativa_wifi, _proxima_tentativa_mqtt, _espera_reconexao_ms
    online = _wlan.isconnected()

    if online != _wifi_estava_online:  # só avisa quando o estado muda
        if online:
            print("Wi-Fi conectado:", _wlan.ifconfig()[0])
            _espera_reconexao_ms = _RECONEXAO_MIN_MS
            _proxima_tentativa_mqtt = time.ticks_ms()  # conecta ao broker já
        else:
            print("Sem Wi-Fi: operando em MODO AUTONOMO com os limites salvos:", _limites_atuais)
            _descartar_mqtt()
        _wifi_estava_online = online

    if not online and time.ticks_diff(time.ticks_ms(), _proxima_tentativa_wifi) >= 0:
        _proxima_tentativa_wifi = time.ticks_add(time.ticks_ms(), _INTERVALO_WIFI_MS)
        try:
            if _wlan.status() != network.STAT_CONNECTING:
                _wlan.active(True)
                _wlan.connect(config.WIFI_SSID, config.WIFI_PASSWORD)
        except Exception as e:
            print("Tentativa de reconectar Wi-Fi falhou:", e)

    return online


def _verificar_mensagens():
    global _ultima_resposta_broker
    if _mqtt is None:
        return
    try:
        for _ in range(10):  # processa as mensagens que estiverem acumuladas
            if _mqtt.check_msg() is None:
                break
            _ultima_resposta_broker = time.ticks_ms()  # broker respondeu: conexão viva
    except OSError as e:
        if e.args and e.args[0] == 11:  # EAGAIN: socket TLS sem dados agora, não é erro
            return
        print("Conexao MQTT perdida no check_msg:", e)
        _descartar_mqtt()
    except Exception as e:
        print("Conexao MQTT perdida no check_msg:", e)
        _descartar_mqtt()


def _checar_conexao_viva():
    """Antes, se o broker fechasse a conexão, o ESP não percebia: ficava num
    socket morto e os comandos do app se perdiam. Agora ele manda um ping a
    cada 10 s e, se o broker não responder, reconecta."""
    global _proximo_ping
    if _mqtt is None:
        return
    agora = time.ticks_ms()
    if time.ticks_diff(agora, _ultima_resposta_broker) > _LIMITE_SEM_RESPOSTA_MS:
        print("Broker nao responde ha %d s: conexao morta, reconectando..." % (_LIMITE_SEM_RESPOSTA_MS // 1000))
        _descartar_mqtt()
        return
    if time.ticks_diff(agora, _proximo_ping) >= 0:
        _proximo_ping = time.ticks_add(agora, _INTERVALO_PING_MS)
        try:
            _mqtt.ping()
        except Exception as e:
            print("Conexao MQTT perdida no ping:", e)
            _descartar_mqtt()


def _publicar(topico, payload, retain=False):
    if _mqtt is None:
        return False
    try:
        _mqtt.publish(topico, payload, retain=retain)
        return True
    except Exception as e:
        print("Erro ao publicar em %s (provavelmente offline): %s" % (topico, e))
        _descartar_mqtt()
        return False


def _publicar_sensores(leituras):
    payload = ujson.dumps(leituras)
    if _publicar(config.TOPICO_SENSORES, payload):
        print("Publicado em %s: %s" % (config.TOPICO_SENSORES, payload))


def _publicar_estado_bomba(forcar=False):
    """Publica LIGADA/DESLIGADA quando o estado muda (e junto de cada leitura)."""
    global _estado_bomba_publicado
    if not _PUBLICAR_ESTADO_BOMBA:
        return
    estado = actuators.estado_bomba()
    if estado == _estado_bomba_publicado and not forcar:
        return
    texto = "LIGADA" if estado else "DESLIGADA"
    if _publicar(_TOPICO_BOMBA, texto):
        print("Publicado em %s: %s" % (_TOPICO_BOMBA, texto))
        _estado_bomba_publicado = estado


# ---------------------------------------------------------------------------
# Lógica de borda
# ---------------------------------------------------------------------------

def _executar_edge_computing(leituras):
    if _fim_rega_manual is not None:
        return  # rega manual em andamento: a lógica automática espera ela terminar

    umidade_solo = leituras.get("umidade_solo")
    umi_min = _limites_atuais.get("umi_min")

    if umi_min is None:
        return
    if umidade_solo is None:
        # Sensor de solo falhou: por segurança a bomba não fica ligada "no escuro"
        actuators.desligar_bomba()
        return

    if umidade_solo < umi_min:
        actuators.ligar_bomba()
    else:
        actuators.desligar_bomba()


# ---------------------------------------------------------------------------
# Ciclo principal
# ---------------------------------------------------------------------------

def iniciar():
    global _limites_atuais, _mqtt, _proxima_leitura, _proxima_tentativa_mqtt
    # Os limites da última cultura escolhida no app ficam salvos na flash,
    # então a estufa já liga sabendo o que fazer, mesmo sem internet.
    _limites_atuais = config_manager.carregar_limites()
    if _wlan.isconnected():
        _mqtt = _conectar_mqtt()
    _proxima_tentativa_mqtt = time.ticks_add(time.ticks_ms(), _RECONEXAO_MIN_MS)
    _proxima_leitura = time.ticks_ms()  # primeira leitura acontece já no primeiro ciclo


def executar_loop():
    global _proxima_leitura

    # ANTES: sem Wi-Fi a placa reiniciava e a irrigação parava.
    # AGORA: a parte de rede é opcional; o controle da estufa roda sempre.
    if _manter_wifi():
        _tentar_reconectar_mqtt()
        _verificar_mensagens()      # comandos do app são atendidos em ~0,1 s
        _checar_conexao_viva()

    _atualizar_rega_manual()

    if time.ticks_diff(time.ticks_ms(), _proxima_leitura) >= 0:
        _proxima_leitura = time.ticks_add(time.ticks_ms(), _INTERVALO_LEITURA_MS)
        leituras = sensors.ler_todos_sensores()
        _executar_edge_computing(leituras)   # funciona com ou sem internet
        _publicar_sensores(leituras)         # só publica se houver conexão
        _publicar_estado_bomba(forcar=True)

    _publicar_estado_bomba()
    time.sleep_ms(_PAUSA_LOOP_MS)