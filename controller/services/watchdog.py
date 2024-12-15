import time
import logging
import sys


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

    def run_watchdog(self, devices, interval=10, max_failures=5):
        """Method which start the watchdog for checking status of external device"""
        # TODO handle the different type of device base on args in function, potential two other instances
        while True:
            time.sleep(interval)

            if self._is_watchdog_alive():
                self._reset_watchdog_state(devices)
                logging.info(f"[WATCHDOG] GRIDMETER ALIVE: {devices.gridmeter_alive}")
            else:
                self._handle_watchdog_failure(devices, max_failures)

            if self.wdg_ext_int_counter > 150:
                self._reset_watchdog_counters()

    def _is_watchdog_alive(self):
        """Auxiliary method: check that watchdog is alive"""
        return (self.wdg_ext_int_counter != self.wdg_ext_int_counter_old and
                self.wdg_ext_int_timestamp != self.wdg_ext_int_timestamp_old)

    def _reset_watchdog_state(self, devices):
        """Auxiliary method: reset the counter and set state"""
        self.wdg_ext_int_counter_old = self.wdg_ext_int_counter
        self.wdg_ext_int_timestamp_old = self.wdg_ext_int_timestamp
        devices.gridmeter_alive = True

    def _handle_watchdog_failure(self, devices, max_failures):
        """Auxiliary method: handle the counting a failures of watchdog"""
        devices.gridmeter_alive = False
        logging.info(f"[WATCHDOG] GRIDMETER ALIVE: {devices.gridmeter_alive}")
        self.wdg_ext_int_failed_counter += 1

        if self.wdg_ext_int_failed_counter > max_failures:
            self._trigger_reset(max_failures)

    @staticmethod
    def _trigger_reset(self, max_failures):
        """Auxiliary method: counting time to reset of external device"""
        for i in range(max_failures, 0, -1):
            logging.info(f"[WATCHDOG] TRIGGER RESET, RESET IN {i}")
            time.sleep(1)
        sys.exit(1)

    def _reset_watchdog_counters(self):
        """Auxiliary method: reset of watchdog counter"""
        self.wdg_ext_int_counter = 0
        self.wdg_ext_int_failed_counter = 0
        logging.info(f"[WATCHDOG] GRIDMETER COUNTER RESET")


class Devices:
    def __init__(self):
        self.gridmeter_alive = True
        self.executor_alive = True
