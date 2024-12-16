import pytest
import time
from threading import Thread
from unittest.mock import MagicMock, patch
from controller.services.watchdog import Watchdog, Devices


@pytest.fixture
def watchdog():
    return Watchdog()


@pytest.fixture
def devices():
    return Devices()


def test_is_watchdog_alive(watchdog):
    # Test gdy watchdog jest aktywny
    watchdog.wdg_ext_int_counter = 10
    watchdog.wdg_ext_int_counter_old = 5
    watchdog.wdg_ext_int_timestamp = 20.0
    watchdog.wdg_ext_int_timestamp_old = 15.0

    assert watchdog._is_watchdog_alive()

    # Test gdy watchdog nie jest aktywny
    watchdog.wdg_ext_int_counter = 5
    watchdog.wdg_ext_int_counter_old = 5
    watchdog.wdg_ext_int_timestamp = 15.0
    watchdog.wdg_ext_int_timestamp_old = 15.0

    assert not watchdog._is_watchdog_alive()


def test_reset_watchdog_state(watchdog, devices):
    watchdog.wdg_ext_int_counter_old = 5
    watchdog.wdg_ext_int_timestamp_old = 10.0
    watchdog.wdg_ext_int_counter = 10
    watchdog.wdg_ext_int_timestamp = 15.0

    watchdog._reset_watchdog_state(devices)

    assert watchdog.wdg_ext_int_counter_old == 10
    assert watchdog.wdg_ext_int_timestamp_old == 15.0
    assert devices.gridmeter_alive is True


@patch("time.sleep", return_value=None)
def test_handle_watchdog_failure(mock_sleep, watchdog, devices):
    devices.gridmeter_alive = True
    watchdog.wdg_ext_int_failed_counter = 0

    watchdog._handle_watchdog_failure(devices, max_failures=3)

    assert devices.gridmeter_alive is False
    assert watchdog.wdg_ext_int_failed_counter == 1


@patch("time.sleep", return_value=None)
@patch("sys.exit", side_effect=Exception("Exit called"))
def test_trigger_reset(mock_exit, mock_sleep, watchdog):
    with pytest.raises(Exception, match="Exit called"):
        watchdog._trigger_reset(max_failures=3)

    assert mock_sleep.call_count == 3
    mock_exit.assert_called_once()


def test_reset_watchdog_counters(watchdog):
    watchdog.wdg_ext_int_counter = 150
    watchdog.wdg_ext_int_failed_counter = 10

    watchdog._reset_watchdog_counters()

    assert watchdog.wdg_ext_int_counter == 0
    assert watchdog.wdg_ext_int_failed_counter == 0


# Funkcja do mockowania _is_watchdog_alive
# Funkcja do mockowania _is_watchdog_alive
def side_effect_is_alive():
    """Symuluje działanie funkcji _is_watchdog_alive."""
    return [True, False]  # Lista stanów: najpierw True, potem False

def simulate_watchdog_counter(watchdog):
    while True:
        watchdog.wdg_ext_int_counter += 1
        time.sleep(0.1)

# @patch("time.sleep", return_value=None)
# # @patch("if self.wdg_ext_int_counter > 150:", side_effect=SystemExit)
# @patch("sys.exit", side_effect=SystemExit)  # Mockujemy sys.exit, aby podnieść SystemExit
def test_run_watchdog():
    # Utwórz instancję watchdog
    watchdog = Watchdog()  # Zakładamy, że klasa jest już zaimportowana
    devices = MagicMock()  # Mock obiektu devices
    devices.gridmeter_alive = True  # Przykładowy stan początkowy

    # Mockowanie zależności
    mock_is_alive = patch.object(watchdog, "_is_watchdog_alive", return_value=True).start()
    mock_reset_state = patch.object(watchdog, "_reset_watchdog_state").start()
    mock_handle_failure = patch.object(watchdog, "_handle_watchdog_failure").start()
    mock_reset_counters = patch.object(watchdog, "_reset_watchdog_counters").start()

    # Inicjalizacja początkowego stanu
    watchdog.wdg_ext_int_counter = 0

    # Wywołanie metody w trybie testowym
    watchdog.run_watchdog(devices, interval=0.1, max_failures=3, testing_mode=1)

    # Sprawdzenie, czy licznik został zaktualizowany w trybie testowym
    assert watchdog.wdg_ext_int_counter > 0, "Licznik nie został zaktualizowany"

    # Sprawdzenie, czy zostały wywołane odpowiednie metody
    mock_reset_state.assert_called()
    mock_is_alive.assert_called()
    mock_reset_counters.assert_called()

    # Oczekujemy, że `testing_mode` kończy pętlę
    assert watchdog.wdg_ext_int_counter == 151, "Pętla nie zakończyła się na czas"

    # Zatrzymanie patchowania
    patch.stopall()