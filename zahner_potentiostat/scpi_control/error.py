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

class ZahnerError(Exception):
    """  Base class for inheritance for Zahner errors.
    
    This class is used to identify Zahnner errors all other Zahnner errors are derived from this class.
    """

    def __init__(self, message):
        self.message = message
        super().__init__(self.message)        



class ZahnerConnectionError(ZahnerError):
    """ Exception which is thrown when an connection error occurs.
    
    This exception is thrown if, for example, the connection to the device is interrupted or an
    attempt is made to connect to a device that does not exist.
    """
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)



class ZahnerDataProtocolError(ZahnerError):
    """ Exception which is thrown when an error occurs in the data protocol.
    
    If this exception is thrown, the device and python must be restarted because a fatal error has occurred.
    """
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


        
class ZahnerSCPIError(ZahnerError):
    """ Exception which can be thrown if the device responds to a command with an error.
    
    ========  ========
    Number    Description
    ========  ========
    100       Value is out of range.
    27        The command does not exist.
    1003      Setup global limit reached.
    1004      Value is out of the limited range.
    1005      The measurement was aborted. The status has to be cleared with \*CLS.
    1006      The command is not executed because of an previous error or manual abort. (1003, 1005)
    1007      An error occurred during calibration. The device may be faulty.
    42        Undefinded error.
    1000      This command has not been implemented yet. But is foreseen.
    ========  ========
    """
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)
