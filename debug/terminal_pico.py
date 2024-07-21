import serial
from datetime import datetime

COM = input("Insert COM number like 'COM6': ")
SPEED = input("Insert baud-rate of UART: ")

ser = serial.Serial(COM, SPEED)

try:
    with open("uart_log.txt", "a", buffering=1) as log_file:
        while True:
            data = ser.readline().decode().strip()
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_line = f"[{current_time}] {data}"
            print(data)
            log_file.write(log_line + '\n')

except KeyboardInterrupt:
    ser.close()