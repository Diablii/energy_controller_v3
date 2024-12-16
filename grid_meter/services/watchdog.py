class Watchdog:
    def __init__(self):
        self.wdg_int_ext = False
        self.wdg_ext_int = False
        self.wdg_ext_int_counter = 0
        self.wdg_ext_int_counter_old = 0
        self.wdg_ext_int_failed_counter = 0


class Devices:
    def __init__(self):
        self.controller_alive = True
        self.executor_alive = true