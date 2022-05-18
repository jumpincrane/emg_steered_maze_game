import socket
import struct
import numpy
from collections import defaultdict
import pandas as pd
import datetime

class _BaseTrignoDaq(object):
    """
    Delsys Trigno wireless EMG system.

    Requires the Trigno Control Utility to be running.

    Parameters
    ----------
    host : str
        IP address the TCU server is running on.
    cmd_port : int
        Port of TCU command messages.
    data_port : int
        Port of TCU data access.
    rate : int
        Sampling rate of the data source.
    total_channels : int
        Total number of channels supported by the device.
    timeout : float
        Number of seconds before socket returns a timeout exception

    Attributes
    ----------
    BYTES_PER_CHANNEL : int
        Number of bytes per sample per channel. EMG and accelerometer data
    CMD_TERM : str
        Command string termination.

    Notes
    -----
    Implementation details can be found in the Delsys SDK reference:
    http://www.delsys.com/integration/sdk/
    """

    BYTES_PER_CHANNEL = 4
    CMD_TERM = '\r\n\r\n'
    #CONFIGURATION_MODES = {'EMG':40, 'EMGACC':3, 'EMGGYRO':7, 'EMGIMU':65, 'EMGORIENTATION':66, 'IMU':609}
    CONFIGURATION_MODES = {'40':'EMG', '3':'EMG+ACC', '7':'EMG+GYRO', '65':'EMG+IMU', '66':'EMG+ORIENTATION', '609':'IMU'}

    def __init__(self, host, cmd_port, data_port, total_channels, timeout):
        self.host = host
        self.cmd_port = cmd_port
        self.data_port = data_port
        self.total_channels = total_channels
        self.timeout = timeout

        self._min_recv_size = self.total_channels * self.BYTES_PER_CHANNEL
        self.max_number_of_sensors = 16

        self._initialize()

    def _initialize(self):

        # create command socket and consume the servers initial response
        self._comm_socket = socket.create_connection(
            (self.host, self.cmd_port), self.timeout)
        self._comm_socket.recv(1024)

        # create the data socket
        self._data_socket = socket.create_connection(
            (self.host, self.data_port), self.timeout)

        # set data socket to non blocking to not block when there is no data to read, it allows to raise BlockingIOError when all data has been read
        self._data_socket.setblocking(False)

    def start(self):
        """
        Tell the device to begin streaming data.
        """
        self._send_cmd('START')

    def read_all(self):
        """
        Receive all available samples from TCP buffer.
        This is a non-blocking method, meaning it could return zero samples when buffer is empty or all samples.

        Returns
        -------
        data : ndarray, shape=(total_channels, number_of_samples)
            Data read from the device. Each channel is a row and each column
            is a point in time.
        """
        packet = bytes()
        lacking_bytes = 0
        while(True):
            try:
                packet += self._data_socket.recv(self._min_recv_size + lacking_bytes)
                relative_packet_length = len(packet) % self._min_recv_size
                if(relative_packet_length != 0):
                    lacking_bytes = self._min_recv_size - relative_packet_length
            except BlockingIOError:
                if(lacking_bytes == 0):
                    break
                else:
                    #insecure, because it can loop many many times when connection is very weak, should be timeouted also
                    pass
            except socket.timeout:
                packet += b'\x00' * (lacking_bytes)
                raise IOError("Device disconnected.")
        number_of_samples = int(len(packet) / self._min_recv_size)
        data = numpy.asarray(
            struct.unpack('<'+'f'*self.total_channels*number_of_samples, packet), dtype =numpy.float32) #type of data from sdk
        data = numpy.transpose(data.reshape((-1, self.total_channels)))
        return data

    def stop(self):
        """Tell the device to stop streaming data."""
        self._send_cmd('QUIT')

    def reset(self):
        """Restart the connection to the Trigno Control Utility server."""
        self._initialize()

    def __del__(self):
        try:
            self._comm_socket.close()
        except:
            pass

    @staticmethod
    def _channels_mask(sensors_ids, number_of_channels, channels_per_sensor):
        """
           Create mask for channels to receive data.

           Parameters
           ----------
           sensors_ids : tuple
               Identifiers of used sensors, e.g. (1, 2,) obtains data from sensors 1 and 2.
           number_of_channels : int
               Number of data channels for one measurement (e.g. EMG data is 1 data channel and Quaternion 4 data channels)
           channels_per_sensor : int
               Number of data channels assigned for one sensor

           Returns
           ----------
           sensors_mask : list
               Mask of channels when expected data occurs.

        """
        sensors_mask = []
        for sensor_iter, sensor_id in enumerate(sensors_ids):
            sensor_mask = list(range(channels_per_sensor*sensor_id-channels_per_sensor, channels_per_sensor*sensor_id-channels_per_sensor+number_of_channels))
            sensors_mask.extend(sensor_mask)
        return sensors_mask

    def _send_cmd(self, command, return_reply = False):
        self._comm_socket.send(self._cmd(command))
        raw_resp = self._comm_socket.recv(128)
        formated_resp = self._get_reply(raw_resp)
        if('?') in command:
            print("Query: {} <->  Reply: {}".format(command, formated_resp))
        else:
            print("Command: {} <->  Reply: {}".format(command, formated_resp))
        if return_reply:
            return formated_resp

    def _get_reply(self, response):
        reply = struct.unpack(str(len(response)) + 's', response)
        reply = reply[0].decode(encoding='ascii')
        if(self.CMD_TERM in reply):
            reply = reply.replace(self.CMD_TERM,'')
        return reply

    def set_mode(self,sensor_number, mode_number):
        """
           Command to set the mode the given sensor.

           Parameters
           ----------
           sensor_number : int
               ID of sensor
           mode_number : int
               Desired mode of sensor.
        """
        self._send_cmd(f'SENSOR {sensor_number} SETMODE {mode_number}')

    def set_backwards_compatibility(self, flag = 'ON'):
        """
           Command to set the backwards compatibility. It is on by default.

           Parameters
           ----------
           flag : str
               ON or OFF flag
        """
        self._send_cmd(f'BACKWARDS COMPATIBILITY {flag}')

    def set_upsampling(self, flag = 'ON'):
        """
           Command to set the upsampling. It is on by default.

           Parameters
           ----------
           flag : str
               ON or OFF flag
        """
        self._send_cmd(f'UPSAMPLE {flag}')

    def pair_sensor(self,sensor_number):
        """
           Command to pair sensor.

           Parameters
           ----------
           sensor_number : int
               ID of sensor
        """
        self._send_cmd(f'SENSOR {sensor_number} PAIR')

    def is_paired(self, sensor_number):
        """
           Query to check if sensor is paired with base.

           Parameters
           ----------
           sensor_number : int
               ID of sensor
        """
        reply = self._send_cmd(f'SENSOR {sensor_number} PAIRED?', return_reply=True)
        return reply

    def what_serial(self,sensor_number):
        """
           Query to get unique serial number of sensor.

           Parameters
           ----------
           sensor_number : int
               ID of sensor
        """
        self._send_cmd(f'SENSOR {sensor_number} SERIAL?', return_reply=False)

    def what_rate(self,sensor_number, channel_number):
        """
           Query to get sampling frequency on the sensor's channel.

           Parameters
           ----------
           sensor_number : int
               ID of sensor
           channel_number : int
               Number of channel
        """
        self._send_cmd(f'SENSOR {sensor_number} CHANNEL {channel_number} RATE?', return_reply=False)

    def where_start(self,sensor_number):
        """
           Query which position in the data buffer a given sensor’s first channel will appear.

           Parameters
           ----------
           sensor_number : int
               ID of sensor
        """
        self._send_cmd(f'SENSOR {sensor_number} STARTINDEX?', return_reply=False)

    def what_aux_channel_count(self,sensor_number):
        """
           Query the number of AUX channels in use on a given sensor.

           Parameters
           ----------
           sensor_number : int
               ID of sensor
        """
        self._send_cmd(f'SENSOR {sensor_number} AUXCHANNELCOUNT?', return_reply=False)

    def what_mode(self,sensor_number):
        """
           Query to current mode of a given sensor

           Parameters
           ----------
           sensor_number : int
               ID of sensor
        """
        reply = self._send_cmd(f'SENSOR {sensor_number} MODE?', return_reply = True)
        try:
            print(f'This is {self.CONFIGURATION_MODES[reply]} mode.')
        except:
            print('Unrecognized mode')

    def is_active(self,sensor_number):
        """
           Query the active state of a given sensor.

           Parameters
           ----------
           sensor_number : int
               ID of sensor
        """
        reply = self._send_cmd(f'SENSOR {sensor_number} ACTIVE?', return_reply = True)
        return reply

    @staticmethod
    def _cmd(command):
        return bytes("{}{}".format(command, _BaseTrignoDaq.CMD_TERM),
                     encoding='ascii')

    @staticmethod
    def _validate(response):
        s = str(response)
        if 'OK' not in s:
            print("warning: TrignoDaq command failed: {}".format(s))


class TrignoEMG(_BaseTrignoDaq):
    """
    Delsys Trigno wireless EMG system EMG data.

    Requires the Trigno Control Utility to be running.

    Parameters
    ----------
    sensors_ids : tuple with sensors ids
        Identifiers of used sensors, e.g. (1, 2,) obtains data from
        sensors 1 and 2.
    units : {'V', 'mV', 'normalized'}, optional
        Units in which to return data. If 'V', the data is returned in its
        un-scaled form (volts). If 'mV', the data is scaled to millivolt level.
        If 'normalized', the data is scaled by its maximum level so that its
        range is [-1, 1].
    host : str, optional
        IP address the TCU server is running on. By default, the device is
        assumed to be attached to the local machine.
    cmd_port : int, optional
        Port of TCU command messages.
    data_port : int, optional
        Port of TCU EMG data access. By default, 50041 is used, but it is
        configurable through the TCU graphical user interface.
    timeout : float, optional
        Number of seconds before socket returns a timeout exception.

    Attributes
    ----------
    rate : int
        Sampling rate in Hz.
    scaler : float
        Multiplicative scaling factor to convert the signals to the desired
        units.
    """

    def __init__(self, sensors_ids, units='V',
                 host='localhost', cmd_port=50040, data_port=50043, timeout=10):
        super(TrignoEMG, self).__init__(
            host=host, cmd_port=cmd_port, data_port=data_port,
            total_channels=16, timeout=timeout)

        self.data_channels = 1
        channels_per_sensor = int(self.total_channels / self.max_number_of_sensors) # 1 for EMG
        self.channels_mask = self._channels_mask(sensors_ids=sensors_ids, number_of_channels=self.data_channels,
                                                 channels_per_sensor=channels_per_sensor)
        self.rate = 2000

        self.scaler = 1.
        if units == 'mV':
            self.scaler = 1000.
        elif units == 'normalized':
            # max range of EMG data is 11 mV
            self.scaler = 1 / 0.011


    def read_time_data(self):
        """
        Receive all available samples from TCP buffer with timestamps.
        This is a non-blocking method, meaning it could return zero samples when buffer is empty or all samples.

        Returns
        -------
        data : ndarray, shape=(total_channels, number_of_samples)
            Data read from the device. Each channel is a row and each column
            is a point in time.
        """
        starting_time = datetime.datetime.now()
        data = super(TrignoEMG, self).read_all()
        data = data[self.channels_mask,:]
        number_of_samples = data.shape[1]
        time_period = round(1 / self.rate, 4)
        timestamps = pd.date_range(starting_time, periods=number_of_samples, freq=f'{time_period}S')
        return data, timestamps

class TrignoOrientation(_BaseTrignoDaq):
    """
    Delsys Trigno wireless EMG system orientation data.

    Requires the Trigno Control Utility to be running.

    Parameters
    ----------
    channel_range : tuple with 2 ints
        Sensor channels to use, e.g. (lowchan, highchan) obtains data from
        channels lowchan through highchan. Each sensor has three accelerometer
        channels.
    host : str, optional
        IP address the TCU server is running on. By default, the device is
        assumed to be attached to the local machine.
    cmd_port : int, optional
        Port of TCU command messages.
    data_port : int, optional
        Port of TCU accelerometer data access. By default, 50042 is used, but
        it is configurable through the TCU graphical user interface.
    timeout : float, optional
        Number of seconds before socket returns a timeout exception.
    """
    def __init__(self, sensors_ids, host='localhost',
                 cmd_port=50040, data_port=50044, timeout=10):
        super(TrignoOrientation, self).__init__(
            host=host, cmd_port=cmd_port, data_port=data_port,
            total_channels=144, timeout=timeout)

        self.data_channels = 4
        channels_per_sensor = int(self.total_channels / self.max_number_of_sensors) # 9 for quaternion
        self.channels_mask = self._channels_mask(sensors_ids=sensors_ids, number_of_channels=self.data_channels, channels_per_sensor = channels_per_sensor)

        self.rate = 148.148 #when upsampling and backward compability are on
        #self.rate = 74.074


    def read_time_data(self):
        """
        Receive all available samples from TCP buffer with timestamps.
        This is a non-blocking method, meaning it could return zero samples when buffer is empty or all samples.

        Returns
        -------
        data : ndarray, shape=(total_channels, number_of_samples)
            Data read from the device. Each channel is a row and each column
            is a point in time.
        """
        starting_time = pd.datetime.now()
        data = super(TrignoOrientation,self).read_all()
        data = data[self.channels_mask,:]
        number_of_samples = data.shape[1]
        time_period = round(1 / self.rate, 4)
        timestamps = pd.date_range(starting_time, periods=number_of_samples, freq=f'{time_period}S')
        return data, timestamps


class TrignoAdapter():
    """
    Delsys Trigno wireless interface for managing sensors bundles.
    """
    TRIGNO_MODE_TO_CLASS = {
        'EMG': TrignoEMG,
        'ORIENTATION': TrignoOrientation,
    }
    TRIGNO_CLASS_TO_MODE = {value: key for key, value in TRIGNO_MODE_TO_CLASS.items()}
    def __init__(self):
        QUATERNION = ['qw', 'qx', 'qy', 'qz']

        self.data_buff = pd.DataFrame(columns=['Sensor_id', 'EMG', *QUATERNION])
        self.active_sensors = defaultdict(list)
        self.TRIGNO_MODE_TO_COLUMNS = {
            'ORIENTATION': self.data_buff.columns[2:],
            'EMG': [self.data_buff.columns[1]]
        }
        pass

    @classmethod
    def __create_sensors(cls,sensors_mode, sensors_ids, host='localhost'):
        try:
            trigno_sensor = cls.TRIGNO_MODE_TO_CLASS[sensors_mode](host=host, sensors_ids=sensors_ids)
            for sensor_id in sensors_ids:
                reply_paired = trigno_sensor.is_paired(sensor_id)
                if (reply_paired == 'NO'):
                    print(f'Sensor {sensor_id} is unpaired. Please pair.')
                    return None
                else:
                    reply_active = trigno_sensor.is_active(sensor_id)
                    if (reply_active == 'YES'):
                        print(f'Sensor {sensor_id} is active.')
                    else:
                        print(f'Sensor {sensor_id} is inactive.')
            return trigno_sensor
        except:
            print(f'Connection problem or unrecognized sensor mode {sensors_mode}. Available types: {list(cls.TRIGNO_MODE_TO_CLASS.keys())}')
            return None


    def add_sensors(self,sensors_mode, sensors_ids, sensors_labels, host='localhost'):
        """
           Add sensor to sensor bundle.

           Parameters
           ----------
           sensors_mode : str
               Desired mode of sensors. (e.g. 'ORIENTATION' or 'EMG')
           sensors_ids : tuple
               Identifiers of used sensors, e.g. (1, 2,) obtains data from
               sensors 1 and 2.
           sensors_labels : tuple
               Labels for used sensors, e.g ('ORIENTATION1', 'ORIENTATION2',). When nothing
               passed then identifiers are used as labels.
            host : str
                IP address of Delsys Trigno Controll Utility or localhost
        """
        if(len(sensors_labels) != len(sensors_ids)):
            sensors_labels = sensors_ids
            print(f'Incorrent number of sensor labels. Changing labels to: {sensors_labels}')
        trigno_sensors = self.__create_sensors(sensors_mode=sensors_mode,sensors_ids=sensors_ids, host=host)
        if(trigno_sensors):
            sensor_mode = self.TRIGNO_CLASS_TO_MODE[type(trigno_sensors)]
            if(type(trigno_sensors) in [type(sensor) for sensor in self.active_sensors[sensors_labels]]):
                print(f'There is an existing sensor with mode: {sensor_mode} and label: {sensors_labels}. Try to change the sensor label or configuration of existing sensor.')
            else:
                self.active_sensors[sensors_labels].append(trigno_sensors)
                print(f'Sensors {sensors_ids} with mode: {sensor_mode} and label: {sensors_labels} has been added.')
        else:
            print('There are unpaired sensors. Please configure sensors adding.')
        #print(list(self.active_sensors.keys())[0][0])

    def start_acquisition(self):
        """
        Start data acquisition from all sensors.
        """
        try:
            list(self.active_sensors.values())[0][0].start()
        except:
            print('Could not start acquisition. There has been no sensors added.')

    def stop_acquisition(self):
        """
        Stop data acquisition from all sensors.
        """
        try:
            list(self.active_sensors.values())[0][0].stop()
        except:
            print('Could not stop acquisition. There has been no sensors added.')

    def sensors_reading(self, sensors_labels = '', buffered = True):
        """
           Read data from sensors. Data comes in packets so there could be more
           than 1 sample from sensor in one reading. Orientation measurements contains
           NaN in EMG column and EMG measurements contains NaNs in quaternion's columns.

           Parameters
           ----------
           sensors_labels : tuple
               Labels for sensors to get reading from, e.g ('ORIENTATION1', 'ORIENTATION2',). When nothing
               passed data is read from all sensors.
           buffered : Bool
               Flag to store all data in buffer

           Returns
           ----------
           sensors_reading : pandas.DataFrame
               Measurements from given sensors. DataFrame columns are: [Sensor_id, EMG, qw, qx, qy, qz]
        """
        sensors_reading = pd.DataFrame(columns=self.data_buff.columns)
        if not(sensors_labels):
            sensors_labels = (*(*self.active_sensors,),)
        elif not(set(self.active_sensors.keys()).intersection(set((sensors_labels,)))):
            raise ValueError("Unrecognized sensors labels.")
        for sensors_label in sensors_labels:
            for sensors in self.active_sensors[sensors_label]:
                data, timestamps = sensors.read_time_data()
                sensor_mode = self.TRIGNO_CLASS_TO_MODE[type(sensors)]
                columns = self.TRIGNO_MODE_TO_COLUMNS[sensor_mode]
                for sensor_iter, sensor_label in enumerate(sensors_label):
                    sensor_mask = list(range(sensor_iter*sensors.data_channels,sensor_iter*sensors.data_channels+sensors.data_channels))
                    sensor_data = data[sensor_mask,:]
                    data_frame = pd.DataFrame(data=sensor_data.T, columns=columns, index = timestamps)
                    data_frame[self.data_buff.columns[0]] = sensor_label
                    sensors_reading = pd.concat([sensors_reading, data_frame], sort=False)
        if(buffered):
            self.data_buff = pd.concat([self.data_buff, sensors_reading], sort=False)
        return sensors_reading














