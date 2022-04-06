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

from zahner_potentiostat.display.dcplot import DCPlot
from .datareceiver import TrackTypes

class DataManager:
    """
    Example class that shows how to get the data from the object structure and use it further.
    
    This is not a ready-made optimization, just a simple example that needs to be adapted to your own use case.
    
    In the future, methods will be added to save the data in Zahner formats, which Zahner Analysis can then open.
    
    :param dataReceiver: DataReceiver object with data from device.
    :type dataReceiver: :class:`~zahner_potentiostat.scpi_control.datareceiver.DataReceiver`
    """
    def __init__(self, dataReceiver):
        self._receiver = dataReceiver
        
    def plotTIUData(self, filename=None, width=None, height=None):
        """ Plot data example.
        
        This is an example to plot the data after the measurement. For plotting the data matplotlib
        is used. For this purpose a simple class DCPlot was implemented, with which current and
        voltage can be plotted over time.
        
        If nothing is passed, only a window is opened and the data is plotted. If a filename is
        passed, the plot is saved under the filename. The documentation for saving must be taken
        from the documentation of savePlot().
        
        :param filename: The path, filename and filetype of the file if it should be saved,
            else None.  
        :param width: The width of the file to save in inch, 
        :param height: The height of the file to save in inch.
        """
        data = self._receiver.getCompletePoints()
        x = data[TrackTypes.TIME.toString()]
        y1 = data[TrackTypes.VOLTAGE.toString()]
        y2 = data[TrackTypes.CURRENT.toString()]
         
        display = DCPlot("Measured Data", "Time", "s", [{"label": "Voltage", "unit": "V", "name": "Voltage"}, {"label": "Current", "unit": "A", "name": "Current"}],[x, [y1, y2]])
         
        if filename != None:
            display.savePlot(filename, width, height)
        return
        
    def saveDataAsText(self, filename):
        """ Save data example.
        
        This is an example to save the data after the measurement.
        
        The data is stored with the standard python decimal separator. As separator ; and a tabulator
        is used, so the file is easily readable. It is deliberately not used a "," as column separator,
        because this is for example in Germany the decimal separator.
        
        It is only an example that needs to be adapted, Zahner does not want to implement all the
        different localizations in order to be able to open the csv file in all countries with Excel,
        for example. Since this repository is actually only a programming interface to the devices.
        
        In the future, methods will be added to save the data in Zahner formats, which Zahner Analysis can then open.
        
        :param filename: The path, filename and filetype of the file if it should be saved.
        """
        data = self._receiver.getCompletePoints()
        
        timeKey = TrackTypes.TIME.toString()
        voltageKey = TrackTypes.VOLTAGE.toString()
        currentKey = TrackTypes.CURRENT.toString()
        
        with open(filename, 'wb') as file:
            file.write("Time [s];\tVoltage [V];\tCurrent [A]\n".encode("utf-8"))
            for i in range(len(data[timeKey])):
                line = "{:+.16E};\t{:+.16E};\t{:+.16E}\n".format(data[timeKey][i], data[voltageKey][i], data[currentKey][i])
                file.write(line.encode("utf-8"))
        
        return
    
