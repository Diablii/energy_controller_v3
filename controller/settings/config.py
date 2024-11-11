class Heaters:
    def __init__(self):
        self.heater_2000W = False
        self.heater_1000W = False
        self.heater_500W = False

    def reset_heaters(self):
        self.heater_2000W = False
        self.heater_1000W = False
        self.heater_500W = False


class Validator:
    def __init__(self):
        self.energy_read = False,
        self.energy_balance = False,
        self.power_of_heaters = False,
        self.grid_meter_frame = False
