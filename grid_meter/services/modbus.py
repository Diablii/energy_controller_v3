import time
import logging
import utime
import struct

from machine import UART, Pin


class Modbus:
    def __init__(self):
        self.commands = {
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
            "Total_reverse_active_energy": [272, 2]
        }
        self.modbus_frame = {
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
            "Total_reverse_active_energy": [0, 0]
        }
        self.modbus_frame_old = {
            "Total_forward_active_energy": [0, 0],
            "Total_reverse_active_energy": [0, 0]
        }
        self.grid_meter_frame = ""

    def modbus_read(self, uart, slave_addr=0, register_addr=0x0, num_registers=0x01, function_code=0x03):
        request = bytearray([slave_addr, function_code,
                             (register_addr >> 8) & 0xFF,
                             register_addr & 0xFF,
                             (num_registers >> 8) & 0xFF,
                             num_registers & 0xFF])
        crc = self.calculate_crc(request)
        request.extend(crc)
        isResponse = False
        response = bytes()
        while not isResponse:
            uart.write(request)
            time.sleep(0.5)
            if uart.any():
                response = uart.read()
                if response:
                    isResponse = True
        return response

    @staticmethod
    def calculate_crc(self, request_to_crc: bytes) -> bytes:
        crc = 0xFFFF
        for i in request_to_crc:
            crc ^= i
            for _ in range(8):
                if crc & 1:
                    crc >>= 1
                    crc ^= 0xA001
                else:
                    crc >>= 1
        return crc.to_bytes(2, "little")

    def modbus_read_frame(self):
        uart = UART(0, buadrate=9600, bits=8, parity=0, stop=1, tx=Pin(0), rx=Pin(1))
        state = 0

        while True:
            if state == 1:
                time.sleep(25)
                logging.info("STANDARD CYCLE - read_modbus_frame()")
            elif state == 0:
                logging.info("FIRST_CYCLE_START - read_modbus_frame()")
                state = 1
            # self.check_memory()  # TODO implement
            for command, parameter in self.commands.items():
                response = None
                while not response:
                    response = self.modbus_read(uart, slave_addr=1, register_addr=parameter[0],
                                                num_registers=parameter[1], function_code=3)
                    utime.sleep(0.1)
                data = int.from_bytes(response[3:7], 'big')
                float_value = struct.unpack('>f', struct.pack('>I', data))[0]
                timestamp = utime.time()
                if command == "Total_forward_active_energy":
                    self.modbus_frame[command][0] = int(float_value * 1000)
                    self.modbus_frame[command][1] = timestamp
                elif command == "Total_reverse_active_energy":
                    self.modbus_frame[command][0] = int(float_value * 1000)
                    self.modbus_frame[command][1] = timestamp
                else:
                    self.modbus_frame[command] = round(float_value, 2)
            self.update_frame()


    def update_frame(self):
        pass
