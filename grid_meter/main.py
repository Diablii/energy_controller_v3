from machine import UART, Pin
import utime
import struct
import _thread
import network
import time
import logging
import gc

from arduino_iot_cloud import ArduinoCloudClient
from secrets import WIFI_SSID, WIFI_PASSWORD, DEVICE_ID, CLOUD_PASSWORD

commands = {
    "L1_voltage": [14, 1],
    "L2_voltage": [16, 1],
    "L3_voltage": [18, 1],
    "L1_current": [22, 1],
    "L2_current": [24, 1],
    "L3_current": [26, 1],
    "L1_active_power": [30, 1],
    "L2_active_power": [32, 1],
    "L3_active_power": [34, 1],
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
    "L1_active_power": 0,
    "L2_active_power": 0,
    "L3_active_power": 0,
    "Total_forward_active_energy": [0, 0],
    "Total_reverse_active_energy": [0, 0],
}

modbus_frame_old = {
    "Total_forward_active_energy": [0, 0],
    "Total_reverse_active_energy": [0, 0],
}

watchdog = {
    "wdg_gridmeter_controller": False,
    "wdg_controller_gridmeter": False,
    "wdg_controller_gridmeter_counter": 0,
    "wdg_controller_gridmeter_counter_old": 0,
    "wdg_controller_gridmeter_failed_counter": 0
}

devices = {
    "controller_alive": True,
    "actuatorheaters_alive": True
}

diff_reverse_active_energy = 0
diff_forward_active_energy = 0

grid_meter_frame = ""


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
    response = bytes()
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
        time.sleep_ms(1000)
    logging.info(f"WiFi Connected {wlan.ifconfig()}")


def update_frame():
    global modbus_frame
    global grid_meter_frame
    grid_meter_frame_local = ""
    for command in ["L1_voltage", "L2_voltage", "L3_voltage",
                    "L1_current", "L2_current", "L3_current",
                    "L1_active_power", "L2_active_power", "L3_active_power"]:
        value_str = str(modbus_frame[command])
        grid_meter_frame_local = grid_meter_frame_local + command + ":" + value_str + ";"
    grid_meter_frame = grid_meter_frame_local
    logging.info(f"Grid Meter Frame: updated - update_frame()")
    return 0


def update_frame_cloud(client):
    global grid_meter_frame
    return grid_meter_frame


def update_total_energy_reverse(client):
    global modbus_frame
    return modbus_frame["Total_reverse_active_energy"][0]


def update_energy_reverse_diff(client):
    global modbus_frame
    global modbus_frame_old
    global diff_reverse_active_energy
    command = "Total_reverse_active_energy"
    logging.info(f"update_energy_reverse_diff")
    logging.info(f"modbus_frame    : {modbus_frame[command]}")
    logging.info(f"modbus_frame_old: {modbus_frame_old[command]}")
    old_time = modbus_frame_old[command][1]
    new_time = modbus_frame[command][1]
    old_value = int(modbus_frame_old[command][0])
    new_value = int(modbus_frame[command][0])
    diff_time = new_time - old_time
    if diff_time > 0:
        diff_time_norm = int(3600 / diff_time)
        diff_reverse_active_energy = (new_value - old_value) * diff_time_norm
        modbus_frame_old[command] = modbus_frame[command].copy()
        logging.info(
            f"diff_reverse_energy: {diff_reverse_active_energy:>5} | {old_value:>10} | {new_value:>10} | {diff_time:>5}")
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
    logging.info(f"update_energy_forward_diff")
    logging.info(f"modbus_frame    : {modbus_frame[command]}")
    logging.info(f"modbus_frame_old: {modbus_frame_old[command]}")
    old_time = modbus_frame_old[command][1]
    new_time = modbus_frame[command][1]
    old_value = int(modbus_frame_old[command][0])
    new_value = int(modbus_frame[command][0])
    diff_time = new_time - old_time
    if diff_time > 0:
        diff_time_norm = int(3600 / diff_time)
        diff_forward_active_energy = (new_value - old_value) * diff_time_norm
        modbus_frame_old[command] = modbus_frame[command].copy()
        logging.info(
            f"diff_forward_energy: {diff_forward_active_energy:>5} | {old_value:>10} | {new_value:>10} | {diff_time:>5}")
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
    global grid_meter_frame
    while True:
        if state == 1:
            time.sleep(25)
            logging.info("STANDARD CYCLE - read_modbus_frame()")
            check_memory()
            for command in ["L1_voltage", "L2_voltage", "L3_voltage",
                            "L1_current", "L2_current", "L3_current",
                            "L1_active_power", "L2_active_power", "L3_active_power",
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
                    modbus_frame[command] = round(float_value, 2)
            update_frame()
        elif state == 0:
            logging.info("FIRST_CYCLE_START - read_modbus_frame()")
            check_memory()
            for command in ["L1_voltage", "L2_voltage", "L3_voltage",
                            "L1_current", "L2_current", "L3_current",
                            "L1_active_power", "L2_active_power", "L3_active_power",
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
                    modbus_frame[command] = round(float_value, 2)
            state = 1
            update_frame()
        utime.sleep(1)
        run_watchdog()


def check_memory():
    gc.collect()
    free_memory = gc.mem_free()
    logging.info(f"FREE MEMORY:      {free_memory:>7}")
    allocated_memory = gc.mem_alloc()
    logging.info(f"ALLOCATED MEMORY: {allocated_memory:>7}")
    total_memory = free_memory + allocated_memory
    logging.info(f"TOTAL MEMORY:     {total_memory:>7}")


def update_wdg_gridmeter_controller(client):
    global watchdog
    watchdog['wdg_gridmeter_controller'] = not watchdog['wdg_gridmeter_controller']
    return watchdog['wdg_gridmeter_controller']


def check_wdg_controller_gridmeter(client, value):
    global watchdog
    watchdog['wdg_controller_gridmeter'] = value
    watchdog['wdg_controller_gridmeter_counter'] += 1


def run_watchdog():
    global watchdog
    global devices
    if watchdog['wdg_controller_gridmeter_counter'] != watchdog['wdg_controller_gridmeter_counter_old']:
        watchdog['wdg_controller_gridmeter_counter_old'] = watchdog['wdg_controller_gridmeter_counter']
        devices['controller_alive'] = True
        logging.info(f"[WATCHDOG] CONTROLLER ALIVE: {devices['controller_alive']}")
    else:
        devices["controller_alive"] = False
        logging.info(f"[WATCHDOG] CONTROLLER ALIVE: {devices['controller_alive']}")
        watchdog['wdg_controller_gridmeter_failed_counter'] += 1
    if watchdog['wdg_controller_gridmeter_counter'] > 150:
        watchdog['wdg_controller_gridmeter_counter'] = 0
        watchdog['wdg_controller_gridmeter_failed_counter'] = 0
        logging.info(f"[WATCHDOG] CONTROLLER COUNTER RESET")
    if watchdog['wdg_controller_gridmeter_failed_counter'] > 5:
        for i in range(5):
            logging.info(f"[WATCHDOG] TRIGGER RESET, RESET IN {5 - i}")
            time.sleep(1)
        machine.reset()


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
    time.sleep(5)
    try:
        wifi_connect()
        client = ArduinoCloudClient(device_id=DEVICE_ID, username=DEVICE_ID, password=CLOUD_PASSWORD, sync_mode=False)
        _thread.start_new_thread(read_modbus_frame, ())

        client.register("grid_meter_frame", value="", on_read=update_frame_cloud, interval=30.0)
        client.register("energy_forward_diff", value=0, on_read=update_energy_forward_diff, interval=120)
        client.register("energy_reverse_diff", value=0, on_read=update_energy_reverse_diff, interval=120)

        client.register("wdg_gridmeter_controller", value=False, on_read=update_wdg_gridmeter_controller, interval=1)
        client.register("wdg_controller_gridmeter", value=False, on_write=check_wdg_controller_gridmeter)

        client.start()

    except Exception as e:
        logging.error(e)
        time.sleep(30)
        machine.reset()


if __name__ == "__main__":
    main()
