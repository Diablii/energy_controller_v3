from machine import UART, Pin
import utime
import struct
# from threading import Thread
import _thread
import network
import time
import logging
from arduino_iot_cloud import ArduinoCloudClient
from secrets import WIFI_SSID, WIFI_PASSWORD, DEVICE_ID, CLOUD_PASSWORD

commands = {
    "L1_voltage": [14, 1],
    "L2_voltage": [16, 1],
    "L3_voltage": [18, 1],
    "L1_current": [22, 1],
    "L2_current": [24, 1],
    "L3_current": [26, 1],
    # "L1_active_power": [30, 1],
    # "L2_active_power": [32, 1],
    # "L3_active_power": [34, 1],
    "Total_forward_active_energy": [264, 2],
    "Total_reverse_active_energy": [272, 2],
}

NUM_UART = 0x0
SLAVE_ADDRESS = 0x0
HOLD_REGISTER_REQUEST = 0x03
DEFAULT_REGISTER = 0x0
DEFAULT_REGISTER_NUM = 0x01

modbus_frame = {
    "L1_voltage": 0,
    "L2_voltage": 0,
    "L3_voltage": 0,
    "L1_current": 0,
    "L2_current": 0,
    "L3_current": 0,
    # "L1_active_power": 0,
    # "L2_active_power": 0,
    # "L3_active_power": 0,
    "Total_forward_active_energy": [0, 0],
    "Total_reverse_active_energy": [0, 0],
}

modbus_frame_old = {
    "L1_voltage": 0,
    "L2_voltage": 0,
    "L3_voltage": 0,
    "L1_current": 0,
    "L2_current": 0,
    "L3_current": 0,
    # "L1_active_power": 0,
    # "L2_active_power": 0,
    # "L3_active_power": 0,
    "Total_forward_active_energy": [0, 0],
    "Total_reverse_active_energy": [0, 0],
}

diff_reverse_active_energy = 0
diff_forward_active_energy = 0


def calculate_crc(request_to_crc: bytes) -> bytes:
    crc = 0xFFFF
    for i in request_to_crc:
        crc ^= i
        for _ in range(8):
            if crc & 1:
                crc >>= 1
                crc ^= 0xA001
            else:
                crc >>= 1
    return crc.to_bytes(2, 'little')


def modbus_request(uart, slave_addr=SLAVE_ADDRESS, register_addr=DEFAULT_REGISTER,
                   num_registers=DEFAULT_REGISTER_NUM, function_code=HOLD_REGISTER_REQUEST):
    request = bytearray([slave_addr, function_code,
                         (register_addr >> 8) & 0xFF,
                         register_addr & 0xFF,
                         (num_registers >> 8) & 0xFF,
                         num_registers & 0xFF])
    crc = calculate_crc(request)
    request.extend(crc)
    isResponse = False
    response = bytes
    while not isResponse:
        uart.write(request)
        utime.sleep(1)
        if uart.any():
            response = uart.read()
            if response:
                isResponse = True
    return response


def wifi_connect():
    if not WIFI_SSID or not WIFI_PASSWORD:
        raise Exception("Network is not configured. Set SSID and passwords in secrets.py")
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(WIFI_SSID, WIFI_PASSWORD)
    while not wlan.isconnected():
        logging.info("Trying to connect. Note this may take a while...")
        time.sleep_ms(500)
    logging.info(f"WiFi Connected {wlan.ifconfig()}")


def update_l1voltage(client):
    global modbus_frame
    return modbus_frame["L1_voltage"]


def update_l2voltage(client):
    global modbus_frame
    return modbus_frame["L2_voltage"]


def update_l3voltage(client):
    global modbus_frame
    return modbus_frame["L3_voltage"]


def update_l1current(client):
    global modbus_frame
    return modbus_frame["L1_current"]


def update_l2current(client):
    global modbus_frame
    return modbus_frame["L2_current"]


def update_l3current(client):
    global modbus_frame
    return modbus_frame["L3_current"]


# def update_l1power(client):
#     global modbus_frame
#     return modbus_frame["L1_active_power"]
#
#
# def update_l2power(client):
#     global modbus_frame
#     return modbus_frame["L2_active_power"]
#
#
# def update_l3power(client):
#     global modbus_frame
#     return modbus_frame["L3_active_power"]


def update_total_energy_reverse(client):
    global modbus_frame
    return modbus_frame["Total_reverse_active_energy"][0]


def update_energy_reverse_diff(client):
    global modbus_frame
    global modbus_frame_old
    global diff_reverse_active_energy
    command = "Total_reverse_active_energy"
    print("modbus_frame:", modbus_frame[command])
    print("modbus_frame_old:", modbus_frame_old[command])
    old_time = modbus_frame_old[command][1]
    new_time = modbus_frame[command][1]
    old_value = int(modbus_frame_old[command][0])
    new_value = int(modbus_frame[command][0])
    diff_time = new_time - old_time
    print("diff_time:", diff_time)
    if diff_time > 0:
        diff_time_norm = int(3600 / diff_time)
        diff_reverse_active_energy = (new_value - old_value) * diff_time_norm
        modbus_frame_old[command] = modbus_frame[command].copy()
        print("modbus_frame:", modbus_frame[command])
        print("modbus_frame_old:", modbus_frame_old[command])
        print("diff_reverse_energy:", diff_reverse_active_energy)
        if 0 <= diff_reverse_active_energy <= 5100:
            return diff_reverse_active_energy
        else:
            return 0
    else:
        return -1


def update_energy_forward_diff(client):
    global modbus_frame
    global modbus_frame_old
    global diff_forward_active_energy
    command = "Total_forward_active_energy"
    print("modbus_frame:", modbus_frame[command])
    print("modbus_frame_old:", modbus_frame_old[command])
    old_time = modbus_frame_old[command][1]
    new_time = modbus_frame[command][1]
    old_value = int(modbus_frame_old[command][0])
    new_value = int(modbus_frame[command][0])
    diff_time = new_time - old_time
    if diff_time > 0:
        diff_time_norm = int(3600 / diff_time)
        diff_forward_active_energy = (new_value - old_value) * diff_time_norm
        modbus_frame_old[command] = modbus_frame[command].copy()
        print("modbus_frame:", modbus_frame[command])
        print("modbus_frame_old:", modbus_frame_old[command])
        print("diff_forward_energy:", diff_forward_active_energy)
        if 0 <= diff_forward_active_energy <= 15000:
            return diff_forward_active_energy
        else:
            return 0
    else:
        return -1


def hard_reset(client, value):
    if value:
        machine.reset()


def read_modbus_frame():
    uart = UART(0, baudrate=9600, bits=8, parity=0, stop=1, tx=Pin(0), rx=Pin(1))
    state = 0
    global modbus_frame
    while True:
        if state == 1:
            while True:
                # for command in ["L1_voltage", "L2_voltage", "L3_voltage", "L1_current", "L2_current", "L3_current",
                #                 "L1_active_power", "L2_active_power", "L3_active_power",
                #                 "Total_forward_active_energy", "Total_reverse_active_energy"]:
                for command in ["L1_voltage", "L2_voltage", "L3_voltage", "L1_current", "L2_current", "L3_current",
                                "Total_forward_active_energy", "Total_reverse_active_energy"]:
                    parameter = commands[command]
                    response = None
                    while not response:
                        response = modbus_request(uart, slave_addr=1, register_addr=parameter[0],
                                                  num_registers=parameter[1], function_code=3)
                        utime.sleep(0.1)
                    data = int.from_bytes(response[3:7], 'big')
                    float_value = struct.unpack('>f', struct.pack('>I', data))[0]
                    timestamp = utime.time()
                    if command == "Total_forward_active_energy":
                        modbus_frame[command][0] = int(float_value * 1000)
                        modbus_frame[command][1] = timestamp
                    elif command == "Total_reverse_active_energy":
                        modbus_frame[command][0] = int(float_value * 1000)
                        modbus_frame[command][1] = timestamp
                    else:
                        modbus_frame[command] = float_value
        elif state == 0:
            print("first_cycle_start")
            # for command in ["L1_voltage", "L2_voltage", "L3_voltage", "L1_current", "L2_current", "L3_current",
            #                 "L1_active_power", "L2_active_power", "L3_active_power",
            #                 "Total_forward_active_energy", "Total_reverse_active_energy"]:
            for command in ["L1_voltage", "L2_voltage", "L3_voltage", "L1_current", "L2_current", "L3_current",
                            "Total_forward_active_energy", "Total_reverse_active_energy"]:
                parameter = commands[command]

                response = None
                while not response:
                    response = modbus_request(uart, slave_addr=1, register_addr=parameter[0],
                                              num_registers=parameter[1], function_code=3)
                    utime.sleep(0.1)
                data = int.from_bytes(response[3:7], 'big')
                float_value = struct.unpack('>f', struct.pack('>I', data))[0]
                timestamp = utime.time()
                if command == "Total_forward_active_energy":
                    modbus_frame[command][0] = int(float_value * 1000)
                    modbus_frame[command][1] = timestamp
                elif command == "Total_reverse_active_energy":
                    modbus_frame[command][0] = int(float_value * 1000)
                    modbus_frame[command][1] = timestamp
                else:
                    modbus_frame[command] = float_value
            state = 1


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
    time.sleep(5)
    try:
        wifi_connect()
        client = ArduinoCloudClient(device_id=DEVICE_ID, username=DEVICE_ID, password=CLOUD_PASSWORD)
        _thread.start_new_thread(read_modbus_frame, ())

        client.register("l1voltage", value=0.0, on_read=update_l1voltage, interval=30.0)
        client.register("l2voltage", value=0.0, on_read=update_l2voltage, interval=30.0)
        client.register("l3voltage", value=0.0, on_read=update_l3voltage, interval=30.0)

        client.register("l1current", value=0.0, on_read=update_l1current, interval=30.0)
        client.register("l2current", value=0.0, on_read=update_l2current, interval=30.0)
        client.register("l3current", value=0.0, on_read=update_l3current, interval=30.0)

        # client.register("l1power", value=0.0, on_read=update_l1power, interval=30.0)
        # client.register("l2power", value=0.0, on_read=update_l2power, interval=30.0)
        # client.register("l3power", value=0.0, on_read=update_l3power, interval=30.0)

        client.register("energy_forward_diff", value=0, on_read=update_energy_forward_diff, interval=120)

        client.register("energy_reverse_diff", value=0, on_read=update_energy_reverse_diff, interval=120)

        client.register("hard_reset", value=False, on_write=hard_reset)

        client.start()
    except Exception as e:
        print(e)
        time.sleep(30)
        machine.reset()


if __name__ == "__main__":
    main()

