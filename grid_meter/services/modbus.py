import time
import logging
import utime
import struct
import gc

from machine import UART, Pin


class Modbus:
    def __init__(self):
        self.uart = UART(0, buadrate=9600, bits=8, parity=0, stop=1, tx=Pin(0), rx=Pin(1))
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

    def modbus_read(self, uart, slave_addr=0, register_addr=0x0, num_registers=0x01, function_code=0x03, timeout=5):
        """
        | Address device | Function code | Data      | CRC-16  |
        |----------------|---------------|-----------|---------|
        | 1 byte         | 1 byte        | n-bytes   | 2 bytes |
        :param uart:
        :param slave_addr:
        :param register_addr:
        :param num_registers:
        :param function_code:
        :param timeout:
        :return:
        """
        request = bytearray([slave_addr, function_code,
                             (register_addr >> 8) & 0xFF,
                             register_addr & 0xFF,
                             (num_registers >> 8) & 0xFF,
                             num_registers & 0xFF])
        crc = self.calculate_crc(request)
        request.extend(crc)

        start_time = time.time()
        response = bytes()

        while time.time() - start_time < timeout:
            uart.write(request)
            time.sleep(0.1)
            if uart.any():
                response = uart.read()
                if response and self.validate_crc(response):  # TODO validation of CRC from reading data
                    return response
        raise TimeoutError("No valid response from Modbus slave within timeout")

    def run_modbus_client(self) -> None:
        """

        :return:
        """
        state = 0
        while True:
            if state == 1:
                time.sleep(25)
                logging.info("STANDARD CYCLE - read_modbus_frame()")
            elif state == 0:
                logging.info("FIRST_CYCLE_START - read_modbus_frame()")
                state = 1
            self.check_memory()  # TODO implement
            for command, parameter in self.commands.items():
                response = None
                while not response:
                    response = self.modbus_read(uart,
                                                slave_addr=1,
                                                register_addr=parameter[0],
                                                num_registers=parameter[1],
                                                function_code=3)
                    utime.sleep(0.1)

                value = self.convert_modbus_data(response)
                timestamp = utime.time()
                if command == "Total_forward_active_energy":
                    self.modbus_frame[command][0] = int(value * 1000)
                    self.modbus_frame[command][1] = timestamp
                elif command == "Total_reverse_active_energy":
                    self.modbus_frame[command][0] = int(value * 1000)
                    self.modbus_frame[command][1] = timestamp
                else:
                    self.modbus_frame[command] = round(value, 2)
            self.update_frame()

    @staticmethod
    def convert_modbus_data(response):
        """
        :param response:
        :return:
        """
        data = int.from_bytes(response[3:7], 'big')
        float_value = struct.unpack('>f', struct.pack('>I', data))[0]
        return float_value

    def update_frame(self) -> None:
        """
        Parse values from modbus to one string - RAM limitation in Pico
        :return:
        """
        grid_meter_frame_local = ""
        commands = list(self.commands.keys())

        for command in commands:
            value_str = str(self.modbus_frame[command])
            grid_meter_frame_local = grid_meter_frame_local + command + ":" + value_str + ";"

        self.grid_meter_frame = grid_meter_frame_local
        logging.info(f"Grid Meter Frame: updated - update_frame()")

    def validate_crc(self, response: bytes) -> bool:
        """
        Check the CRC-16 for received messages
        :param response:
        :return:
        """
        if len(response) < 3:
            return False

        data_without_crc = response[:-2]
        received_crc = response[-2:]

        calculated_crc = self.calculate_crc(data_without_crc)

        return received_crc == calculated_crc

    @staticmethod
    def calculate_crc(request_to_crc: bytes) -> bytes:
        """
        Calculate CRC-16 for given frame
        :param request_to_crc:
        :return:
        """
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

    @staticmethod
    def check_memory() -> None:
        """
        Call gc.collect() for startup garbage collection - problems with RAM usage in Rpi Pico
        :return:
        """
        free_memory_before = gc.mem_free()
        allocated_memory_before = gc.mem_alloc()

        gc.collect()

        free_memory_after = gc.mem_free()
        allocated_memory_after = gc.mem_alloc()

        logging.info(f"FREE MEMORY:      {free_memory_before:>7} | {free_memory_after:>7}")
        logging.info(f"ALLOCATED MEMORY: {allocated_memory_before:>7} | {allocated_memory_after:>7}")
