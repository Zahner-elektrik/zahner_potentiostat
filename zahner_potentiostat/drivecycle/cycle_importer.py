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

import re
from .HUDDSCOL import *
from .NYCCCOL import *


def readLinesFromProfie(profile):
    """ Read lines from a file without the header.
    
    This function reads all lines from a file except the first two lines.
    
    :param file: Path to the file.
    :returns: Array with the lines of the file.
    """
    lines = []
    if "NYCCCO" in profile:
        lines = NYCCCO_profile.split("\n")
    elif "HUDDSCOL" in profile:
        lines = HUDDSCOL_profile.split("\n")        
    return lines

    
def calculatedNormalisedDataForLines(lines):
    """ Get normalised data for the lines of the file.
    
    This function is intended as an example.
    
    With the help of the function the velocity data of the file are normalized to the absolute value
    of 1 to be able to measure the profile later with a individual current factor.
    
    The parser for the line content is developed as an example for both HUDDSCOL.txt and NYCCCOL.txt.
    The decimal separator is a dot and the column separator is a tab.
    
    The data structure required by the measureProfile() method is returned. The data is structured
    like the following example:
    
    [{"time": 0, "value": 0.1},{"time": 1, "value": 0.4},{"time": 2, "value": 0.3}]
    
    The structure is an array with a dictionary for each step. The dictionary has two keys:
        time: The time point of the value.
        value: The value, what the value is whether voltage, current or other is specified in the
            measureProfile() method.
    
    :param lines: Array with the data lines of the file as string.
    :returns: Explained data structure.
    """
    maxValue = 0
    normalisedData = []
    seperatorRegex = re.compile(r"([0-9,.]+)[\W]+([0-9,.]+)")   
    
    for line in lines:
        linematch = seperatorRegex.match(line)
        if linematch != None:
            data = dict()
            data["time"] = float(linematch.group(1))
            value = float(linematch.group(2))
            if abs(value) > abs(maxValue):
                maxValue = value
            data["value"] = value
            normalisedData.append(data)
    
    for data in normalisedData:
        """
        Normalisation to the biggest Value from -1 to 1.
        """
        data["value"] = data["value"] / abs(maxValue)
    return normalisedData


def getNormalisedCurrentTableForHUDDSCOL(): 
    """
    These are NOT correct current cycles they are SPEED CURVES.

    These cycles are not correct, because these are velocity curves and not current or voltage curves.
    These velocity curves must be converted to current curves or voltage curves depending on the application,
    THIS MUST BE DONE BY THE USER.
    The velocity waveforms were only obtained as an example of waveforms.
    
    Here the path may need to be adjusted.
    
    :returns: Explained data structure.
    """
    lines = readLinesFromProfie("HUDDSCOL")
    normalisedData = calculatedNormalisedDataForLines(lines)
    return normalisedData
    
    
def getNormalisedCurrentTableForNYCCCOL():
    """
    These are NOT correct current cycles they are SPEED CURVES.

    These cycles are not correct, because these are velocity curves and not current or voltage curves.
    These velocity curves must be converted to current curves or voltage curves depending on the application,
    THIS MUST BE DONE BY THE USER.
    The velocity waveforms were only obtained as an example of waveforms.
    
    Here the path may need to be adjusted.
    
    :returns: Explained data structure.
    """
    lines = readLinesFromProfie("NYCCCO")
    normalisedData = calculatedNormalisedDataForLines(lines)
    return normalisedData
    
