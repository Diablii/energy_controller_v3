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


class Constants:
    def __init__(self):
        self.DEVICE_ID = b"242186a1-15ce-4157-bfb3-81545e4ac2d5"
        self.SECRET_KEY = b"anJxtmZnXeNRrlakm1yMd?gUL"
        self.HEATER_2000W_POWER = 2000
        self.HEATER_1000W_POWER = 1000
        self.HEATER_500W_POWER = 500


