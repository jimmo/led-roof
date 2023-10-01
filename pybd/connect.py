import network
import config
import time

print('Setting hostname to:', config.hostname)
network.hostname(config.hostname)

sta_if = network.WLAN(network.STA_IF)

def reconnect():
    if sta_if.isconnected():
        return

    print('Reconnecting to', config.network)
    sta_if.active(0)
    sta_if.active(1)
    sta_if.config(pm=0)
    sta_if.connect(config.network, config.password, bssid=config.bssid)

    for i in range(200):
        time.sleep_ms(100)
        print(sta_if.status(), sta_if.status('rssi'))
        if sta_if.isconnected():
            print('Connected:', sta_if.ifconfig())
            return


reconnect()
