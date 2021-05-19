'''
  ____       __                        __    __   __      _ __
 /_  / ___ _/ /  ___  ___ ___________ / /__ / /__/ /_____(_) /__
  / /_/ _ `/ _ \/ _ \/ -_) __/___/ -_) / -_)  '_/ __/ __/ /  '_/
 /___/\_,_/_//_/_//_/\__/_/      \__/_/\__/_/\_\\__/_/ /_/_/\_\

Copyright 2021 ZAHNER-elektrik I. Zahner-Schiller GmbH & Co. KG

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

import struct
from threading import Thread, Semaphore
from .error import ZahnerDataProtocolError
from enum import Enum


class PacketTypes(Enum):
    """ Enumeration with the numbers of the different package types.
    """
    DATALIGHT = 0xFEEDDA7A22222222
    DATALIGHTBULK = 0xFEEDDA7A44444444
    DATALIGHTBULKAPPENDUM = 0xFEEDDA7A77777777
    MEASUREMENTHEADER = 0xB007F00D11111111
    MEASUREMENTTRACKS = 0xADDDF00D11111111

class MeasurementTypes(Enum):
    """ Enumeration with known standard measurements.
    """
    IE = 5
    TIU = 21
    
class HeaderState(Enum):
    """ Enumeration with status numbers of the header.
    """
    PENDING = 0
    START = 1
    RUNNING = 2
    DONE = 3
    FINISHING = 4
    ABORTED = 5
    CANCELLED = 6


class TrackTypes(Enum):
    """ Enumeration with the different types for the data tracks.
    """
    TIME = 13
    CURRENT = 12
    VOLTAGE = 11
    
    @classmethod
    def numberToTrack(cls, number):
        """ Convert a number to the TrackType.
        
        :param number: The number of the Track.
        :returns: The specific Track as TrackTypes Type.        
        """
        if number == TrackTypes.TIME.value:
            return TrackTypes.TIME
        elif number == TrackTypes.CURRENT.value:
            return TrackTypes.CURRENT
        elif number == TrackTypes.VOLTAGE.value:
            return TrackTypes.VOLTAGE
        else:
            raise ValueError("Unknown Track")
        
    @classmethod
    def stringToTrack(cls, string):
        """ Convert a string to the TrackType.
        
        :param string: The Track as string of the Track.
        :returns: The specific Track as TrackTypes Type.        
        """
        for name, member in __class__.__members__.items():
            if name in string:
                return member
        raise ValueError()
            
    def __str__(self):
        """ Overwrite the string representation of the object.
        
        :returns: The TrackTypes Type as String.
        """
        classname = str(__class__)
        split = classname.split("'")
        classname = split[1]
        return classname + "." + self.name
    
    def toString(self):
        """ Convert the TrackTypes Type to a String.
        
        :returns: The TrackTypes Type as String.
        """
        return self.__str__()


class DataReceiver:
    """
    Class which receives the measurement data from the device.
    
    The device tries to send the data during the measurement, but if not all measurement points
    could be sent live, they are sent afterwards and then sorted into the live measurement points.
    Live data and online data means the same.

    If several primitives are measured one after the other, the date will be appended further and
    further to the old data. The primitives always start again at time 0 but at this time there is
    no measurement result yet. Only at the time 0 plus sampling period there is the first measuring point.

    This class recalculates the time axis if the primitives were measured one after the other.
    The dead time at the end of the measurement if complete data must be transmitted is not visible
    in the time axis, since here is not measured.

    The complete protocol documentation is available on request.
    This implementation is sufficient for normal operation.
    
    The examples and the example online display are the easiest way to learn how to use this class
    to get the data from the measuring device. Examples are in datahandler.py. There the data are
    read from the object.
    
    The following is an example of the data structure: 
    {":class:`~zahner_potentiostat.scpi_control.datareceiver.TrackTypes`.TIME" : [1, 2, 3, 4] , ":class:`~zahner_potentiostat.scpi_control.datareceiver.TrackTypes`.VOLTAGE" : [3, 2, 3, 4] , ":class:`~zahner_potentiostat.scpi_control.datareceiver.TrackTypes`.CURRENT" : [0, 2, 3, 0]}
    
    :param dataInterface: Data interface to the device.   
    :type dataInterface: :class:`~zahner_potentiostat.scpi_control.serial_interface.SerialDataInterface`
    """
    def __init__(self, dataInterface):
        """ Constructor
                    
        """
        self._dataInterface = dataInterface
        self._completeData = []
        self._onlineData = []
        self._currentTrackTypes = []
        self._lastHeaderSate = None
        self._lastPacketType = None
        self._maximumTimeInCycle = 0
        self._lastMaximumTime = 0
        self._receiveThreadHandler = Thread(target=self._receiveDataThread)
        self._receiving_worker_is_running = True
        self._receiveThreadHandler.start()
        self._completeDataSemaphore = Semaphore(1)
        self._onlineDataSemaphore = Semaphore(1)
    
    def stop(self):
        """ Stop the data receiver and close.
        
        This method stops the internal threads and closes the interface.
        """
        self._receiving_worker_is_running = False
        self._dataInterface.close()
        self._receiveThreadHandler.join()
        return
        
    def getNumberOfCompleteAndOnlinePoints(self):
        """ Get the number of received points.
        
        Returns the number of measurement points which are complete and which were received live.
        After the end of a primitive, live data becomes complete data.
        
        :returns: Number of measurement points.
        """
        return self.getNumberOfCompletePoints() + self.getNumberOfOnlinePoints()
    
    def getNumberOfCompletePoints(self):
        """ Get the number of received complete data.
        
        Returns the number of measurement points which are complete. Thus completed finished primitive.
        After the end of a primitive, live data becomes complete data.
        
        :returns: Number of measurement points.
        """
        return len(self._completeData)
    
    def getNumberOfOnlinePoints(self):
        """ Get the number of received live points.
        
        Returns the number of measurement points which are complete and which were received live.
        After the end of a primitive, live data becomes complete data.
        
        :returns: Number of measurement points.
        """
        return len(self._onlineData)
    
    def getTrackTypeList(self):
        """ List of track types that are currently being processed.
        
        At the moment with the PP2x2 and XPOT2 devices there is only voltage, current and time.
        
        :returns: Number of measurement points.
        """
        return self._currentTrackTypes
    
    def getCompleteTrack(self, track , minIndex=0, maxIndex=None):
        """ Retrieves points to a completed data track.
        
        :param track: Track as string, number or TrackTypes.
        :param minIndex: By default 0, this means from 0.
        :param maxIndex: By default 0, this means to the end.
        :returns: An array with the data for the track. Each returned data point consists of a
            dictionary with the track names.
        """
        retval = []
        key = None
        if isinstance(track, TrackTypes):
            key = track.value
        elif isinstance(track, int):
            key = TrackTypes.numberToTrack(track).toString()
        else:
            key = track
        
            if maxIndex == None:
                maxIndex = self.getNumberOfCompletePoints()
            for i in range(minIndex, maxIndex, 1):
                pointDict = self._completeData[i]
                retval.append(pointDict[key])
        return retval
    
    def getOnlineTrack(self, track , minIndex=0, maxIndex=None):
        """ Retrieves points to a online/live data track.
        
        :param track: Track as string, number or TrackTypes.
        :param minIndex: By default 0, this means from 0.
        :param maxIndex: By default 0, this means to the end.
        :returns: An array with the data for the track. Each returned data point consists of a
            dictionary with the track names.
        """
        retval = []
        key = None
        if isinstance(track, TrackTypes):
            key = track.value
        elif isinstance(track, int):
            key = TrackTypes.numberToTrack(track).toString()
        else:
            key = track
        if maxIndex == None:
            maxIndex = self.getNumberOfCompletePoints()
        for i in range(minIndex, maxIndex, 1):
            pointDict = self._onlineData[i]
            retval.append(pointDict[key])
        return retval
    
    def getCompletePoints(self, minIndex=0, maxIndex=None):
        """ Retrieves points to all data tracks for completed data.
        
        :param minIndex: By default 0, this means from 0.
        :param maxIndex: By default 0, this means to the end.
        :returns: An array with the data for the track. Each returned data point consists of a
            dictionary with the track names.
        """
        retval = dict()
        with self._completeDataSemaphore:
            if maxIndex == None:
                maxIndex = self.getNumberOfCompletePoints()
            for track in self._currentTrackTypes:
                data = self.getCompleteTrack(track, minIndex, maxIndex)
                retval[track] = data
        return retval
    
    def getOnlinePoints(self, minIndex=0, maxIndex=None):
        """ Retrieves points to all data tracks for online/live data.
        
        :param minIndex: By default 0, this means from 0.
        :param maxIndex: By default 0, this means to the end.
        :returns: An array with the data for the track. Each returned data point consists of a
            dictionary with the track names.
        """
        retval = dict()
        with self._onlineDataSemaphore:
            if maxIndex == None:
                maxIndex = self.getNumberOfOnlinePoints()
            for track in self._currentTrackTypes:
                data = self.getOnlineTrack(track, minIndex, maxIndex)
                retval[track] = data
        return retval
    
    def getCompleteAndOnlinePoints(self):
        """ Retrieves points to all data tracks for completed and online data.
        
        :returns: An array with the data for the track. Each returned data point consists of a
            dictionary with the track names.
        """
        complete = self.getCompletePoints()
        online = self.getOnlinePoints()
        for key in complete.keys():
            dataFromKey = online[key]
            for data in dataFromKey:
                complete[key].append(data)
        return complete
    
    def deletePoints(self):
        """ Delete the received complete points.
        """
        with self._completeDataSemaphore:
            self._completeData = []
            self._lastMaximumTime = 0
        return
    
    """
    Private internally required functions that process the data stream.
    These do not have to be used or accessed by the user.
    """
    
    def _receiveDataThread(self):
        """ Receive thread which calls the individual decoders for the different packets.
        """
        packetError = False
        while self._receiving_worker_is_running == True:
            try:
                packetType = self._readU64()
                length = self._readU64()
                
                if packetType == PacketTypes.DATALIGHT.value:
                    self._processDataLight(length)
                elif packetType == PacketTypes.DATALIGHTBULK.value:
                    self._processDataLightBulk(length)
                elif packetType == PacketTypes.DATALIGHTBULKAPPENDUM.value:
                    self._processDataLightBulkAppendum(length)
                elif packetType == PacketTypes.MEASUREMENTHEADER.value:
                    self._processMeasurementHeader(length)
                elif packetType == PacketTypes.MEASUREMENTTRACKS.value:
                    self._processMeasurementTracks(length)
                else:
                    packetError = True
                self._lastPacketType = packetType
            except:
                self._receiving_worker_is_running = False
            if packetError:
                raise ZahnerDataProtocolError("Unknown Packet: " + str(packetType))
        return
                
    def _processDataLight(self, length):
        """ Process packet type DataLight
        """
        numberOfTracks = length / 8
        
        if numberOfTracks == len(self._currentTrackTypes):
            dataPacket = dict()
            for track in self._currentTrackTypes:
                dataPacket[track] = self._readF64()
                
            if TrackTypes.TIME.toString() in dataPacket.keys():
                """
                Correction of the time axis for successive primitives,
                so that time continues to run and does not start at 0 for each primitive.
                """
                time = dataPacket[TrackTypes.TIME.toString()]
                if time > self._maximumTimeInCycle:
                    self._maximumTimeInCycle = time
                dataPacket[TrackTypes.TIME.toString()] += self._lastMaximumTime
            else:
                raise ZahnerDataProtocolError("No Time track")
            self._onlineData.append(dataPacket)
        else:
            raise ZahnerDataProtocolError("numberOfTracks != len(self._currentTrackTypes)")
        return
    
    def _processDataLightBulk(self, length):
        """ Process packet type DataLightBulk
        """
        length -= 8  #startindex
        startIndex = self._readU64()
        
        numberOfPackets = length / (len(self._currentTrackTypes) * 8)
        
        if numberOfPackets.is_integer() == False:
            raise ZahnerDataProtocolError("numberOfPackets for Bulk not correct")
        else:
            numberOfPackets = int(numberOfPackets)
        
        """
        Bulk data at the end of the measurement.
        Delete all online data, then receive the complete data in the online data
        Then transfer the online data to the complete data.
        """
        
        self._clearOnlineData()
        
        for i in range(numberOfPackets):
            self._processDataLight(len(self._currentTrackTypes) * 8)
            
        self._onlineDataToCompleteData()
        return
    
    def _sortOnlineDataByTrack(self, trackType):
        """ Sort the online data.
        
        Sorting the data according to one of the data tracks.
        
        :param trackType:
        :type trackType: :class:`~zahner_potentiostat.scpi_control.datareceiver.TrackTypes`
        """
        self._onlineData = sorted(self._onlineData, key=lambda datapoint : datapoint[trackType])
    
    def _processDataLightBulkAppendum(self, length):
        """ Process packet type DataLightBulkAppendum.
        
        This data must then be sorted into the online data.
        """
        length -= 8  #startindex
        trackType = self._readU64()
        trackType = TrackTypes.numberToTrack(trackType)
        
        numberOfPackets = length / (len(self._currentTrackTypes) * 8)
        
        if numberOfPackets.is_integer() == False:
            raise ZahnerDataProtocolError("numberOfPackets for Bulk appendum not correct")
        else:
            numberOfPackets = int(numberOfPackets)
        
        for i in range(numberOfPackets):
            self._processDataLight(len(self._currentTrackTypes) * 8)
            
        self._sortOnlineDataByTrack(trackType.toString())
        
        self._onlineDataToCompleteData()
        return
    
    def _processMeasurementHeader(self, length):
        """ Process packet type MeasurementHeader
        """
        measurementType = self._readU64()
        measurementState = self._readU64()
        measurementFlags = self._readString()
        measurementName = self._readString()
        
        if measurementState == HeaderState.FINISHING.value:
            if self._lastPacketType == PacketTypes.MEASUREMENTHEADER.value and self._lastHeaderSate == HeaderState.DONE.value:
                self._onlineDataToCompleteData()
        else:
            """
            Not yet needed at the moment.
            """
            pass
        self._lastHeaderSate = measurementState
        return
    
    def _processMeasurementTracks(self, length):
        """ Process packet type MeasurementTracks
        """
        numberOfTracks = self._readU64()
        self._currentTrackTypes = []
        
        for i in range(numberOfTracks):
            trackType = self._readU64()
            name = self._readString()
            unit = self._readString()
            flags = self._readString()
            
            self._currentTrackTypes.append(TrackTypes.numberToTrack(trackType).toString())
        return
        
    def _readU64(self):
        """ Read unsigned 64 bit integer from the interface.
        
        :returns: The read value.
        """
        data = self._dataInterface.readBytes(8)
        return struct.unpack('Q', data[0:8])[0]
    
    def _readF64(self):
        """ Read 64 bit floating point from the interface.
        
        :returns: The read value.
        """
        data = self._dataInterface.readBytes(8)
        return struct.unpack('d', data[0:8])[0]
    
    def _readString(self):
        """ Read a string from the interface.
        
        :returns: The read string.
        """
        continueRead = True
        data = bytearray()
        while continueRead == True:
            byte = self._dataInterface.readBytes(1)
            if byte.decode("ASCII") == '\0':
                continueRead = False
            data.append(byte[0])
        
        return data.decode("ASCII")
    
    def _clearOnlineData(self):
        """ Clear the received online data.
        """
        with self._onlineDataSemaphore:
            self._onlineData = []
        return
        
    def _onlineDataToCompleteData(self):
        """ Transfer online to complete data.
        """
        with self._completeDataSemaphore:
            for data in self._onlineData:
                self._completeData.append(data)
            self._clearOnlineData()
            self._lastMaximumTime += self._maximumTimeInCycle
            self._maximumTimeInCycle = 0
        return
        
