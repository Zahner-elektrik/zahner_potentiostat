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

import matplotlib
import matplotlib.pyplot as plt
from matplotlib.ticker import EngFormatter
import numpy as np


class DCPlot(object):
    """ Example class for plotting the data.
    
    This class is an example to show the data in an exemplary way. For special use cases, everyone
    must implement the plots themselves. The plot was optimized for data over a time track.
    
    X and Y axis are always displayed linearly. The labeling and unit of the axes can be adjusted
    separately.
    
    The constructor creates the plotting window with labels without data.
    Theoretically, an infinite number of y axes are possible. However, only 2 have been tested so far.
    The axes are automatically formatted with engineering prefixes.
    
    The display blocks as long as it does not get any computing time. It is optimized to be able
    to append data, and remains open after plt.show().
    By default, matplotlib would wait until the display is closed by the user.
    
    Example of how the yAxis parameter must be formatted:
    
    [{"label": "Voltage", "unit": "V"}, {"label": "Current", "unit": "A", "log": True}]
    
    The structure is an array with a dictionary for each axis. The dictionary has two keys:
    
    * label: The label of the axis.
    * unit: The unit of the axis.
    
    :param figureTitle: Title of the figure.
    :param xAxisLabel: Lable of the X-axis.
    :param xAxisUnit: Unit of the X-axis.
    :param yAxis: Data structure for the Y-axis.
    """
    colors = ["r", "b", "g", "c", "m", "y"]
    
    def __init__(self, figureTitle, xAxisLabel, xAxisUnit, yAxis, data = None,**kwargs):
        self._isOpen = True
        self.xData = []
        self.yData = []
        self.yAxisConfig = yAxis
        xFormatter = EngFormatter(unit=xAxisUnit)
        yFormatters = []
        for yAx in yAxis:
            if "unit" in yAx.keys():
                yFormatters.append(EngFormatter(unit=yAx["unit"]))
            else:
                yFormatters.append(EngFormatter(unit=""))

        self.fig, self.axis = plt.subplots(1, 1)
        self.fig.set_size_inches(10, 6)
        self.fig.canvas.manager.set_window_title(figureTitle)
        """
        Add a close event to easily check if the window is still open.
        """
        self.fig.canvas.mpl_connect('close_event', self._closeEvent)
                
        i = 0
        self.line = []
        self.allAxes = [self.axis]
        for yAx in yAxis:
            self.line.append(None)
            self.yData.append([])
            
            axLabel = ""
            if "label" in yAx.keys():
                axLabel = yAx["label"]
                if "log" in self.yAxisConfig[i] and self.yAxisConfig[i]["log"] == True:
                    axLabel = "|" + axLabel + "|"
                
            color = "fuchsia"  # default, if there are not enough colors in the array
            if i < len(DCPlot.colors):
                color = DCPlot.colors[i]
                
            #Voltage blue current red. Must be adjusted later if there are different voltages or currents.
            if "unit" in yAx.keys():
                if yAx["unit"] == "V":
                    color = "b"
                elif yAx["unit"] == "A":
                    color = "r"
                
            if i == 0:
                self.line[i], = self.axis.plot(self.xData, self.yData[i], label=axLabel, color=color, linewidth=1)
                self.axis.set_ylabel(axLabel)
                
                if "log" in yAx.keys() and yAx["log"] == True:
                    self.axis.set_yscale("log")
                self.axis.yaxis.set_major_formatter(yFormatters[i])
                
            else:
                self.allAxes.append(self.axis.twinx())
                self.line[i], = self.allAxes[i].plot(self.xData, self.yData[i], label=axLabel, color=color, linewidth=1)
                self.allAxes[i].set_ylabel(axLabel)
                
                if "log" in yAx.keys() and yAx["log"] == True:
                    self.allAxes[i].set_yscale("log")
                self.allAxes[i].yaxis.set_major_formatter(yFormatters[i])
            i += 1
            
        self.axis.xaxis.set_major_formatter(xFormatter)
        self.axis.set_xlabel(xAxisLabel)
        self.axis.xaxis.grid(which='both', linestyle='--')
        self.axis.yaxis.grid(which='both', linestyle='--')
        
        if len(yAxis) > 1:
            plt.legend(handles=self.line, loc="best")
        
        if data != None:
            self.addData(data[0], data[1], redraw = False)
        
        plt.figure(self.fig)
        plt.tight_layout()
        self.fig.canvas.draw()
        plt.pause(100e-3)
        return
        
    def addData(self, xData, yDatas, redraw = True):
        """ Append the data of the plot.
        
        This method is used to append data to the plot.
        
        xData contains an array with values for the X-axis. yDatas contains an array with one array
        for each Y-axis. The number of points must be the same for each data track.
        
        Example structure:
            xData = [0,1,2,3]
            yDatas = [[0,1,2,3],[0,1,2,3],...]
        
        :param xData: Array with points for the X-axis.
        :param yDatas: Array with arrys for each Y-axis.
        """
        self.xData.extend(xData)
            
        for i in range(len(self.yData)):
            absRequired = False
            if "log" in self.yAxisConfig[i] and self.yAxisConfig[i]["log"] == True:
                    absRequired = True
            if absRequired == False:
                self.yData[i].extend(yDatas[i])
            else:
                self.yData[i].extend(np.abs(yDatas[i]))
                
            self.line[i].set_ydata(self.yData[i])
            self.line[i].set_xdata(self.xData)
        
        for ax in self.allAxes:
            ax.relim(visible_only=True)
            ax.autoscale_view(True, True, True)
        
        if len(self.xData) > 0:
            if min(self.xData) != max(self.xData):
                self.axis.set_xlim(min(self.xData), max(self.xData))
                
        if redraw:
            plt.figure(self.fig)
            plt.tight_layout()
            self.fig.canvas.draw()
            plt.pause(1e-3)
        return
        
    def pause(self, time):
        """ Pause the plot.
        
        When the display pause is called, it gets compute time and is re-rendered.
        
        :param time: Pause in seconds.
        """
        plt.figure(self.fig)
        plt.pause(time)
        return
        
    def clearData(self):
        """ Clear the data from the plot.
        
        This command only deletes the data from the display.
        """
        self.xData = []
            
        for i in range(len(self.yData)):
            self.yData[i] = []
                
            self.line[i].set_ydata(self.yData[i])
            self.line[i].set_xdata(self.xData)
        return
            
    def clearPlot(self):
        """ Clear the data from the plot.
        
        This command deletes the data from the display and then redraws all of them to update the display.
        """
        self.clearData()
        plt.tight_layout()
        plt.draw()
        plt.pause(1e-3)
        return
        
    def savePlot(self, file, w=None, h=None):
        """ Saving the plot.

        Saving the plot, where the size of the plot can be adjusted beforehand.
        When saving, the file type must also be specified in the file name.
        These are the data types of the corresponding matplotlib command
        https://matplotlib.org/stable/api/_as_gen/matplotlib.pyplot.savefig.html .
        PDF works well for vector graphics. 
        
        :param file: File to save, with path and filetype.
        :param w: With of the image in inches, but can be omitted if not needed.
        :param h: Height of the image in inches, but can be omitted if not needed.
                    If only w is set, w is also used for the height, by matplotlib
                    and the image is square.
        """
        if w != None:
            self.fig.set_size_inches(w, h)
        plt.tight_layout()
        plt.draw()
        plt.pause(1e-3)
        self.fig.savefig(file, bbox_inches='tight')
        return
    
    def close(self):
        """ Close the plot.
        """
        plt.close()
        return
        
    def isOpen(self):
        """ Check if the window is open.
        
        Checks if the window is still open. If the window is closed, a private variable in the
        callback is set to false.
        
        :returns: True if the window is open else False.
        """
        return self._isOpen
    
    def _closeEvent(self, evt):
        """ Close event.
        
        This function is called when the plotting window is closed.
        """
        self._isOpen = False
        plt.close(self.fig)
        return
        
