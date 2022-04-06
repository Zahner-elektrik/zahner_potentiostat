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

from .dcplot import DCPlot
from zahner_potentiostat.scpi_control.datareceiver import TrackTypes
import multiprocessing
import threading
import time
from enum import Enum


class OnlineDisplayStatus(Enum):
    """ Online Display Status
    """
    RENDERED = 0
    CLOSED = 1

class OnlineDisplayJob(Enum):
    """ Online Display Status
    """
    APPEND = 0
    CLEAR = 1

class PlottingProcess:
    """ Auxiliary class for displaying the plotting window.
    
    By default, the program waits until the plotting window is closed.
    As long as they are not closed, they have computing time and can be interacted with.

    However, if the plotting window is called as an online display, then it only gets computing time
    when the display pause is called. Also the plotting must always take place in the main thread.
    
    Therefore this class comes in a new process, in which only plotting is done, so you can always
    interact with the live display and it doesn't freeze.
    """
    def __init__(self):
        """ Constructor
        """
        self._pipe = None
        self._display = None
        
    def terminate(self):
        """ Close
        """
        self._display.close()

    def processingLoop(self):
        """ Main process loop.
        
        This is the main loop and will continue until None is sent to the process or the display is closed.
        The data is sent to the process with a process pipeline.
        """
        while True:
            try:
                if self._display.isOpen() == False:
                    self._pipe.send(OnlineDisplayStatus.CLOSED.value)
                    self.terminate()
                    return
            
                if self._pipe.poll() == False:
                    self._display.pause(0.04)
                else:
                    command = self._pipe.recv()
                    if command is None:
                        self.terminate()
                        return
                    elif command["job"] == OnlineDisplayJob.APPEND.value :
                        self._display.addData(command["data"][0], command["data"][1])
                    elif command["job"] == OnlineDisplayJob.CLEAR.value :
                        self._display.clearPlot()
                    self._pipe.send(OnlineDisplayStatus.RENDERED.value)
            except Exception as e:
                raise e
                print("Error online display receiver.")
                print(f"Exception message: {e}")
                self.terminate()
                return

    def __call__(self, pipe, displayConfiguration):
        """ Call method implementation.
        
        Initialization and call of the main loop of the process in which the data is processed and plotted.
        
        :param pipe: multiprocessing.Pipe() object from the process.
        """
        self._pipe = pipe
        self._display = DCPlot(**displayConfiguration)
        
        self.processingLoop()


class OnlineDisplay(object):
    """
    Online display class, which allows to display live the measurement data while the
    measurement is taking place.
    
    This class sends the data to the plotting process, which is then displayed by the other process.
    
    This class is passed the :class:`~zahner_potentiostat.scpi_control.datareceiver.DataReceiver` object of the measuring device, then after calling the
    constructor all data from the measuring device are displayed live.

    The other possibility is to pass the data with the variable data. Then the data must be passed
    as you can read in the documentation of :func:`~zahner_potentiostat.display.dcplot.DCPlot.addData`.
    
    By default, the X axis is time and current and voltage are each displayed on a Y axis.
    
    The variable displayConfiguration can be used to change the display format.
    With this variable either two default settings can be selected, or everything can be set individually.
    
    displayConfiguration="UI": X-axis voltage, Y-axis current.
    displayConfiguration="UlogI": X-axis voltage, Y-axis magnitude of current logarithmically scaled.
    
    Instead of the default diagram presets, the axis labeling and the data type can also be changed individually
    by passing a dictionary. All parameters from the two following examples must be passed.
    With x/yTrackName the name of the data track is passed, which is to be displayed on the axis.
    
    .. code-block:: python
        
        displayConfiguration = {
            "figureTitle":"My Custom Online Display",
            "xAxisLabel":"Time",
            "xAxisUnit":"s",
            "xTrackName":TrackTypes.TIME.toString(),
            "yAxis":[
            {"label": "Cell Potential", "unit": "V", "trackName":TrackTypes.VOLTAGE.toString()},
            {"label": "Cell Current", "unit": "A", "trackName":TrackTypes.CURRENT.toString()}
            ]}
    
    or
    
    .. code-block:: python
        
        displayConfiguration = {
            "figureTitle":"Online Display",
            "xAxisLabel":"Potential",
            "xAxisUnit":"V",
            "xTrackName":TrackTypes.VOLTAGE.toString(),
            "yAxis":[
            {"label": "Current", "unit": "A", "name": "Current", "log": True, "trackName":TrackTypes.CURRENT.toString()}
            ]}
    

    
    :param dataReceiver: Receiver object.
    :type dataReceiver: :class:`~zahner_potentiostat.scpi_control.datareceiver.DataReceiver`
    :param data: Packed into an array: [xData, yDatas]
    :param displayConfiguration: Default value None for TIU diagrams. A dict or string as explained
        in the previous text for other representations.
    """
    def __init__(self, dataReceiver, data=None, displayConfiguration=None):
        self._dataReveiver = dataReceiver
        self._numberOfPoints = 0
        self._processingLoopRunning = True
        self.xTrackName = None
        self.yTrackNames = []
        self.minSendInterval = 0.1
        self.lastOnlineMinTimeStamp = 0
        self.lastOnlineMaxTimeStamp = 0
        
        configuration = {"figureTitle":"Online Display",
                         "xAxisLabel":"Time",
                         "xAxisUnit":"s",
                         "xTrackName":TrackTypes.TIME.toString(),
                         "yAxis":
        [{"label": "Voltage", "unit": "V", "trackName":TrackTypes.VOLTAGE.toString()},
         {"label": "Current", "unit": "A", "trackName":TrackTypes.CURRENT.toString()}]
        }
        
        if isinstance(displayConfiguration, dict):
            self.xTrackName = configuration["xTrackName"]
            for yAxis in configuration["yAxis"]:
                self.yTrackNames.append(yAxis["trackName"])
            configuration = displayConfiguration
        elif isinstance(displayConfiguration, str):
            if "UI" == displayConfiguration:
                self.xTrackName = TrackTypes.VOLTAGE.toString()
                self.yTrackNames = [TrackTypes.CURRENT.toString()]
                configuration = {"figureTitle":"Online Display", "xAxisLabel":"Voltage", "xAxisUnit":"V", "yAxis":[{"label": "Current", "unit": "A", "name": "Current", "log": False}]}
            elif "UlogI" == displayConfiguration:
                self.xTrackName = TrackTypes.VOLTAGE.toString()
                self.yTrackNames = [TrackTypes.CURRENT.toString()]
                configuration = {"figureTitle":"Online Display", "xAxisLabel":"Voltage", "xAxisUnit":"V", "yAxis":[{"label": "Current", "unit": "A", "name": "Current", "log": True}]}
        else:
            self.xTrackName = configuration["xTrackName"]
            for yAxis in configuration["yAxis"]:
                self.yTrackNames.append(yAxis["trackName"])
            
        
        self.plot_pipe, plotter_pipe = multiprocessing.Pipe()
        self.plotter = PlottingProcess()
        self.plot_process = multiprocessing.Process(
            target=self.plotter, args=(plotter_pipe,configuration,), daemon=True)
        self.plot_process.start()
        
        if data == None:
            self._dataProcessingThreadHandle = threading.Thread(target=self.processingLoop)
            self._dataProcessingThreadHandle.start()
        else:
            self._sendDataToProcess(data)
        return
        
    def stopProcessingLoop(self):
        """
        This function must be called by another thread which tells the processing loop
        to stop the loop to process online data. Because of the Matplotlib syntax,
        the plot window will then also be closed, but then the complete data can be displayed.
        """
        self._processingLoopRunning = False
        return
    
    def setMinimumSendInterval(self, interval):
        """ Set the minimum interval for sending data.
        
        Only after this time is it checked again whether data can be sent to the online display.
        
        :param interval: Time in s.
        """
        self.minSendInterval = interval
        return
        
    def processingLoop(self):
        """ Measurement data processing thread.
        
        This thread reads from the DataReceiver object. If there is new data, all points are sent to
        the PlottingProcess, which then plots the data.
        """
        lastNumberOfPoints = 0
        while self._processingLoopRunning == True:
            
            number = self._dataReveiver.getNumberOfOnlinePoints()
            
            if lastNumberOfPoints != number:
                lastNumberOfPoints = number
                
                if number > 0:
                    data = self._dataReveiver.getOnlinePoints()
                    
                    try:
                        if not self.plot_pipe.closed:
                            if self._replyFromProcessAvailable():
                                #delete old replys
                                reply = self._waitForReplyFromProcess()
                                if reply is OnlineDisplayStatus.CLOSED.value:
                                    print("Online display closed.")
                                    self._processingLoopRunning = False
                                    return
                            
                            minTime = min(data[TrackTypes.TIME.toString()])
                            maxTime = max(data[TrackTypes.TIME.toString()])
                            
                            if maxTime <= self.lastOnlineMaxTimeStamp:
                                # delete online display data
                                self._sendDataToProcess(OnlineDisplayJob.CLEAR.value)
                                reply = self._waitForReplyFromProcess()
                                if reply is not OnlineDisplayStatus.RENDERED.value:
                                    print("Error online display answer.")
                                    self._processingLoopRunning = False
                                    return
                            else:
                                # remove already existing data
                                dataFromIndex = next(x[0] for x in enumerate(data[TrackTypes.TIME.toString()]) if x[1] > self.lastOnlineMaxTimeStamp)
                                for key in data.keys():
                                    data[key] = data[key][dataFromIndex:]
                            
                            self._sendDataToProcess(OnlineDisplayJob.APPEND.value, data)
                            reply = self._waitForReplyFromProcess()
                            
                            if reply is not OnlineDisplayStatus.RENDERED.value:
                                print("Error online display answer.")
                                self._processingLoopRunning = False
                                return
                                                       
                            self.lastOnlineMinTimeStamp = minTime
                            self.lastOnlineMaxTimeStamp = maxTime
                        else:
                            self._processingLoopRunning = False                                                        
                                
                    except Exception as e:
                        print("Error online display transmitter.")
                        print(f"Exception message: {e}")
                        self._processingLoopRunning = False
                        return
                    
                    time.sleep(self.minSendInterval)
                    
            else:
                time.sleep(self.minSendInterval)
        return
    
    def _sendDataToProcess(self, job, data = None):
        """ Sending data to the process via the pipe.
        
        This method reads the data from the DataReceiver object and assembles it so that it can be
        sent to the PlottingProcess.
        
        :param data: The data to plot. data = [xData, yDatas]. Like :func:`~zahner_potentiostat.display.dcplot.DCPlot.addData`.
        """
        if data is None:
            self.plot_pipe.send({"job" : job, "data" : data})
        else:
            self.plot_pipe.send({"job" : job, "data" : [data[self.xTrackName], [data[y] for y in self.yTrackNames]]})
        return
    
    def _waitForReplyFromProcess(self):
        return self.plot_pipe.recv()
    
    def _replyFromProcessAvailable(self):
        return self.plot_pipe.poll()
            
    def close(self):
        """ Close the online display.
        """
        self.stopProcessingLoop()
        if self.plot_pipe.closed == False:
            try:
                self.plot_pipe.send(None)
            except:
                pass
        return
  
