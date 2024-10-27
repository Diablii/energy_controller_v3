import sys

import logging
import time

from threading import Thread
from arduino_iot_cloud import ArduinoCloudClient

sys.path.append("lib")


# noinspection PyUnusedLocal
class EnergyManager:
    DEVICE_ID = b"242186a1-15ce-4157-bfb3-81545e4ac2d5"
    SECRET_KEY = b"anJxtmZnXeNRrlakm1yMd?gUL"

    def __init__(self):
        self.state_of_grid_meter = 0
        self.energy_forward_diff = 0
        self.energy_reverse_diff = 0
        self.grid_meter_frame = {
            "L1_voltage": 0.0,
            "L1_current": 0.0,
            "L1_active_power": 0.0,
            "L2_voltage": 0.0,
            "L2_current": 0.0,
            "L2_active_power": 0.0,
            "L3_voltage": 0.0,
            "L3_current": 0.0,
            "L3_active_power": 0.0
        }
        self.energy_balance = 0
        self.power_of_heaters = 0
        self.heaters = {
            "heater_2000W": False,
            "heater_1000W": False,
            "heater_500W": False
        }
        self.value_validation = {
            "energy_read_valid": False,
            "energy_balance_valid": False,
            "power_of_heaters_valid": False,
            "grid_meter_frame_valid": False
        }
        self.watchdog = {
            "wdg_controller_gridmeter": False,
            "wdg_gridmeter_controller": False,
            "wdg_gridmeter_controller_counter": 0,
            "wdg_gridmeter_controller_counter_old": 0,
            "wdg_gridmeter_controller_failed_counter": 0
        }
        self.devices = {
            "gridmeter_alive": True,
            "actuatorheaters_alive": True
        }

        self.client = ArduinoCloudClient(device_id=self.DEVICE_ID, username=self.DEVICE_ID, password=self.SECRET_KEY)
        self.setup_client()

    def setup_client(self):
        self.client.register("energy_forward_diff", value=None, on_write=self.read_energy_forward_diff)
        self.client.register("energy_reverse_diff", value=None, on_write=self.read_energy_reverse_diff)
        self.client.register("grid_meter_frame", value=None, on_write=self.read_grid_meter_frame)
        # self.client.register("hard_reset", value=False, on_read=self.hard_reset_grid_meter, interval=30)
        self.client.register("energy_balance", value=0, on_read=self.write_energy_balance, interval=5)
        self.client.register("power_of_heaters", value=0, on_read=self.update_power_of_heaters, interval=5)

        self.client.register("l1_voltage", value=0.0, on_read=self.update_l1_voltage, interval=20)
        self.client.register("l1_current", value=0.0, on_read=self.update_l1_current, interval=20)
        self.client.register("l1_active_power", value=0.0, on_read=self.update_l1_power, interval=20)

        self.client.register("l2_voltage", value=0.0, on_read=self.update_l2_voltage, interval=20)
        self.client.register("l2_current", value=0.0, on_read=self.update_l2_current, interval=20)
        self.client.register("l2_active_power", value=0.0, on_read=self.update_l2_power, interval=20)

        self.client.register("l3_voltage", value=0.0, on_read=self.update_l3_voltage, interval=20)
        self.client.register("l3_current", value=0.0, on_read=self.update_l3_current, interval=20)
        self.client.register("l3_active_power", value=0.0, on_read=self.update_l3_power, interval=20)

        self.client.register("wdg_controller_gridmeter", value=False,
                             on_read=self.update_wdg_controller_gridmeter, interval=1)
        self.client.register("wdg_gridmeter_controller", value=False,
                             on_write=self.check_wdg_gridmeter_controller)

    @staticmethod
    def parse_string_to_dict(input_string):  # create unit tests
        result = {}
        logging.info(f"[GRIDMETER] parse_string_to_dict -> (input_string) {input_string}")
        pairs = input_string.split(';')
        for pair in pairs:
            if pair:
                key, value = pair.split(':')
                if 'e' in value:
                    result[key] = 0.0
                else:
                    try:
                        value = float(value)
                    except Exception as e:
                        logging.error(f"parsing error {e}")
                    result[key] = value
        logging.info(f"[GRIDMETER] parse_string_to_dict -> ( output_dict) {result}")
        return result

    def update_wdg_controller_gridmeter(self, client):
        self.watchdog['wdg_controller_gridmeter'] = not self.watchdog['wdg_controller_gridmeter']
        return self.watchdog['wdg_controller_gridmeter']

    def check_wdg_gridmeter_controller(self, client, value):
        self.watchdog['wdg_gridmeter_controller'] = value
        self.watchdog['wdg_gridmeter_controller_counter'] += 1

    def read_energy_forward_diff(self, client, value):
        self.energy_forward_diff = value
        self.value_validation['energy_read_valid'] = True
        logging.info(f"[GRIDMETER] Value of energy_forward_diff updated to: {self.energy_forward_diff:>6}")

    def read_energy_reverse_diff(self, client, value):
        self.energy_reverse_diff = value
        self.value_validation['energy_read_valid'] = True
        logging.info(f"[GRIDMETER] Value of energy_reverse_diff updated to: {self.energy_reverse_diff:>6}")

    def update_l1_voltage(self, client):
        return self.grid_meter_frame['L1_voltage']

    def update_l1_current(self, client):
        return self.grid_meter_frame['L1_current']

    def update_l1_power(self, client):
        return self.grid_meter_frame['L1_active_power']

    def update_l2_voltage(self, client):
        return self.grid_meter_frame['L2_voltage']

    def update_l2_current(self, client):
        return self.grid_meter_frame['L2_current']

    def update_l2_power(self, client):
        return self.grid_meter_frame['L2_active_power']

    def update_l3_voltage(self, client):
        return self.grid_meter_frame['L3_voltage']

    def update_l3_current(self, client):
        return self.grid_meter_frame['L3_current']

    def update_l3_power(self, client):
        return self.grid_meter_frame['L3_active_power']

    def read_grid_meter_frame(self, client, value):
        if self.devices['gridmeter_alive']:
            self.grid_meter_frame = self.parse_string_to_dict(value)
            # self.grid_meter_frame = value
            # self.value_validation['grid_meter_frame_valid'] = True
            logging.debug(self.grid_meter_frame)

    def hard_reset_grid_meter(self, client):
        if self.state_of_grid_meter == 0:
            self.state_of_grid_meter = 1
            return True
        else:
            return False

    def write_energy_balance(self, client):
        if self.value_validation['energy_read_valid']:
            if self.energy_reverse_diff >= 0 and self.energy_forward_diff >= 0:
                self.energy_balance = int((self.energy_reverse_diff - self.energy_forward_diff) - self.power_of_heaters)
                # self.adjust_heaters()
                # self.update_power_of_heaters_total()
                self.value_validation['energy_balance_valid'] = True
                self.value_validation['energy_read_valid'] = False
                return self.energy_balance
            else:
                return -1

    def update_power_of_heaters_total(self):
        total_power = 0
        heaters = self.heaters.copy()
        for heater, state in heaters.items():
            if state:
                power = int(heater.split('_')[1][:-1])
                total_power += power
        self.power_of_heaters = total_power
        self.value_validation['power_of_heaters_valid'] = True

    def update_power_of_heaters(self, client):
        # logging.info(f"update_power_of_heaters {self.power_of_heaters}")
        if self.value_validation['power_of_heaters_valid']:
            self.value_validation['power_of_heaters_valid'] = False
            return self.power_of_heaters

    def adjust_heaters(self):  # create unit tests
        energy_balance_local = self.energy_balance
        power_of_heaters_local = self.power_of_heaters
        logging.info(f"[ENERGY MANAGEMENT] Start of adjust_heaters with parameters: "
                     f"{energy_balance_local:>6} {self.heaters}")
        if energy_balance_local >= 500 and self.value_validation['energy_balance_valid']:
            if ((energy_balance_local + power_of_heaters_local) / 2000) >= 1 and not self.heaters["heater_2000W"]:
                energy_balance_local -= 2000
                power_of_heaters_local += 2000
                self.heaters["heater_2000W"] = True
            if ((energy_balance_local + power_of_heaters_local) / 1000) >= 1 and not self.heaters["heater_1000W"]:
                energy_balance_local -= 1000
                power_of_heaters_local += 1000
                self.heaters["heater_1000W"] = True
            if ((energy_balance_local + power_of_heaters_local) / 500) >= 1 and not self.heaters["heater_500W"]:
                energy_balance_local -= 500
                power_of_heaters_local += 500
                self.heaters["heater_500W"] = True

        if energy_balance_local < 0 and self.value_validation['energy_balance_valid']:

            while energy_balance_local < 0:

                if self.heaters["heater_2000W"] and (energy_balance_local / -2000) > 0.75:
                    energy_balance_local += 2000
                    self.heaters["heater_2000W"] = False
                elif self.heaters["heater_2000W"] and 0.25 < (energy_balance_local / -2000) <= 0.75\
                        and not self.heaters['heater_1000W']:
                    energy_balance_local += 2000
                    self.heaters["heater_2000W"] = False
                elif self.heaters["heater_2000W"] and 0 < (energy_balance_local / -2000) <= 0.25\
                        and not self.heaters['heater_500W']:
                    energy_balance_local += 2000
                    self.heaters["heater_2000W"] = False

                elif self.heaters["heater_1000W"] and (energy_balance_local / -1000) > 0.5:
                    energy_balance_local += 1000
                    self.heaters["heater_1000W"] = False
                elif self.heaters["heater_1000W"] and 0 < (energy_balance_local / -1000) <= 0.5 \
                        and not self.heaters["heater_500W"]:
                    energy_balance_local += 1000
                    self.heaters["heater_1000W"] = False

                elif self.heaters["heater_500W"] and (energy_balance_local / -500) > 0:
                    energy_balance_local += 500
                    self.heaters["heater_500W"] = False
                else:
                    break

        self.energy_balance = energy_balance_local
        logging.info(f"[ENERGY MANAGEMENT] End of adjust_heaters with parameters:   "
                     f"{energy_balance_local:>6} {self.heaters}")

        if self.value_validation['energy_balance_valid']:
            if 0 <= self.energy_balance < 500:
                self.value_validation['energy_balance_valid'] = False
            elif self.energy_balance >= 500 and all(value is True for value in self.heaters.values()):
                self.value_validation['energy_balance_valid'] = False
            elif self.energy_balance < 0 and all(value is False for value in self.heaters.values()):
                self.value_validation['energy_balance_valid'] = False
            else:
                try:
                    self.adjust_heaters()
                except Exception as e:
                    logging.warning(f"recursion fault{e}")
        self.update_power_of_heaters_total()
        return 0

    def run_energy_management(self):
        while True:
            if self.devices['gridmeter_alive']:
                logging.info(f"[ENERGY MANAGEMENT] GRIDMETER IS ALIVE")
                if self.value_validation['energy_balance_valid']:
                    logging.info(f"[ENERGY MANAGEMENT] ENERGY BALANCE VALUE IS VALID")
                    self.adjust_heaters()
                else:
                    logging.info(f"[ENERGY MANAGEMENT] ENERGY BALANCE VALUE IS NOT VALID")
            else:
                logging.info(f"[ENERGY MANAGEMENT] GRIDMETER IS DEAD")
            time.sleep(30)


    def run_watchdog(self):
        while True:
            time.sleep(10)
            if self.watchdog['wdg_gridmeter_controller_counter'] \
                    != self.watchdog['wdg_gridmeter_controller_counter_old']:
                self.watchdog['wdg_gridmeter_controller_counter_old'] \
                    = self.watchdog['wdg_gridmeter_controller_counter']
                self.devices['gridmeter_alive'] = True
                logging.info(f"[WATCHDOG] GRIDMETER ALIVE: {self.devices['gridmeter_alive']}")
            else:
                self.devices['gridmeter_alive'] = False
                logging.info(f"[WATCHDOG] GRIDMETER ALIVE: {self.devices['gridmeter_alive']}")
                self.watchdog['wdg_gridmeter_controller_failed_counter'] += 1
            if self.watchdog['wdg_gridmeter_controller_counter'] > 150:
                self.watchdog['wdg_gridmeter_controller_counter'] = 0
                self.watchdog['wdg_gridmeter_controller_failed_counter'] = 0
                logging.info(f"[WATCHDOG] GRIDMETER COUNTER RESET")
            if self.watchdog['wdg_gridmeter_controller_failed_counter'] > 5:
                for i in range(5):
                    logging.info(f"[WATCHDOG] TRIGGER RESET, RESET IN {5 - i}")
                    time.sleep(1)
                sys.exit(1)

    def start(self):
        # add thread for adjust_heaters
        adjust_heaters_thread = Thread(target=self.run_energy_management)
        adjust_heaters_thread.start()
        watchdog_gridmeter_thread = Thread(target=self.run_watchdog)
        watchdog_gridmeter_thread.start()

        self.client.start()


def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    energy_manager = EnergyManager()
    energy_manager.start()


if __name__ == "__main__":
    main()
