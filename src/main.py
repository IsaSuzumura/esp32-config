import time
import controller

controller.iniciar()

while True:
    try:
        controller.executar_loop()
    except Exception as e:
        print("Erro inesperado no loop principal:", e)
        time.sleep(5)
