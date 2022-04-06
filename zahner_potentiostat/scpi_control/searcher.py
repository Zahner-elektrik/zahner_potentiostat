'''
  ____       __                        __    __   __      _ __
 /_  / ___ _/ /  ___  ___ ___________ / /__ / /__/ /_____(_) /__
  / /_/ _ `/ _ \/ _ \/ -_) __/___/ -_) / -_)  '_/ __/ __/ /  '_/
 /___/\_,_/_//_/_//_/\__/_/      \__/_/\__/_/\_\\__/_/ /_/_/\_\

Copyright 2022 Zahner-Elektrik GmbH & Co. KG

Permission is hereby granted, free of charge, to any person obtaining
a copy of this software and associated documentation files (the "Software"),
to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense,
and/or sell copies of the Software, and to permit persons to whom the Software
is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included
in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH
THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
'''

import glob
import sys
import time

from serial.serialwin32 import Serial
import serial.tools.list_ports


class SCPIDeviceSearcher():
    """ Search for Zahner devices.
    
    Each Zahner device provides two serial interfaces via USB.
    The USB Product ID 0xA3AD is registered for Zahner.

    With this class Zahner devices are searched and can be integrated more simply.
    For example in the Windows device manager you can't see immediately which comports belong
    to which device, because the numbers of the comports can change.

    This class always returns the names of the serial interfaces with the corresponding methods.
    """
    ZAHNER_SCPI_DEVICENAME = "ZAHNER-ELEKTRIK"
    ZAHNER_VID = 0x0483
    ZAHNER_PID = 0xA3AD

    def __init__(self):
        """
        Constructor
        """
        self.commandInterface = None
        self.dataInterface = None
        
    def searchDevices(self):
        """ Search connected devices with IDN command.
        
        It is NOT recommended to use this command, because it opens all serial ports of the computer
        and speaks to the devices with the string \*IDN?, this could cause interference with the devices.
        
        :returns: Returns a list with serial numbers of connected Zahner devices. The serial numbers are strings.
        """
        devices = self.searchDevicesWithIDN(None)
        return devices
        
    def searchZahnerDevices(self):
        """ Search connected devices with Zahner PID and VID and IDN command.
        
        This command should be used to search for Zahner devices.
        Only Zahner devices are addressed for identification with this command.
        
        :returns: Returns a list with serial numbers of connected Zahner devices. The serial numbers are strings.
        """
        serialInterfacesWithZahnerVIDPID = self.searchSerialInterfacesWithZahnerVIDPID()
        devices = self.searchDevicesWithIDN(serialInterfacesWithZahnerVIDPID)
        return devices
    
    def searchSerialInterfacesWithZahnerVIDPID(self):
        """ Search serial interfaces with Zahner PID and VID.
        
        Checks the VID and PID of the serial interfaces, if it is a Zahner device.
        
        :returns: List with serial interface names with Zahner PID and VID.
        """
        ports = serial.tools.list_ports.comports()
        portsWithZahnerDevices = []
        for port in ports:
            if port.vid == SCPIDeviceSearcher.ZAHNER_VID and port.pid == SCPIDeviceSearcher.ZAHNER_PID:
                portsWithZahnerDevices.append(port.device)
        return portsWithZahnerDevices
    
    def searchDevicesWithIDN(self, ports=None):
        """ Search connected devices with IDN command.
        
        Opens all serial interfaces and sends the string \*IDN? to the device and evaluates the response.
        If a list of serial interfaces is passed for the ports parameter, only this list of ports is checked.
        
        :param ports: List of serial interface names to be scanned.
        :returns: Returns a list with serial numbers of connected Zahner devices. The serial numbers are strings.
        """
        
        self.comportsWithHPDevice = []
        self.comportsWithZahnerDevices = []
        self.foundZahnerDevicesSerialNumbers = []
        
        if ports == None:
            ports = self._getAvailableSerialInterfaceNames()
            print("Serial interfaces found: " + str(ports))
        
        for port in ports:
            print(port + ":")
            try:
                connection = Serial(port=port, timeout=1, write_timeout=1)
                writeTime = time.time()
                connection.write(bytearray("*IDN?\n", "ASCII"))
                while 1 > (time.time() - writeTime) and connection.inWaiting() == 0:
                    """
                    Wait 1 second or until data has arrived.
                    """
                    pass
                if connection.inWaiting() == 0:
                    connection.close()
                    raise serial.SerialTimeoutException()
                data = connection.read(1000)
                data = data.decode("ASCII") 
                connection.close()
                print(data)
                string = data.split(",")
                if len(data) > 3:
                    DeviceManufacturer = string[0].strip()
                    DeviceName = string[1].strip()
                    DeviceSerialNumber = string[2].strip()
                    DeviceSoftwareVersion = string[3].replace("binary","").strip()
                    
                    isBinary = False
                    if "binary" in data:
                        isBinary = True
                    
                    if SCPIDeviceSearcher.ZAHNER_SCPI_DEVICENAME in DeviceManufacturer:
                        data = dict()
                        data["serial_name"] = port
                        data["manufacturer"] = DeviceManufacturer
                        data["name"] = DeviceName
                        data["serialnumber"] = DeviceSerialNumber
                        data["software_version"] = DeviceSoftwareVersion
                        data["binary"] = isBinary
                        self.comportsWithZahnerDevices.append(data)
                        if DeviceSerialNumber not in self.foundZahnerDevicesSerialNumbers:
                            self.foundZahnerDevicesSerialNumbers.append(DeviceSerialNumber)
                    elif "HEWLETT-PACKARD" in DeviceManufacturer:
                        """
                        HP Multimeter is needed in-house, for calibration.
                        This can be seen as an example if other serial devices are
                        to be included in order to be able to find them.
                        """
                        self.comportsWithHPDevice.append(port)
                else:
                    print("error device answer: " + data)                
            except:
                print("error: " + port)
                
        return self.foundZahnerDevicesSerialNumbers
    
    def selectDevice(self, serialNumber = None):
        """ Select a found device.
        
        This method selects a device by its serial number.
        If no serial number is passed, then the first found device is selected.
        The serial number must be specified as a string.
        
        This function returns two values the command comport and the online live data comport.
        If the respective comport is not found None is returned.

        The data has to be read from the online channel, otherwise the measuring device hangs.
        The online channel can also be used by other software like the Zahner-Lab to use it as a display.
        
        :param serialNumber: The serial number of the device to select as string.
        :returns: Two strings commandInterface, dataInterface with the port names.
        """
        self.commandInterface = None
        self.dataInterface = None
        
        if serialNumber == None:
            """
            Use the first device if no serialnumber was set.
            """
            if len(self.foundZahnerDevicesSerialNumbers) > 0:
                serialNumber = self.foundZahnerDevicesSerialNumbers[0]
            else:
                print("no device found")
                return None, None
        """
        Search for the comports found in the previous one.
        """
        for device in self.comportsWithZahnerDevices:
            if serialNumber in device["serialnumber"] and device["binary"] == True:
                self.dataInterface = device["serial_name"]
            elif serialNumber in device["serialnumber"]:
                self.commandInterface = device["serial_name"]
                
        return self.commandInterface, self.dataInterface   
    
    def getCommandInterface(self):
        """ Select a found command interface.
        
        Returns the name of the serial interface. If no device was selected before, the first one is selected.
        If no interface exists, None is returned.
        
        :returns: Returns a string with the name of the serial interface. None if no command interface was found.
        """
        if self.commandInterface == None and len(self.comportsWithZahnerDevices) > 0:
            self.selectDevice()
        return self.commandInterface
        
    def getDataInterface(self):
        """ Select a found data interface.
        
        Returns the name of the serial interface. If no device was selected before, the first one is selected.
        If no interface exists, None is returned.
        
        :returns: Returns a string with the name of the serial interface. None if no command interface was found.
        """
        if self.commandInterface == None and len(self.comportsWithZahnerDevices) > 0:
            self.selectDevice()
        return self.dataInterface
    
    def getMultimeterPort(self):
        """ Returns the comport to which the multimeter is connected.

        HP Multimeter is needed in-house, for calibration.
        This can be seen as an example if other serial devices are
        to be included in order to be able to find them.
        
        :returns: The first comport with an HP device.
        """
        if len(self.comportsWithHPDevice) > 0:
            return self.comportsWithHPDevice.pop(0)
        else:
            return None
        
    def _getAvailableSerialInterfaceNames(self):
        """ Detect the available serial interfaces.

        This function determines the available serial interfaces independently of the platform.
        
        :returns: A List with available comport names.
        """
        if sys.platform.startswith("win"):
            ports = ["COM%s" % (i + 1) for i in range(256)]
        elif sys.platform.startswith("linux") or sys.platform.startswith("cygwin"):
            # this excludes your current terminal "/dev/tty"
            ports = glob.glob("/dev/tty[A-Za-z]*")
        elif sys.platform.startswith("darwin"):
            ports = glob.glob("/dev/tty.*")
        else:
            raise EnvironmentError("Unsupported platform")
    
        result = []
        for port in ports:
            try:
                s = Serial(port = port, timeout=1, write_timeout=1)
                s.close()
                result.append(port)
            except:
                pass
        return result
