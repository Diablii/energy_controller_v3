import sys

import logging

from energy_manager import EnergyManager

sys.path.append("lib")


def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    energy_manager = EnergyManager()
    energy_manager.start()


if __name__ == "__main__":
    main()
