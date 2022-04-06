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

from abc import ABCMeta, abstractmethod
from datetime import datetime
import threading
from .error import ZahnerConnectionError
import serial
from enum import Enum
import queue
from serial.serialutil import SerialException
import time

"""
With DEBUG = True it is switched on that log strings are stored.
Then all commands that are sent and responses that are received are saved with timestamp.
"""
DEBUG = False


class CommandType(Enum):
    """
    Class for the two different command types.
    """
    COMMAND = 1
    CONTROL = 2

    
class SerialInterface(metaclass=ABCMeta):
    """
    Abstract base class from which the data and command interfaces are derived.
    """

    def __init__(self, serialName):
        """ Constructor
        :param serialName: Name of the serial interface.
        """
        self.serialName = serialName
        self.serialConnection = None
        self.logData = []
        self.connect(self.serialName)
        self._startTelegramListener()
    
    def connect(self, serialName=None):
        """ Connect to a serial interface.
        
        This method opens a serial interface.
        
        :param serialName: Name of the serial interface.
        :returns: True if it connected, else false.  Prints to the console if the
            connection is not possible.
        """
        try:
            if serialName == None:
                self.serialConnection = serial.Serial(self.serialName)  # timeout = 1, newline = '\n'
            else:
                self.serialName = serialName
                self.serialConnection = serial.Serial(port=serialName)
        except SerialException:
            if self.serialName == None:
                self.serialName = "None"
            raise ZahnerConnectionError("could not open port: " + self.serialName) from None
        if self.isConnected() == False:
            if self.serialName == None:
                self.serialName = "None"
            raise ZahnerConnectionError("could not open port: " + self.serialName) from None 
        return
        
    def isConnected(self):
        """ Check if there is a connection to a serial interface.
        
        :returns: True if it is connected, else False.
        """
        if self.serialConnection != None:
            return self.serialConnection.is_open
        else:
            return False
    
    def write(self, data):
        """ Write to the serial interface.
        
        :param data: The data as bytearray().
        """
        if DEBUG:
            self.writeLog(data, "write")
        try:
            self.serialConnection.write(data)
        except SerialException:
            """
            Nothing can be sent to the device. The connection was probably interrupted and must be
            completely reestablished. So that everything is finished cleanly, close is called to
            terminate the threads.
            """
            self.close()
            raise ZahnerConnectionError("Connection to the device interrupted") from None
        return
                
    def close(self):
        """ Close the connection
        """
        self._stopTelegramListener()
        return
            
    def writeLog(self, data, direction):
        """ Write to the log.
        
        The time stamp is calculated automatically.
        
        :param data: The data as bytearray().
        :param direction: The direction as string.
        """
        if isinstance(data, bytearray) or isinstance(data, bytes):
            data = data.decode("ASCII")
        log = dict()
        log["time"] = datetime.now().time()
        log["direction"] = direction
        log["data"] = data.replace("\n", "")
        self.logData.append(log)
        return
            
    def getDebugString(self, withTime=False, direction=None):
        """ Read the log.
        This function is intended as debug output.
        To control what was sent when to the device and what the response was.
        
        :param withTime: Output of the time points. True means with time.
        :param direction: The direction as string, which one you want to read. None means all.
        """
        retval = ""
        for log in self.logData:
            if direction == None:
                if withTime == True:
                    retval += str(log["time"]) + " " 
                retval += log["direction"] + ":\t"
                retval += log["data"] + "\n"
            else:
                if log["direction"] == direction:
                    if withTime == True:
                        retval += str(log["time"]) + " " 
                    retval += log["data"] + "\n"
        return retval
    
    def getLastCommandWithAnswer(self, withTime=False, direction=None):
        retval = ""
        for log in self.logData[-2:]:
            if direction == None:
                if withTime == True:
                    retval += str(log["time"]) + " " 
                retval += log["direction"] + ":\t"
                retval += log["data"] + "\n"
            else:
                if log["direction"] == direction:
                    if withTime == True:
                        retval += str(log["time"]) + " " 
                    retval += log["data"] + "\n"
        return retval
        
    
    def _startTelegramListener(self):
        """ Private method which starts the receive thread.
        """
        self._receiving_worker_is_running = True
        self.receivingWorker = threading.Thread(target=self._telegramListenerJob)
        self.receivingWorker.start()
        return
        
    def _stopTelegramListener(self):
        """ Private method which stopps the receive thread.
        """
        try:
            """
            It could be that the connection has already been closed and the receiving thread has
            been terminated. Then an exception is thrown here when trying to close again or to
            interrupt the operations.
            """
            self._receiving_worker_is_running = False
            time.sleep(0.1)
            self.serialConnection.cancel_read()
            self.serialConnection.cancel_write()
            self.serialConnection.close()
        except:
            pass
        finally:
            self.receivingWorker.join()
        return
    
    @abstractmethod
    def _telegramListenerJob(self):
        """
        Private method which is called as receive thread.
        This must be implemented by the class that implements the abstract base class.

        In the function must be stayed until _receiving_worker_is_running is False.
        """
        pass


class SerialCommandInterface(SerialInterface):
    """
    Class which implements the command interface.
    
    :param serialName: Name of the serial interface.
    """

    def __init__(self, serialName):
        """ Constructor
        
        """
        self.waiting = dict()
        self.waiting[CommandType.COMMAND.value] = None
        self.waiting[CommandType.CONTROL.value] = None
        
        self.queues = dict()
        self.queues[CommandType.COMMAND.value] = queue.SimpleQueue()
        self.queues[CommandType.CONTROL.value] = queue.SimpleQueue()
        
        super().__init__(serialName)
        return
            
    def waitForReplyString(self, commandType, timeout = None):
        """ Waiting for the reply string.
        
        :param commandType: Type of the command.
        :param timeout: The timeout for reading, None for blocking.
        :type commandType: :class:`~zahner_potentiostat.scpi_control.serial_interface.CommandType`
        :returns: The answer string.
        """
        reply = self.queues[commandType.value].get(True, timeout=timeout)
        if reply == None:
            raise ZahnerConnectionError("Connection to the device interrupted")
        return reply
      
    def sendStringAndWaitForReplyString(self, string, commandType=CommandType.COMMAND):
        """ Sending a string and waiting for the response.
        
        :param string: The string to send.
        :param timeout: The timeout for reading, None for blocking.
        :type commandType: :class:`~zahner_potentiostat.scpi_control.serial_interface.CommandType`
        :returns: The answer string.
        """
        command = bytearray(string + '\n', 'ASCII')
        self.waiting[commandType.value] = command
        self.write(command)
        reply = self.waitForReplyString(commandType)
        return reply
    
    def _telegramListenerJob(self):
        """ Method in which the receive thread runs.
        
        More doku is in the function.
        """
        while self._receiving_worker_is_running:
            try:
                line = self.serialConnection.readline()
                """
                If the connection is terminated and the blocking read is interrupted,
                then an empty string is returned.
                """
                            
                if DEBUG:
                    self.writeLog(line, "read")
                    
                line = line.decode("ASCII")
                
                if line == "":
                    self._receiving_worker_is_running = False
                else:
                    """
                    There are only the two possibilities:
                    CommandType.CONTROL
                    CommandType.COMMAND
                    
                    The commands ABOR and *RST are executed immediately and parallel to the other commands,
                    with a higher priority. Therefore it is possible that several responses can come in
                    unknown order from two threads.
                    ABOR and *RST are always answered with ok.
                    The command which was aborted returns a corresponding status.
                    But if the command was terminated before the ABOR was processed then also two ok can be returned.
                    """
                    waitingKeys = []
                    for key in self.waiting.keys():
                        if self.waiting[key] != None:
                            waitingKeys.append(key)
                    
                    if len(waitingKeys) > 1:
                        """
                        Two are waiting for an answer, so two lines must be received to decide who gets which.
                        ABORT and RESET always get the ok.
                        """
                        line2 = self.serialConnection.readline()
                        if DEBUG:
                            self.writeLog(line2, "read")
                            
                        line2 = line2.decode("ASCII")
                            
                        if "ok" in line and "ok" in line2:
                            for key in waitingKeys:
                                self.queues[key].put("ok")
                        elif "ok" in line:
                            self.queues[CommandType.CONTROL.value].put(line)
                            self.queues[CommandType.COMMAND.value].put(line2)
                        elif "ok" in line2:
                            self.queues[CommandType.CONTROL.value].put(line2)
                            self.queues[CommandType.COMMAND.value].put(line)
                        else:
                            raise ValueError("Unexpected error: line;line2 " + line + " ; " + line2)
                        for key in self.waiting.keys():
                            self.waiting[key] = None          
                    elif len(waitingKeys) == 1:
                        self.queues[waitingKeys[0]].put(line)
                        self.waiting[waitingKeys[0]] = None
                    else:
                        raise ValueError("Nothing sent, which includes the answer: " + line)
            except (SerialException, TypeError):
                self._receiving_worker_is_running = False
        
        if self._receiving_worker_is_running is False:
            waitingKeys = []
            for key in self.waiting.keys():
                if self.waiting[key] != None:
                    waitingKeys.append(key)
            for key in waitingKeys:
                self.queues[key].put(None)
                self.waiting[key] = None
        return
        
        
class SerialDataInterface(SerialInterface):
    """
    Class which implements the data interface.
    
    :param serialName: Name of the serial interface.
    """

    def __init__(self, serialName):
        """ Constructor
        """
        self.queue = queue.SimpleQueue()
        super().__init__(serialName)
        return
        
    def _telegramListenerJob(self):
        """ Method in which the receive thread runs.
        """
        while self._receiving_worker_is_running:
            try:
                receivedBytes = self.serialConnection.read_all()
                               
                for byte in receivedBytes:
                    self.queue.put(byte)
            except:
                self._receiving_worker_is_running = False
        
        if self._receiving_worker_is_running is False:
            """
            Push a None into the queue to free waiting threads.
            """
            self.queue.put(None)
        return
        
    def availableBytes(self):
        """ Returns the available bytes.
        
        :returns: The available bytes.
        """
        return self.queue.qsize()
    
    def readBytes(self, numberOfBytes, timeout=None):
        """ Read bytesRead from the interface.
        
        :param numberOfBytes: The number of bytesRead to read.
        :param timeout: The timeout for reading, None for blocking.
        :returns: The bytesRead read.
        :rtype: bytearray
        """
        bytesRead = bytearray()
        for i in range(numberOfBytes):
            byte = self.queue.get(block=True, timeout=timeout)
            if byte != None:
                """
                A None is received when the receiving thread is terminated.
                """
                bytesRead.append(byte)
            else:
                break
        return bytesRead
            
            
