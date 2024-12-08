class Watchdog:
    def __init__(self):
        # int - board the board on which the application is running
        # ext - a board that is ext and sends a watchdog signal periodically
        self.wdg_int_ext = False
        self.wdg_ext_int = False
        self.wdg_ext_int_timestamp = 0.0
        self.wdg_ext_int_timestamp_old = 0.0
        self.wdg_ext_int_counter = 0
        self.wdg_ext_int_counter_old = 0
        self.wdg_ext_int_failed_counter = 0


class Devices:
    def __init__(self):
        self.gridmeter_alive = True
        self.executor_alive = True
