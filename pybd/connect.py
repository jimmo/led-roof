import network
import config
import time

sta_if = network.WLAN(network.STA_IF)
sta_if.active(1)
sta_if.config(pm=0)

def reconnect():
    if sta_if.isconnected():
        return

    print('Reconnecting...')

    while True:
        sta_if.connect(config.network, config.password)

        while sta_if.status() == 1:
            time.sleep_ms(100)

        if sta_if.isconnected():
            print('Connected:', sta_if.ifconfig())
            break

        time.sleep_ms(10000)


reconnect()
