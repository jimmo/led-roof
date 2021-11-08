import network
import config
import time

sta_if = network.WLAN(network.STA_IF)
sta_if.active(1)
sta_if.config(pm=0)
sta_if.connect(config.network, config.password)

while not sta_if.isconnected():
    time.sleep_ms(100)

print('Connected:', sta_if.ifconfig())
