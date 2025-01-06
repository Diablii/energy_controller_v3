import sys

import logging
import time
from threading import Thread

from energy_manager import EnergyManager

sys.path.append("lib")


def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    energy_manager = EnergyManager()

    adjust_heaters_thread = Thread(target=energy_manager.run_energy_management)
    adjust_heaters_thread.start()
    watchdog_gridmeter_thread = Thread(target=energy_manager.watchdog.run_watchdog, args=(energy_manager.devices,))
    watchdog_gridmeter_thread.start()

    # energy_manager.client.start()
    client_start = Thread(target=energy_manager.client.start)
    client_start.start()



if __name__ == "__main__":
    main()
