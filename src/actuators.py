from machine import Pin
from config import PINO_RELE_BOMBA

ESTADO_LIGADO = 0
ESTADO_DESLIGADO = 1

_rele = Pin (PINO_RELE_BOMBA, Pin.OUT)
_rele.value(ESTADO_DESLIGADO) 

_bomba_ligada = False

def ligar_bomba():
    global _bomba_ligada
    _rele.value(ESTADO_LIGADO)
    if not _bomba_ligada:
        print("Bomba d'agua: LIGADA")
    _bomba_ligada = True
    
def desligar_bomba():
    global _bomba_ligada
    _rele.value(ESTADO_DESLIGADO)
    if _bomba_ligada:
        print("Bomba d'agua: DESLIGADA")
    _bomba_ligada = False
    
def estado_bomba():
    return _bomba_ligada