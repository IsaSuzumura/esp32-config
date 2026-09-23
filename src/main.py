import time
import machine

# Watchdog: se o programa travar por mais de 60 s (ex.: conexão de rede
# pendurada), o próprio ESP32 se reinicia. Essencial para quem fica na
# tomada sem ninguém olhando.
_wdt = machine.WDT(timeout=60000)

try:
    import controller
    import actuators
    controller.iniciar()
except Exception as e:
    # Longe do computador ninguém vê o erro: espera um pouco e reinicia
    print("Erro fatal ao iniciar:", e)
    time.sleep(10)
    machine.reset()

try:
    while True:
        try:
            controller.executar_loop()
        except Exception as e:
            print("Erro inesperado no loop principal:", e)
            time.sleep(5)
        _wdt.feed()  # "estou vivo" - enquanto o loop girar, o watchdog não reinicia
except KeyboardInterrupt:
    # Programa parado pelo computador (MicroPico / Ctrl+C)
    actuators.desligar_bomba()
    print("Programa parado. O watchdog vai reiniciar a placa em ate 60 s.")