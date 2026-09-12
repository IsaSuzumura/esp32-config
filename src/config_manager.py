import ujson
import uos
from config import LIMITES_PADRAO

_ARQUIVO_CONFIG = "config_estufa.json"


def salvar_limites(limites: dict):
    try:
        with open(_ARQUIVO_CONFIG, "w") as f:
            ujson.dump(limites, f)
        print("Limites salvos na flash:", limites)
        return True
    except Exception as e:
        print("Erro ao salvar limites na flash:", e)
        return False


def carregar_limites():
    try:
        if _ARQUIVO_CONFIG not in uos.listdir():
            print("Nenhuma configuracao salva. Usando limites padrao.")
            salvar_limites(LIMITES_PADRAO)
            return dict(LIMITES_PADRAO)

        with open(_ARQUIVO_CONFIG, "r") as f:
            limites = ujson.load(f)
            print("Limites carregados da flash:", limites)
            return limites
    except Exception as e:
        print("Erro ao ler limites da flash, usando padrao:", e)
        return dict(LIMITES_PADRAO)