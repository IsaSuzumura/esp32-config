import time

_CONT_HIGH_RES = 0x10

class BH1750:
    def __init__(self, i2c, addr=0x23):
        self.i2c = i2c
        self.addr = addr

    def luminosidade(self):
        self.i2c.writeto(self.addr, bytes([_CONT_HIGH_RES]))
        time.sleep_ms(180)
        dado = self.i2c.readfrom(self.addr, 2)
        bruto = (dado[0] << 8) | dado[1]
        return bruto / 1.2