import logging
import sys

from arduino_iot_cloud import ArduinoCloudClient

from dotenv import load_dotenv
import os

sys.path.append("lib")


class EnergyManager:
    load_dotenv()

    device_id = os.getenv('DEVICE_ID')
    secret_key = os.getenv('SECRET_KEY')

    DEVICE_ID = device_id.encode('utf-8')
    SECRET_KEY = secret_key.encode('utf-8')

    def __init__(self):
        self.state_of_grid_meter = 0
        self.energy_forward_diff = 0
        self.energy_reverse_diff = 0
        self.grid_meter_frame = {
            "L1_voltage": 0,
            "L1_current": 0,
            "L1_active_power": 0,
            "L2_voltage": 0,
            "L2_current": 0,
            "L2_active_power": 0,
            "L3_voltage": 0,
            "L3_current": 0,
            "L3_active_power": 0
        }
        self.energy_balance = 0
        self.power_of_heaters = 0
        self.heaters = {
            "heater_2000W": False,
            "heater_1000W": False,
            "heater_500W": False
        }
        self.value_validation = {
            "energy_balance_valid": False,
            "power_of_heaters_valid": False
        }

        self.client = ArduinoCloudClient(device_id=self.DEVICE_ID, username=self.DEVICE_ID, password=self.SECRET_KEY)
        self.setup_client()

    def setup_client(self):
        self.client.register("energy_forward_diff", value=None, on_write=self.read_energy_forward_diff)
        self.client.register("energy_reverse_diff", value=None, on_write=self.read_energy_reverse_diff)
        self.client.register("grid_meter_frame", value=None, on_write=self.read_grid_meter_frame)
        # self.client.register("hard_reset", value=False, on_read=self.hard_reset_grid_meter, interval=30)
        self.client.register("energy_balance", value=0, on_read=self.write_energy_balance, interval=1)
        self.client.register("power_of_heaters", value=0, on_read=self.update_power_of_heaters, interval=1)

        self.client.register("l1_voltage", value=0.0, on_read=self.update_l1_voltage, interval=20)
        self.client.register("l1_current", value=0.0, on_read=self.update_l1_current, interval=20)
        self.client.register("l1_active_power", value=0.0, on_read=self.update_l1_power, interval=20)

        self.client.register("l2_voltage", value=0.0, on_read=self.update_l2_voltage, interval=20)
        self.client.register("l2_current", value=0.0, on_read=self.update_l2_current, interval=20)
        self.client.register("l2_active_power", value=0.0, on_read=self.update_l2_power, interval=20)

        self.client.register("l3_voltage", value=0.0, on_read=self.update_l3_voltage, interval=20)
        self.client.register("l3_current", value=0.0, on_read=self.update_l3_current, interval=20)
        self.client.register("l3_active_power", value=0.0, on_read=self.update_l3_power, interval=20)

    @staticmethod
    def parse_string_to_dict(input_string):  # create unit tests
        result = {}

        pairs = input_string.split(';')
        for pair in pairs:
            if pair:
                key, value = pair.split(':')
                if '1e-' in value:
                    result[key] = 0.0
                else:
                    try:
                        value = float(value)
                    except ValueError:
                        pass
                    result[key] = value
        return result

    def read_energy_forward_diff(self, client, value):
        self.energy_forward_diff = value
        self.value_validation['energy_balance_valid'] = True
        logging.info(f"Value of energy_forward_diff updated to: {self.energy_forward_diff:>6}")

    def read_energy_reverse_diff(self, client, value):
        self.energy_reverse_diff = value
        self.value_validation['energy_balance_valid'] = True
        logging.info(f"Value of energy_reverse_diff updated to: {self.energy_reverse_diff:>6}")

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
        self.grid_meter_frame = self.parse_string_to_dict(value)
        logging.debug(self.grid_meter_frame)

    def hard_reset_grid_meter(self, client):
        if self.state_of_grid_meter == 0:
            self.state_of_grid_meter = 1
            return True
        else:
            return False

    def write_energy_balance(self, client):
        if self.value_validation['energy_balance_valid']:
            if self.energy_reverse_diff >= 0 and self.energy_forward_diff >= 0:
                self.energy_balance = int((self.energy_reverse_diff - self.energy_forward_diff) - self.power_of_heaters)
                self.adjust_heaters(self.energy_balance)
                self.update_power_of_heaters_total()
                return self.energy_balance
            else:
                return -1

    def update_power_of_heaters_total(self):
        total_power = 0
        for heater, state in self.heaters.items():
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

    def adjust_heaters(self, calculated_energy_balance):  # create unit tests
        energy_balance_local = calculated_energy_balance
        power_of_heaters_local = self.power_of_heaters
        logging.info(f"Start of adjust_heaters with parameters: {energy_balance_local:>6} {self.heaters}")
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
        logging.info(f"End of adjust_heaters with parameters:   {energy_balance_local:>6} {self.heaters}")

        if self.value_validation['energy_balance_valid']:
            if 0 <= self.energy_balance < 500:
                self.value_validation['energy_balance_valid'] = False
            elif self.energy_balance >= 500 and all(value is True for value in self.heaters.values()):
                self.value_validation['energy_balance_valid'] = False
            elif self.energy_balance < 0 and all(value is False for value in self.heaters.values()):
                self.value_validation['energy_balance_valid'] = False
            else:
                self.adjust_heaters(self.energy_balance)
        return 0

    def start(self):
        self.client.start()


def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    energy_manager = EnergyManager()
    energy_manager.start()


if __name__ == "__main__":
    main()
