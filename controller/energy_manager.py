import sys
import time

import logging
from arduino_iot_cloud import ArduinoCloudClient

from services import watchdog
from settings import config
from settings import secrets

sys.path.append("lib")


class EnergyManager:

    def __init__(self):
        self.init_states()
        self.init_devices()
        self.init_client()
        self.setup_client()

    def __str__(self):
        return self.__class__.__name__

    def init_states(self):
        logging.info(f"[{str(self)}] - init_states")
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

    def init_devices(self):
        logging.info(f"[{str(self)}] - init_devices")
        self.heaters = config.Heaters()
        self.validator = config.Validator()
        self.constants = config.Constants()
        self.secrets = secrets.Secrets()
        self.watchdog = watchdog.Watchdog()
        self.devices = watchdog.Devices()

    def init_client(self):
        logging.info(f"[{str(self)}] - init_client")
        self.client = ArduinoCloudClient(device_id=self.secrets.DEVICE_ID, username=self.secrets.DEVICE_ID,
                                         password=self.secrets.SECRET_KEY)

    def setup_client(self):
        logging.info(f"[{str(self)}] - setup_client")
        self.client.register("energy_forward_diff", value=None, on_write=self.read_energy_forward_diff)
        self.client.register("energy_reverse_diff", value=None, on_write=self.read_energy_reverse_diff)
        self.client.register("grid_meter_frame", value=None, on_write=self.read_grid_meter_frame)
        # self.client.register("hard_reset", value=False, on_read=self.hard_reset_grid_meter, interval=30)
        self.client.register("energy_balance", value=0, on_read=self.update_energy_balance, interval=5)
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
        logging.info(f"[GRIDMETER] parse_string_to_dict - INPUT  -> {input_string}")
        pairs = input_string.split(';')
        for pair in pairs:
            if pair:
                pair_dict = pair.split(":")
                if len(pair_dict) == 2:
                    key, value = pair_dict
                    if 'e' in value:  # when values is very small then cloud return them as exponential value
                        result[key] = 0.0
                        logging.info(f"[GRIDMETER] parse_string_to_dict - OUTPUT -> {key, value}")
                    else:
                        try:
                            value = float(value)
                            result[key] = value
                            logging.info(f"[GRIDMETER] parse_string_to_dict - OUTPUT -> {key, value}")
                        except Exception as e:
                            logging.error(f"parsing error {e}")
                            result[key] = 0.0
                else:
                    logging.warning(f"Invalid pair - [raw]:{pair}, [transformed]:{pair_dict}")

        # logging.info(f"[GRIDMETER] parse_string_to_dict -> ( output_dict) {result}")
        return result

    def update_wdg_controller_gridmeter(self, client):
        self.watchdog.wdg_int_ext = not self.watchdog.wdg_int_ext
        return self.watchdog.wdg_int_ext

    def check_wdg_gridmeter_controller(self, client, value):
        self.watchdog.wdg_ext_int = value
        self.watchdog.wdg_ext_int_timestamp = time.time()
        self.watchdog.wdg_ext_int_counter += 1
        self.devices.gridmeter_alive = True

    def read_energy_forward_diff(self, client, value):
        self.energy_forward_diff = value
        self.validator.energy_read = True
        logging.info(f"[GRIDMETER] Value of energy_forward_diff updated to: {self.energy_forward_diff:>6}")

    def read_energy_reverse_diff(self, client, value):
        self.energy_reverse_diff = value
        self.validator.energy_read = True
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
        if self.devices.gridmeter_alive:
            self.grid_meter_frame = self.parse_string_to_dict(value)
            logging.debug(self.grid_meter_frame)

    def hard_reset_grid_meter(self, client):
        if self.state_of_grid_meter == 0:
            self.state_of_grid_meter = 1
            return True
        else:
            return False

    def update_energy_balance(self, client):
        if self.validator.energy_read:
            if self.energy_reverse_diff >= 0 and self.energy_forward_diff >= 0:
                # self.energy_balance = int(self.energy_reverse_diff - self.energy_forward_diff)  # in case real heaters
                self.energy_balance = int((self.energy_reverse_diff - self.energy_forward_diff) - self.power_of_heaters)
                self.validator.energy_balance = True
                self.validator.energy_read = False
                return self.energy_balance
            else:
                return -1

    def update_power_of_heaters_total(self):
        total_power = 0
        heaters = {
            "2000": self.heaters.heater_2000W,
            "1000": self.heaters.heater_1000W,
            "500": self.heaters.heater_500W
        }
        for heater, state in heaters.items():
            if state:
                power = int(heater)
                total_power += power
        self.power_of_heaters = total_power
        self.validator.power_of_heaters = True

    def update_power_of_heaters(self, client):
        if self.validator.power_of_heaters:
            self.validator.power_of_heaters = False
            return self.power_of_heaters

    def adjust_heaters(self):  # TODO create unit tests
        """Heaters adjust used for proper turning on heaters and tweak to current production of energy"""
        energy_balance_local = self.energy_balance
        power_of_heaters_local = self.power_of_heaters

        logging.info(f"[ENERGY MANAGEMENT] Start of adjust_heaters with parameters: "
                     f"{energy_balance_local:>6} "
                     f"| HEATER_500W: {self.heaters.heater_500W} | "
                     f"HEATER_1000W: {self.heaters.heater_1000W} | "
                     f"HEATER_2000W: {self.heaters.heater_2000W} |")

        energy_balance_local, power_of_heaters_local = self.activate_heaters(
            energy_balance_local, power_of_heaters_local)

        energy_balance_local = self.deactivate_heaters(energy_balance_local)

        self.energy_balance = energy_balance_local
        logging.info(f"[ENERGY MANAGEMENT] End of adjust_heaters with parameters:   "
                     f"{energy_balance_local:>6} "
                     f"| HEATER_500W: {self.heaters.heater_500W} | "
                     f"HEATER_1000W: {self.heaters.heater_1000W} | "
                     f"HEATER_2000W: {self.heaters.heater_2000W} |")

        self.validate_energy_balance()

        self.update_power_of_heaters_total()

        return 0

    def activate_heaters(self, energy_balance_local, power_of_heaters_local):
        """Heater activation logic."""
        if energy_balance_local >= 500 and self.validator.energy_balance:
            if ((energy_balance_local + power_of_heaters_local) / 2000) >= 1 and not self.heaters.heater_2000W:
                energy_balance_local -= self.constants.HEATER_2000W_POWER
                power_of_heaters_local += self.constants.HEATER_2000W_POWER
                self.heaters.heater_2000W = True
            if (((energy_balance_local + power_of_heaters_local) / self.constants.HEATER_1000W_POWER) >= 1 and not
                    self.heaters.heater_1000W):
                energy_balance_local -= self.constants.HEATER_1000W_POWER
                power_of_heaters_local += self.constants.HEATER_1000W_POWER
                self.heaters.heater_1000W = True
            if (((energy_balance_local + power_of_heaters_local) / self.constants.HEATER_500W_POWER) >= 1 and not
                    self.heaters.heater_500W):
                energy_balance_local -= self.constants.HEATER_500W_POWER
                power_of_heaters_local += self.constants.HEATER_500W_POWER
                self.heaters.heater_500W = True
        return energy_balance_local, power_of_heaters_local

    def deactivate_heaters(self, energy_balance_local):
        """Heater deactivation logic in loop to avoid recursion."""
        while energy_balance_local < 0 and self.validator.energy_balance:
            # HEATER 2000W
            if self.heaters.heater_2000W:
                if (energy_balance_local / -self.constants.HEATER_2000W_POWER) > 0.75:
                    energy_balance_local += self.constants.HEATER_2000W_POWER
                    self.heaters.heater_2000W = False
                    continue
                elif 0.25 < (energy_balance_local / -self.constants.HEATER_2000W_POWER) <= 0.75 \
                        and not self.heaters.heater_1000W:
                    energy_balance_local += self.constants.HEATER_2000W_POWER
                    self.heaters.heater_2000W = False
                    continue
                elif 0 < (energy_balance_local / -self.constants.HEATER_2000W_POWER) <= 0.25 \
                        and not self.heaters.heater_500W:
                    energy_balance_local += self.constants.HEATER_2000W_POWER
                    self.heaters.heater_2000W = False
                    continue
            # HEATER 1000W
            if self.heaters.heater_1000W:
                if (energy_balance_local / -self.constants.HEATER_1000W_POWER) > 0.5:
                    energy_balance_local += self.constants.HEATER_1000W_POWER
                    self.heaters.heater_1000W = False
                    continue
                elif 0 < (energy_balance_local / -self.constants.HEATER_1000W_POWER) <= 0.5 \
                        and not self.heaters.heater_500W:
                    energy_balance_local += self.constants.HEATER_1000W_POWER
                    self.heaters.heater_1000W = False
                    continue
            # HEATER 500W
            if self.heaters.heater_500W:
                if (energy_balance_local / -self.constants.HEATER_500W_POWER) > 0:
                    energy_balance_local += self.constants.HEATER_500W_POWER
                    self.heaters.heater_500W = False
                    continue
            break

        return energy_balance_local

    def validate_energy_balance(self):
        """Checks if energy is balanced and sets validation flag."""
        heaters = [self.heaters.heater_2000W, self.heaters.heater_1000W, self.heaters.heater_500W]
        if self.validator.energy_balance:
            if 0 <= self.energy_balance < self.constants.HEATER_500W_POWER:
                self.validator.energy_balance = False
            elif self.energy_balance >= self.constants.HEATER_500W_POWER and all(heaters):
                self.validator.energy_balance = False
            elif self.energy_balance < 0 and not any(heaters):
                self.validator.energy_balance = False

    def run_energy_management(self):
        while True:
            if self.devices.gridmeter_alive:
                logging.info(f"[ENERGY MANAGEMENT] GRIDMETER IS ALIVE")
                if self.validator.energy_balance:
                    logging.info(f"[ENERGY MANAGEMENT] ENERGY BALANCE VALUE IS VALID")
                    self.adjust_heaters()
                else:
                    logging.info(f"[ENERGY MANAGEMENT] ENERGY BALANCE VALUE IS NOT VALID")
            else:
                logging.info(f"[ENERGY MANAGEMENT] GRIDMETER IS DEAD")
            time.sleep(30)
