"""
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
"""

from typing import Optional, Union


class ZahnerError(Exception):
    """Base class for inheritance for Zahner errors.

    This class is used to identify Zahnner errors all other Zahnner errors are derived from this class.
    """

    _error_code: int
    _error_message: Optional[str]

    def __init__(
        self, error_code: Union[int, str], error_message: Optional[str] = None
    ):
        if isinstance(error_code, str):
            error_code = (
                error_code.strip()
            )  # passed error code strings sometimes end with a trailing '\n'
        self._error_code = error_code
        self._error_message = error_message
        super().__init__(
            "error code "
            + str(self._error_code)
            + (": " + self._error_message if self._error_message is not None else "")
        )


class ZahnerConnectionError(ZahnerError):
    """Exception which is thrown when an connection error occurs.

    This exception is thrown if, for example, the connection to the device is interrupted or an
    attempt is made to connect to a device that does not exist.
    """

    def __init__(self, error_code: Union[int, str]):
        super().__init__(error_code, None)


class ZahnerDataProtocolError(ZahnerError):
    """Exception which is thrown when an error occurs in the data protocol.

    If this exception is thrown, the device and python must be restarted because a fatal error has occurred.
    """

    def __init__(self, error_code: Union[int, str]):
        super().__init__(error_code, None)


class ZahnerSCPIError(ZahnerError):
    """
    exception which can be thrown if the device responds to a command with an error

    see static attribute `_message_strings` for possible specializations
    """

    _message_strings: dict[int, str] = {
        100: "value is out of range",
        27: "command does not exist",
        1003: "setup global limit reached",
        1004: "value is out of limited range",
        1005: "measurement was aborted. The status has to be cleared with \*CLS.",
        1006: "command is not executed because of an previous error or manual abort. (1003, 1005)",
        1007: "an error occurred during calibration. The device may be faulty.",
        42: "undefinded error",
        1000: "this command has not been implemented yet. But is foreseen.",
    }
    """associates an error number with a human-readable error code"""

    def __init__(self, error_code: Union[int, str]):
        # try to convert the error code to an int
        # unfortunately, the calling code adds a lot of "garbage strings", e.g. "Issue: \nerror "
        # TODO: this conversion should be done in the base class – just pass `_message_string` to
        # the base class constructor and let it handle the dirty work
        if isinstance(error_code, str):
            try:
                error_code = int(
                    error_code.removeprefix("Issue:")
                    .strip()
                    .removeprefix("error")
                    .strip()
                )
            except:
                pass  # TODO: this is not type-safe
        super().__init__(
            error_code,
            (
                self._message_strings[error_code]  # type: ignore # mypy gets confused here
                if error_code in self._message_strings
                else "unknown error – maybe upgrade your version of `zahner_potentiostat` package"
            ),
        )
