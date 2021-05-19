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

from .dcplot import DCPlot
from zahner_potentiostat.scpi_control.datareceiver import TrackTypes
import multiprocessing
import threading
import time


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
            if self._display.isOpen() == False:
                self.terminate()
                return
            
            if self._pipe.poll() == False:
                self._display.pause(0.04)
            else:
                command = self._pipe.recv()
                if command is None:
                    self.terminate()
                    return
                else:
                    self._display.clearData()
                    self._display.addData(command[0], command[1])

    def __call__(self, pipe):
        """ Call method implementation.
        
        Initialization and call of the main loop of the process in which the data is processed and plotted.
        
        :param pipe: multiprocessing.Pipe() object from the process.
        """
        self._pipe = pipe
        self._display = DCPlot("Online Display", "Time", "s", [{"label": "Voltage", "unit": "V"}, {"label": "Current", "unit": "A"}])
        
        self.processingLoop()


class OnlineDisplay(object):
    """
    Online display class, which allows to display live the measurement data over time while the
    measurement is taking place.
    
    This class sends the data to the plotting process, which is then displayed by the other process.
    
    This class is passed the :class:`~zahner_potentiostat.scpi_control.datareceiver.DataReceiver` object of the measuring device, then after calling the
    constructor all data from the measuring device are displayed live.

    The other possibility is to pass the data with the variable data. Then the data must be passed
    as you can read in the documentation of :func:`~zahner_potentiostat.display.dcplot.DCPlot.addData`.
    
    :param dataReceiver: Receiver object.
    :type dataReceiver: :class:`~zahner_potentiostat.scpi_control.datareceiver.DataReceiver`
    :param data: Packed into an array: [xData, yDatas]
    """

    def __init__(self, dataReceiver, data=None):
        self._dataReveiver = dataReceiver
        self._numberOfPoints = 0
        self._processingLoopRunning = True
        self.plot_pipe, plotter_pipe = multiprocessing.Pipe()
        self.plotter = PlottingProcess()
        self.plot_process = multiprocessing.Process(
            target=self.plotter, args=(plotter_pipe,), daemon=True)
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
        
    def processingLoop(self):
        """ Measurement data processing thread.
        
        This thread reads from the DataReceiver object. If there is new data, all points are sent to
        the PlottingProcess, which then plots the data.
        """
        lastNumberOfPoints = 0
        while self._processingLoopRunning == True:
            number = self._dataReveiver.getNumberOfCompleteAndOnlinePoints()
            if lastNumberOfPoints != number:
                lastNumberOfPoints = number
                
                if number > 0:
                    data = self._dataReveiver.getCompleteAndOnlinePoints()
                    self._sendDataToProcess(data)
                    
            else:
                time.sleep(0.02)
        return
    
    def _sendDataToProcess(self, data):
        """ Sending data to the process via the pipe.
        
        This method reads the data from the DataReceiver object and assembles it so that it can be
        sent to the PlottingProcess.
        
        :param data: The data to plot. data = [xData, yDatas]. Like :func:`~zahner_potentiostat.display.dcplot.DCPlot.addData`.
        """
        x = data[TrackTypes.TIME.toString()]
        y1 = data[TrackTypes.VOLTAGE.toString()]
        y2 = data[TrackTypes.CURRENT.toString()]
        
        if self.plot_pipe.closed:
            self._processingLoopRunning = False
        else:
            try:
                self.plot_pipe.send([x, [y1, y2]])
            except:
                self._processingLoopRunning = False
        return
            
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
  
