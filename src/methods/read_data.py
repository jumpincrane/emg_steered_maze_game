import time
from src.pytringos.pytringos import TrignoAdapter
import sys, signal

def signal_handler(signal, frame):
    trigno_sensors.stop_acquisition()
    sys.exit(0)


if __name__ == "__main__":
    trigno_sensors = TrignoAdapter()
    trigno_sensors.add_sensors(sensors_mode='EMG', sensors_ids=(4,), sensors_labels=('EMG1',), host='150.254.46.37')
    trigno_sensors.add_sensors(sensors_mode='ORIENTATION', sensors_ids=(4,), sensors_labels=('ORIENTATION1',), host='150.254.46.37')
    trigno_sensors.start_acquisition()

    time_period = 1.0 #s
    signal.signal(signal.SIGINT, signal_handler)

    while(True):
        time.sleep(time_period)
        sensors_reading = trigno_sensors.sensors_reading()
        print(sensors_reading)
    trigno_sensors.stop_acquisition()