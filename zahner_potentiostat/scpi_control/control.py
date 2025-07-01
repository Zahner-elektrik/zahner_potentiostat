r"""
  ____       __                        __    __   __      _ __
 /_  / ___ _/ /  ___  ___ ___________ / /__ / /__/ /_____(_) /__
  / /_/ _ `/ _ \/ _ \/ -_) __/___/ -_) / -_)  '_/ __/ __/ /  '_/
 /___/\_,_/_//_/_//_/\__/_/      \__/_/\__/_/\_\\__/_/ /_/_/\_\

Copyright 2025 Zahner-Elektrik GmbH & Co. KG

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

from enum import Enum
from typing import Optional, Union
import time
import re
import datetime
import sys

import numpy
from .serial_interface import (
    CommandType,
    DEBUG,
    SerialCommandInterface,
    SerialDataInterface,
)
from .datareceiver import DataReceiver
from .error import ZahnerSCPIError
from builtins import isinstance


def firmwareStringToNumber(firmwareString):
    softwareVersionRegex = re.compile(
        r"(?P<major>[\d]+).(?P<minor>[\d]+).(?P<build>[\d]+)(?P<additional>.*)"
    )
    softwareVersionMatch = softwareVersionRegex.match(firmwareString)
    firmwareNumber = 0
    firmwareNumber = firmwareNumber + 100000**2 * int(softwareVersionMatch["major"])
    firmwareNumber = firmwareNumber + 100000**1 * int(softwareVersionMatch["minor"])
    firmwareNumber = firmwareNumber + 100000**0 * int(softwareVersionMatch["build"])
    return firmwareNumber


requiredSoftwareVersionString = "1.1.0"
requiredSoftwareVersion = firmwareStringToNumber(requiredSoftwareVersionString)


class COUPLING(Enum):
    """
    Working modes for the potentiostat.
    """

    GALVANOSTATIC = 0
    POTENTIOSTATIC = 1


class RELATION(Enum):
    """
    Possible potential references for voltage parameters.
    OCP and OCV are the same and mean reference to open circuit voltage and potential respectively.
    """

    ZERO = 0
    OCV = 1


class SCPIDevice:
    r"""General important information for the control of the devices with this class.

    The control concept is that via `SCPI <https://de.wikipedia.org/wiki/Standard_Commands_for_Programmable_Instruments>`_ with the setter methods parameters are set which configure
    the primitives.

    Under SCPI-COMMAND you can see the command sent by the method to the device.
    The command must be followed by an "\\\\n" as a line break.

    The following primitives are available to compose methods with:

    **Potentiostatic or galvanostatic polarization**

    * :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.measurePolarization`

    **Open circuit voltage/potential scan**

    * :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.measureOCV`
    * :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.measureOCVScan`

    **Ramps potentiostatic or galvanostatic**

    * :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.measureRampValueInTime`
    * :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.measureRampValueInScanRate`
    * :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.measureRampScanRateForTime`

    **Staircase potentiostatic or galvanostatic**

    * :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.measureIEStairs`


    As an example, the following measurement methods were composed of the primitives:

    **Charge or discharge something**

    * :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.measureCharge`
    * :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.measureDischarge`

    **Output potentiostatic or galvanostatic profile as potentiostatic and galvanostatic polarization or ramps**

    * :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.measureProfile`

    **PITT Potentiostatic Intermittent Titration Technique**

    * :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.measurePITT`

    **GITT Galvanostatic Intermittent Titration Technique**

    * :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.measureGITT`



    When the primitives are called, they use all parameters and then behave differently depending on
    the configuration. The methods are setters for devices internal parameters for the individual
    primitives which can be assembled. The parameters are not reset after the primitive and must be
    changed manually if they are to change, for the next primitive.

    **The concept is that nothing is done implicitly, everything must be done explicitly.
    The only thing that is done implicitly is that the potentiostat is switched on by the methods
    when they need a potentiostat switched on.**


    The following methods/parameters are allowed by default:

    * :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.setAutorangingEnabled`
    * :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.setInterpolationEnabled`

    By default the following methods/parameters are disabled:

    * :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.setMinMaxVoltageParameterCheckEnabled`
    * :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.setMinMaxCurrentParameterCheckEnabled`
    * :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.setGlobalVoltageCheckEnabled`
    * :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.setGlobalCurrentCheckEnabled`
    * :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.setToleranceBreakEnabled`
    * :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.setGlobalVoltageCheckEnabled`
    * :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.setChargeBreakEnabled`

    The primitives turn the potentiostat on or off depending on how they need it.
    They turn the potentiostat off or on after the primitive depending on how it was before.

    After each primitive there is no measurement for a short time and the data is transferred to the
    computer. This time depends on how the sampling rate is chosen, usually this time is in the
    range of 0 ms to 100 ms, tending to be about 10 ms - 20 ms. In the future, primitives will
    follow in which arbitrary signals with voltage or current values can be output without dead times.

    If somewhere POGA is mentioned then the primitive :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.measurePolarization` is meant,
    with which constant voltage or constant current can be output.

    The binary serialName can be read from this object, or by other software such as the Zahner-Lab.
    The data must always be read from the device when it sends them.

    At the moment an autonomous measuring operation without connected computer is not possible.

    When using multiple devices, these objects must each run in a separate thread.
    It is not possible to pass these objects as argument for multiprocessing, because this object cannot be serialized.

    :param commandInterface: SerialCommandInterface object to control the device.
    :type commandInterface: :class:`~zahner_potentiostat.scpi_control.serial_interface.SerialCommandInterface`
    :param dataInterface: SerialDataInterface object for online data.
    :type dataInterface: :class:`~zahner_potentiostat.scpi_control.serial_interface.SerialDataInterface`
    :param enablePackageUpdateWarning: False to disable warn output to the package version on the console.
    """

    def __init__(
        self,
        commandInterface: SerialCommandInterface,
        dataInterface: Optional[SerialDataInterface],
        enablePackageUpdateWarning: bool = True,
    ):
        self._commandInterface = commandInterface
        self._coupling = COUPLING.POTENTIOSTATIC
        self._raiseOnError = False
        self._dataReceiver: Optional[DataReceiver] = None
        if dataInterface is not None:
            self._dataReceiver = DataReceiver(dataInterface)
        """
        Read the device firmware version and check if the version matches the library.
        """
        deviceInformation = self.IDN()
        softwareVersionString = (
            deviceInformation.split(",")[3].replace("binary", "").strip()
        )
        softwareVersionNumber = firmwareStringToNumber(softwareVersionString)

        if softwareVersionNumber == requiredSoftwareVersion:
            pass
        elif softwareVersionNumber < requiredSoftwareVersion:
            errorString = f"""ERROR: Device firmware must be updated.

The device firmware has the version {softwareVersionString}, but for this package the firmware version {requiredSoftwareVersionString} is needed.

Please carefully read the manual from the following link for updating the device firmware and properly follow the provided instructions:
https://download.zahner.de/ExternalPotentiostatUpdater/ZahnerPotentiostatUpdaterManual.pdf

From the following link you can download the installer for the latest device software:
https://download.zahner.de/ExternalPotentiostatUpdater/ZahnerPotentiostatUpdater_latest.exe

For any questions or in case of problems please contact: support@zahner.de
"""
            print(errorString)
            _ = input()
            sys.exit()
        elif (
            softwareVersionNumber > requiredSoftwareVersion
            and enablePackageUpdateWarning
        ):
            warningString = f"""WARNING: There might be an update available for the Python package.

The Python package was installed for the devices firmware {requiredSoftwareVersionString}, but the found device has the firmware version {softwareVersionString}.
So it could be possible that an update for the Python package is available.

Check GitHub or pip for updates:
https://github.com/Zahner-elektrik/zahner_potentiostat
pip install zahner-potentiostat -U
"""
            print(warningString)

        return

    """
    Methods for managing the object and the connection.
    """

    def close(self) -> None:
        """Close the Connection.

        Close the connection and stop the receiver.
        """
        self._commandInterface.close()
        if self._dataReceiver != None:
            self._dataReceiver.stop()

    def getDataReceiver(self) -> DataReceiver:
        """Get the DataReceiver object.

        The DataReceiver type object processes the data from the binary comport.

        :returns: the DataReceiver object or None if it doesn't exist.
        """
        return self._dataReceiver

    def setRaiseOnErrorEnabled(self, enabled: bool = True) -> None:
        """Setting the error handling of the control object.

        If False, then strings from the device containing error are thrown as exceptions.

        :param enabled: True to throw execeptions on errors.
        """
        self._raiseOnError = enabled
        return

    def getRaiseOnErrorEnabled(self) -> bool:
        """Read the error handling of the control object.

        :returns: True if errors trigger an exception.
        """
        return self._raiseOnError

    """
    Methods that talk to the device via SCPI.
    """

    def IDN(self) -> str:
        r"""Read informations about the device.

        The device uses the `SCPI <https://de.wikipedia.org/wiki/Standard_Commands_for_Programmable_Instruments>`_ protocol on the interface.

        This method provides for example the following software information.
        Manufacturer, device name, serial number, software version and "binary" if it is the binary channel.

        For example:
        ZAHNER-ELEKTRIK,PP212,33000,1.0.0 binary

        :SCPI-COMMAND: \*IDN?
        :returns: The response string from the device.
        :rtype: string
        """
        return self._writeCommandToInterfaceAndReadLine("*IDN?")

    def readDeviceInformations(self) -> str:
        r"""Read informations about the device.

        The device uses the `SCPI <https://de.wikipedia.org/wiki/Standard_Commands_for_Programmable_Instruments>`_ protocol on the interface.

        This method provides for example the following software information.
        Manufacturer, device name, serial number, software version and "binary" if it is the binary channel.

        For example:
        ZAHNER-ELEKTRIK,PP212,33000,1.0.0 binary

        The information is then transferred to the internal data structure.

        :SCPI-COMMAND: \*IDN?
        :returns: The response string from the device.
        :rtype: string
        """
        reply = self.IDN()
        reply = reply.split(",")
        reply[0] = reply[0].strip()
        self.DeviceName = reply[1].strip()
        self.DeviceSerialNumber = reply[2].strip()
        self.DeviceSoftwareVersion = reply[3].strip()
        self.DiagnosticState = 0
        return self.IDN()

    def clearState(self) -> str:
        r"""Clear device state.

        Deleting the device state, for example, if the Global Limits have been exceeded.
        The error numbers are described in the class :class:`~zahner_potentiostat.scpi_control.error.ZahnerSCPIError`.

        :SCPI-COMMAND: \*CLS
        :returns: The response string from the device.
        :rtype: string
        """
        return self._writeCommandToInterfaceAndReadLine("*CLS")

    def readState(self) -> str:
        r"""Read device state.

        Read the device state, for example, if the Global Limits have been exceeded.
        The error numbers are described in the class :class:`~zahner_potentiostat.scpi_control.error.ZahnerSCPIError`.

        :SCPI-COMMAND: \*CLS?
        :returns: The response string from the device.
        :rtype: string
        """
        return self._writeCommandToInterfaceAndReadLine("*CLS?")

    def checkResetStatus(self) -> str:
        """Check device status.

        Read and clear the status if an error has occurred.

        :returns: The response string from the device.
        :rtype: string
        """
        status = self.readState()
        if status != 0:
            self.clearState()
            print("Error Status: " + str(status))
        return status

    def resetCommand(self) -> str:
        r"""Reset the device.

        **THIS FUNCTION CAN BE CALLED FROM AN OTHER THREAD**

        This command switches off the potentiostat and reboots the device.
        This causes the connection to be lost and the connection must be re-established.
        This object must also be recreated so that everything is reinitialized via the
        constructors and the threads are restarted.

        :SCPI-COMMAND: \*RST
        :returns: The response string from the device.
        :rtype: string
        """
        return self._writeCommandToInterfaceAndReadLine("*RST")

    def abortCommand(self) -> str:
        """Abort of the active measurement.

        **THIS FUNCTION CAN BE CALLED FROM AN OTHER THREAD**

        This function aborts the measurement and switches off the potetiosat.
        Afterwards the status must be reset with CLS so that the measurement can be continued and
        new primitives can be called.

        The device responds to reply with ok. Other command that are active for example an ramp will
        return with an status that the measurement was aborted. It is also possible that the device
        will return with two ok if, depending on when the active measurement was finished.

        :SCPI-COMMAND: ABOR
        :returns: The response string from the device.
        :rtype: string
        """
        return self._writeCommandToInterfaceAndReadLine("ABOR")

    def calibrateOffsets(self) -> str:
        """Execute the offset calibration.

        The offsets must be calibrated manually by calling this method after the instrument has been
        warmed up for at least half an hour.

        The calibration data contains the warm offset values at the time of calibration.
        If the cold instrument is calibrated, the offsets will be worse when the instrument is warm.
        If you do not calibrate after the start, the offsets will be getting better until the instrument is warmed up.

        It is NOT recommended to calibrate the cold instrument only once after startup.
        It does not hurt to calibrate the offsets from time to time, as this only takes a few seconds.

        If the calibration returns several times with an error, there may be a defect.
        In this case, contact your Zahner distributor.

        :SCPI-COMMAND: :SESO:CALO
        :returns: The response string from the device.
        :rtype: string
        """
        return self._writeCommandToInterfaceAndReadLine(":SESO:CALO")

    def switchToEPCControl(self) -> str:
        """Switch to EPC mode and switch off the potentiostat for safety.

        When this command is called, the device closes the USB connection and can only be controlled via the EPC interface.
        It must be switched back to the SCPI mode manually via Remote2 from the Thales side.

        This function probably throws an exception, because the device disconnects from USB by software.
        This must be received with Try and Catch.

        :SCPI-COMMAND: :SYST:SEPC
        :returns: The response string from the device.
        :rtype: string
        """

        if self._dataReceiver != None:
            self._dataReceiver.stop()
        return self._writeCommandToInterfaceAndReadLine(":SYST:SEPC")

    def switchToEPCControlWithoutPotentiostatStateChange(self) -> str:
        """Switch to EPC mode without changing settings on the potentiostat.

        This function leaves the potentiostat in its current operating state and then switches to EPC mode.
        This should only be used when it is really necessary to leave the potentiostat on,
        because between the change of control no quantities like current and voltage are monitored.

        When this command is called, the device closes the USB connection and can only be controlled via the EPC interface.
        It must be switched back to the SCPI mode manually via Remote2 from the Thales side.

        This function probably throws an exception, because the device disconnects from USB by software.
        This must be received with try and catch.

        To ensure that the switch between Thales and Python/SCPI is interference-free, the following procedure should be followed.
        This is necessary to ensure that both Thales and Python/SCPI have calibrated offsets, otherwise jumps may occur when switching modes:

         1. Connect Zennium with USB and EPC-device/power potentiostat (XPOT2, PP2x2, EL1002) with USB to the computer. As well as Zennium to power potentiostat by EPC cable.
         2. Switch on all devices.
         3. Allow the equipment to warm up for at least 30 minutes.
         4. Select and calibrate the EPC-device in Thales (with Remote2).
         5. Switching the EPC-device to SCPI mode via Remote2 command.
         6. Performing the offset calibration with Python/SCPI.
         7. Then it is possible to switch between Thales and Python/SCPI with the potentiostat switched on.

        :SCPI-COMMAND: :SYST:HOTS
        :returns: The response string from the device.
        :rtype: string
        """

        if self._dataReceiver != None:
            self._dataReceiver.stop()
        return self._writeCommandToInterfaceAndReadLine(":SYST:HOTS")

    def setLineFrequency(self, frequency: float) -> str:
        """Set the line frequency of the device.

        With this command the line frequency can be changed, depending on the country where the
        device is located.
        The line frequency is stored in the device and is still stored after a restart of the device.

        The device must know the line frequency of the country in which it is located in order to
        suppress interference.


        :SCPI-COMMAND: :SYST:LINF <value>
        :param frequency: The frequency as float value.
        :returns: The response string from the device.
        :rtype: string
        """
        return self._writeCommandToInterfaceAndReadLine(
            ":SYST:LINF {}".format(frequency)
        )

    def getLineFrequency(self) -> float:
        """Read the line frequency of the device.

        The line frequency is stored in the device and is still stored after a restart of the device.


        :SCPI-COMMAND: :SYST:LINF?
        :returns: The set line frequency as float.
        :rtype: float
        """
        return self._writeCommandToInterfaceAndReadValue(":SYST:LINF?")

    def setDateTime(
        self, year: int, month: int, day: int, hour: int, minute: int, second: int
    ) -> str:
        """Set the time of the device.

        This command is used to set the device time.

        :SCPI-COMMAND: :SYST:TIME <yyyy>-<mm>-<dd>T<hh>:<mm>:<ss>
        :returns: The response string from the device.
        :rtype: string
        """
        return self._writeCommandToInterfaceAndReadLine(
            ":SYST:TIME {:04d}-{:02d}-{:02d}T{:02d}:{:02d}:{:02d}".format(
                year, month, day, hour, minute, second
            )
        )

    def __get_date_time_str_as_iso_8601__(self) -> str:
        """read the time of the device

        :SCPI-COMMAND: :SYST:TIME?
        :returns: the time from the device as ISO 8601 string
        :rtype: string
        """
        return self._writeCommandToInterfaceAndReadLine(":SYST:TIME?")

    def getDateTime(self) -> str:
        """read the time of the device

        :returns: the time from the device as ISO 8601 string
        """
        return self.__get_date_time_str_as_iso_8601__()

    def getDateTimeStruct(self) -> datetime.date:
        """
        read the time of the device

        :returns the date and time as `datetime` struct
        """
        return datetime.datetime.fromisoformat(self.__get_date_time_str_as_iso_8601__())

    def getSoftwareInfo(self) -> str:
        """Read software information.

        The basic revision of the software can be queried with IDN.
        This command queries complex software information that is not required under normal circumstances.
        It is only used internally to identify untagged versions of the software.

        For example:
        Version: 1.0.0-rc3; Branch: master; Hash: 247a16a75a3d5685def55972588990aeebbf280f; Target: Debug; Compile time: 2021-04-08T10:49:25.074486+01:00

        :SCPI-COMMAND: :SYST:SOFT:INFO?
        :returns: The time from the device as ISO 8601 string.
        :rtype: string
        """
        return self._writeCommandToInterfaceAndReadLine(":SYST:SOFT:INFO?")

    def getPotential(self) -> float:
        """Read the potential from the device.

        This command is the same as getVoltage to allow the naming of voltage and potential.

        :SCPI-COMMAND: :MEAS:VOLT?
        :returns: The most recent measured potential.
        :rtype: float
        """
        return self.getVoltage()

    def getVoltage(self) -> float:
        """Read the voltage from the device.

        Read the voltage between Reference and Working Sense.

        :SCPI-COMMAND: :MEAS:VOLT?
        :returns: The most recent measured voltage.
        :rtype: float
        """
        line = self._writeCommandToInterfaceAndReadLine(":MEAS:VOLT?")
        text = line.split(",")
        return float(text[0])

    def getPotentialMedian(self, measurements: int = 7) -> float:
        """Read potential and calculate median.

        Does the same as getVoltageMedian.

        :param measurements: The number of measurements for median calculation.
        :returns: The median potential.
        :rtype: float
        """
        return self.getVoltageMedian(measurements)

    def getVoltageMedian(self, measurements: int = 7) -> float:
        """Read potential and calculate median.

        Reade measurements times the potential from the device and calculate the
        median.

        :param measurements: The number of measurements for median calculation.
        :returns: The median potential.
        :rtype: float
        """
        data = []
        for i in range(measurements):
            time.sleep(0.050)
            data.append(self.getVoltage())
        data = sorted(data)
        return numpy.median(data)

    def getCurrent(self) -> float:
        """Read the current from the device.

        This command reads only the current current value.
        This function does NOT automatically set the correct current range, it ONLY READS.

        :SCPI-COMMAND: :MEAS:CURR?
        :returns: The most recent measured current.
        :rtype: float
        """
        return self._writeCommandToInterfaceAndReadValue(":MEAS:CURR?")

    def getCurrentMedian(self, measurements: int = 7) -> float:
        """Read current and calculate median.

        Reade measurements times the current from the device and calculate the
        median.

        :param measurements: The number of measurements for median calculation.
        :returns: The median current.
        :rtype: float
        """
        data = []
        for i in range(measurements):
            time.sleep(0.050)
            data.append(self.getCurrent())
        data = sorted(data)
        return numpy.median(data)

    def setPotentiostatEnabled(self, enable: bool = False) -> str:
        """Switching the potentiostat on or off.

        If only the potentiostat is switched on, **NO RANGING** is performed and **NO LIMITS** are monitored.
        Everything must be done manually.

        If primitives require a potentiostat to be on, such as polarizing, then they will turn the
        potentiostat on. After the primitive it will be switched back to the previous state.

        If the potentiostat was on before a primitive, for example, then it will be switched on
        again after the primitive.

        If the potentiostat was not on before a primitive, it takes up to 50 ms at the beginning of
        the primitive, depending on the device, until the potentiostat has settled and measurement
        can be started. If the potentiostat is already on at the beginning of the measurement, the
        measurement starts immediately. If faster processes are to be recorded in succession in
        different primitives, the potentiostat must be switched on beforehand.

        :SCPI-COMMAND: :SESO:STAT <ON|OFF>
        :param enable: The state. True to turn on.
        :returns: The response string from the device.
        :rtype: string
        """
        if enable == True:
            command = ":SESO:STAT ON"
        else:
            command = ":SESO:STAT OFF"
        return self._writeCommandToInterfaceAndReadLine(command)

    def _getRelationCommandParameter(self, relation: Union[RELATION, str]) -> str:
        """Get the relation command parameter.

        This function returns the parameter for the relation, which must be sent as SCPI command.

        :param relation: The relation OCV or ZERO.
        :type relation: :class:`~zahner_potentiostat.scpi_control.control.RELATION`
        :returns: The parameter string
        :rtype: string
        """
        if isinstance(relation, RELATION) and (
            relation == RELATION.OCV or relation == RELATION.OCV.value
        ):
            command = "OCV"
        elif isinstance(relation, str) and (
            "OCV" in relation.upper() or "OCP" in relation.upper()
        ):
            command = "OCV"
        else:
            if isinstance(relation, RELATION) and (
                relation == RELATION.ZERO or relation == RELATION.ZERO.value
            ):
                command = "0"
            elif isinstance(relation, str) and (
                "0" in relation or "ZERO" in relation.upper()
            ):
                command = "0"
            else:
                raise ValueError("invalid parameter `relation`")
        return command

    def setVoltageRelation(self, relation: Union[RELATION, str]) -> str:
        """Set the relation of the voltage parameter for simple use.

        If the relation is related to OCV, :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.measureOCV` must be used to specify the OCV relation to
        be used for calculating the relative voltage.

        The relation is of the type :class:`~zahner_potentiostat.scpi_control.control.RELATION`.
        The strings OCP OCV and the number 1 is also supported for relation to Open Circuit.
        Everything else means relation to 0 V.

        :SCPI-COMMAND: :SESO:UREL <OCV|0>
        :param relation: The relation OCV or ZERO.
        :type relation: :class:`~zahner_potentiostat.scpi_control.control.RELATION`
        :returns: The response string from the device.
        :rtype: string
        """
        return self._writeCommandToInterfaceAndReadLine(
            f":SESO:UREL {self._getRelationCommandParameter(relation)}"
        )

    def setVoltageValue(self, value: float) -> str:
        """Set the voltage parameter for simple use.

        This value should be set before switching on.

        If the potentiostat is simply switched on potentiostatically without a primitive,
        this voltage value is output on the potentiostat.

        If :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.setVoltageRelation` is selected as OCV, then this value is added to the measured OCV.

        :SCPI-COMMAND: :SESO:UVAL <value>
        :param value: The voltage value.
        :returns: The response string from the device.
        :rtype: string
        """
        return self._writeCommandToInterfaceAndReadLine(":SESO:UVAL " + str(value))

    def setCurrentValue(self, value: float) -> str:
        """Set the current parameter for simple use.

        This value should be set before switching on.

        If the potentiostat is simply switched on galvanostatically without a primitive,
        this current value is output on the galvanostat.

        :SCPI-COMMAND: :SESO:IVAL <value>
        :param value: The current value.
        :returns: The response string from the device.
        :rtype: string
        """
        return self._writeCommandToInterfaceAndReadLine(":SESO:IVAL " + str(value))

    def getMACAddress(self) -> str:
        """Read MAC address from device.

        Each device is assigned a MAC address from the Zahner MAC address block.
        With this command the MAC address can be read.

        :SCPI-COMMAND: :SYST:MAC?
        :returns: The MAC address of the device.
        :rtype: string
        """
        return self._writeCommandToInterfaceAndReadLine(":SYST:MAC?")

    def setVoltageRange(self, voltage: float) -> str:
        """Set the voltage range.

        This command sets the voltage range by an voltage value.

        :SCPI-COMMAND: :SESO:VRNG <value>
        :param voltage: voltage for which the range is to be selected.
        :returns: The response string from the device.
        :rtype: string
        """
        return self._writeCommandToInterfaceAndReadLine(":SESO:VRNG " + str(voltage))

    def setVoltageRangeIndex(self, voltage: int) -> str:
        """Set the voltage range.

        This command sets the voltage range by the range index.
        Index starts at 0.

        :SCPI-COMMAND: :SESO:VRNG:IDX <value>
        :param voltage: voltage range index.
        :returns: The response string from the device.
        :rtype: string
        """
        return self._writeCommandToInterfaceAndReadLine(
            ":SESO:VRNG:IDX " + str(voltage)
        )

    def setAutorangingEnabled(self, state: bool = True) -> str:
        """Set the autoranging state.

        This does not work perfectly depending on the measurement object.
        The best option is always to measure with a fixed current range without autoranging.

        Autoranging is only activ in primitves.
        If only the potentiostat is switched on, **NO RANGING** is performed and **NO LIMITS** are monitored.
        It is recommended to measure without autoranging if you know the current that will flow.

        It can be rang in all primitives. However, disturbances can be seen in the measurement
        from the ringing, since disturbances occur during the shunt change.
        The time for switching is up to 50 ms depending on the device.

        If you start in the wrong measuring range, time passes at the beginning in which disturbances
        and measuring errors are to be seen, until the correct measuring range is found.

        Before starting the measurement, you can manually set a current range to accelerate until
        the correct shunt is found.

        :SCPI-COMMAND: :SESO:CRNG:AUTO <1|0>
        :param state: The state of autoranging. True means turned on.
        :returns: The response string from the device.
        :rtype: string
        """
        if state:
            command = ":SESO:CRNG:AUTO 1"
        else:
            command = ":SESO:CRNG:AUTO 0"
        return self._writeCommandToInterfaceAndReadLine(command)

    def setInterpolationEnabled(self, state: bool = True) -> str:
        """Set the interpolation state.

        When autoranging is active, disturbances in the measurement may be seen
        due to the current range change of the potentiostat.

        If interpolation is switched off, the disturbances are visible in the data.
        If interpolation is switched on, the current points are linearly interpolated
        with the current values before and after the range change.

        This does not work perfectly depending on the measurement object.
        The best option is always to measure with a fixed current range without autoranging.

        :SCPI-COMMAND: :SESO:INTP <1|0>
        :param state: The state of interpolation. True means turned on.
        :returns: The response string from the device.
        :rtype: string
        """
        if state == True:
            command = ":SESO:INTP 1"
        else:
            command = ":SESO:INTP 0"
        return self._writeCommandToInterfaceAndReadLine(command)

    def setMinimumShuntIndex(self, index: int) -> str:
        """Set the minimum shunt index.

        This command sets the smallest shunt that is used.
        Index starts at 0.

        :SCPI-COMMAND: :SESO:CRNG:AUTO:LLIM <value>
        :param current: Current range index.
        :returns: The response string from the device.
        :rtype: string
        """
        return self._writeCommandToInterfaceAndReadLine(
            ":SESO:CRNG:AUTO:LLIM " + str(index)
        )

    def setMaximumShuntIndex(self, index: int) -> str:
        """Set the maximum shunt index.

        This command sets the biggest shunt that is used.
        Index starts at 0.

        :SCPI-COMMAND: :SESO:CRNG:AUTO:ULIM <value>
        :param current: Current range index.
        :returns: The response string from the device.
        :rtype: string
        """
        return self._writeCommandToInterfaceAndReadLine(
            ":SESO:CRNG:AUTO:ULIM " + str(index)
        )

    def setShuntIndex(self, index: int) -> str:
        """Set the shunt index.

        This command sets a shunt, via its index.
        Index starts at 0.

        :SCPI-COMMAND: :SESO:CRNG:IDX <value>
        :param current: Current range index.
        :returns: The response string from the device.
        :rtype: string
        """
        return self._writeCommandToInterfaceAndReadLine(":SESO:CRNG:IDX " + str(index))

    def setCurrentRange(self, current: float) -> str:
        """Set the current range.

        This command sets a shunt.
        The shunt is automatically selected to match the current value.

        :SCPI-COMMAND: :SESO:CRNG <value>
        :param current: Current for which the range is to be selected.
        :returns: The response string from the device.
        :rtype: string
        """
        return self._writeCommandToInterfaceAndReadLine(":SESO:CRNG " + str(current))

    def setTimeParameter(self, time: Union[float, str]) -> str:
        """Set the time parameter.

        This command sets the time for primitives that require a single time parameter, such as ramps.

        The time can be specified as a floating point number, then it is interpreted as seconds.
        The number should not be much smaller than one second.

        Alternatively, the time can also be specified as a string.
        Then you have s, m and min and h as time unit available.

        As can be read in the class :class:`~zahner_potentiostat.scpi_control.control.SCPIDevice`,
        there is a dead time at the ends of the primitive, that this does not fall into the weight,
        the time should not be less than one second.

        Examples:

        * setTimeParameter(3.1415)         Input as seconds.
        * setTimeParameter("3.1415 s")     Input as seconds.
        * setTimeParameter("3.1415 m")     Input as minutes.
        * setTimeParameter("3.1415 min")   Input as minutes.
        * setTimeParameter("3.1415 h")     Input as hours.

        :SCPI-COMMAND: :PARA:TIME <value>
        :param time: The time parameter. READ THE TEXT ABOVE.
        :returns: The response string from the device.
        :rtype: string
        """
        time = self._processTimeInput(time)
        return self._writeCommandToInterfaceAndReadLine(":PARA:TIME " + str(time))

    def setMaximumTimeParameter(self, value: Union[float, str]) -> str:
        """Set the maximum time parameter.

        Parameters for primitives that require a maximum time.
        Enter the parameter as for :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.setTimeParameter`.

        As can be read in the class :class:`~zahner_potentiostat.scpi_control.control.SCPIDevice`,
        there is a dead time at the ends of the primitive, that this does not fall into the weight,
        the time should not be less than one second.

        :SCPI-COMMAND: :PARA:TMAX <value>
        :param time: time parameter; for valid values see `setTimeParameter`
        :returns: response string from the device
        :rtype: string
        """
        value = self._processTimeInput(value)
        return self._writeCommandToInterfaceAndReadLine(":PARA:TMAX " + str(value))

    def setMinimumTimeParameter(self, value: Union[float, str]) -> str:
        """Set the minimum time parameter.

        Parameters for primitives that require a minimum time.
        Enter the parameter as for :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.setTimeParameter`.

        :SCPI-COMMAND: :PARA:TMIN <value>
        :param time: time parameter; for valid values see `setTimeParameter`
        :returns: The response string from the device.
        :rtype: string
        """
        value = self._processTimeInput(value)
        return self._writeCommandToInterfaceAndReadLine(":PARA:TMIN " + str(value))

    def setVoltageParameterRelation(self, relation: Union[RELATION, str]) -> str:
        """Set the relation of the voltage parameter for primitves.

        If the relation is related to OCV, :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.measureOCV` must be used to specify the OCV relation to
        be used for calculating the relative voltage.

        The relation is of the type :class:`~zahner_potentiostat.scpi_control.control.RELATION`.
        The strings OCP OCV and the number 1 is also supported for relation to Open Circuit.
        Everything else means relation to 0 V.

        :SCPI-COMMAND: :PARA:UREL <OCV|0>
        :param relation: The relation OCV or ZERO.
        :type relation: :class:`~zahner_potentiostat.scpi_control.control.RELATION`
        :returns: The response string from the device.
        :rtype: string
        """
        return self._writeCommandToInterfaceAndReadLine(
            f":PARA:UREL {self._getRelationCommandParameter(relation)}"
        )

    def setVoltageParameter(self, value: float) -> str:
        """Set the voltage parameter for primitives.

        Primitves that need an voltage parameter like ramps use this parameter.
        This parameter is only used when the coupling is potentiostatic.

        If :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.setVoltageParameterRelation` is selected as OCV, then this value is added to the measured OCV.

        :SCPI-COMMAND: :PARA:UVAL <value>
        :param value: The voltage value.
        :returns: The response string from the device.
        :rtype: string
        """
        return self._writeCommandToInterfaceAndReadLine(":PARA:UVAL " + str(value))

    def setCurrentParameter(self, value: float) -> str:
        """Set the current parameter for primitives.

        Primitves that need an current parameter like ramps use this parameter.
        This parameter is only used when the coupling is galvanostatic.

        :SCPI-COMMAND: :PARA:IVAL <value>
        :param value: The current value.
        :returns: The response string from the device.
        :rtype: string
        """
        return self._writeCommandToInterfaceAndReadLine(":PARA:IVAL " + str(value))

    def setScanRateParameter(self, scanrate: float) -> str:
        """Set the scan rate for primitives.

        Primitves that need an scan rate parameter use this parameter.
        The value is interpreted as V/s or A/s depending on the selected coupling.

        :SCPI-COMMAND: :PARA:SCRA <value>
        :param value: The scanrate value. V/s or A/s depending on coupling as float.
        :returns: The response string from the device.
        :rtype: string
        """
        return self._writeCommandToInterfaceAndReadLine(":PARA:SCRA " + str(scanrate))

    def setCoupling(self, coupling: Union[COUPLING, str]) -> str:
        """Set the coupling of the device.

        Set the coupling to galvanostatic or potentiostatic.
        The parameter coupling has to be from type :class:`~zahner_potentiostat.scpi_control.control.COUPLING` or the string "pot".

        When the coupling is changed the potentiostat will be turned off.
        It must be switched on again manually, with :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.setPotentiostatEnabled`.

        :SCPI-COMMAND: :SESO:COUP <pot|gal>
        :param coupling: The coupling of the device.
        :type coupling: :class:`~zahner_potentiostat.scpi_control.control.COUPLING`
        :returns: The response string from the device.
        :rtype: string
        """
        if isinstance(coupling, str):
            if "pot" in coupling:
                command = ":SESO:COUP pot"
                self._coupling = COUPLING.POTENTIOSTATIC
            elif "gal" in coupling:
                command = ":SESO:COUP gal"
                self._coupling = COUPLING.GALVANOSTATIC
            else:
                raise ValueError("invalid parameter `coupling`")
        elif isinstance(coupling, COUPLING):
            if coupling == COUPLING.POTENTIOSTATIC:
                command = ":SESO:COUP pot"
                self._coupling = COUPLING.POTENTIOSTATIC
            else:
                command = ":SESO:COUP gal"
                self._coupling = COUPLING.GALVANOSTATIC
        else:
            raise ValueError("invalid type for parameter `coupling`")

        return self._writeCommandToInterfaceAndReadLine(command)

    def setBandwith(self, bandwithIdx: int) -> str:
        """Set the bandwith of the device.

        The bandwidth of the device is automatically set correctly, it is not recommended to change it.

        :SCPI-COMMAND: :SESO:BAND <value>
        :param bandwith: The bandwith as index.
        :returns: The response string from the device.
        :rtype: string
        """
        return self._writeCommandToInterfaceAndReadLine(
            ":SESO:BAND " + str(bandwithIdx)
        )

    def setFilterFrequency(self, frequency: float) -> str:
        """Set the filter frequency of the device.

        The filter frequency of the device is automatically set correctly, it is not recommended to change it.

        :SCPI-COMMAND: :SESO:FILT <value>
        :param frequency: The frequency as float value.
        :returns: The response string from the device.
        :rtype: string
        """
        return self._writeCommandToInterfaceAndReadLine(":SESO:FILT " + str(frequency))

    def setParameterLimitCheckToleranceTime(self, time: float) -> str:
        """Setting the time for which operation outside the limits is allowed.

        By default this parameter is 0.
        It will be aborted at the latest at the next integer multiple of the sampling period duration.
        For this time, it is allowed to exceed or fall below the functional parameter current and voltage limits.

        Enter the parameter as for :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.setTimeParameter`.

        :SCPI-COMMAND: :PARA:UILT <value>
        :param time: The time in seconds.
        :returns: The response string from the device.
        :rtype: string
        """
        time = self._processTimeInput(time)
        return self._writeCommandToInterfaceAndReadLine(":PARA:UILT " + str(time))

    def setMinMaxVoltageParameterCheckEnabled(self, state: bool = True) -> str:
        """Switch voltage check on or off.

        The voltage is absolute and independent of OCP/OCV.

        When switched on, the voltage is checked in galvanostatic primitives, such as ramps or galvanostatic polarization.
        When the limit is reached, it continues to the next primitive and the state of the device is ok and it has no error.

        This can be used, for example, to apply a constant current until a voltage is reached.
        This is used in the method :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.measureCharge`.

        :SCPI-COMMAND: :PARA:ULIM:STAT <ON|OFF>
        :param state: The state of check. True means turned on.
        :returns: The response string from the device.
        :rtype: string
        """
        return self._writeCommandToInterfaceAndReadLine(
            ":PARA:ULIM:STAT ON" if state else ":PARA:ULIM:STAT OFF"
        )

    def setMinMaxCurrentParameterCheckEnabled(self, state: bool = True) -> str:
        """Switch current check on or off.

        The current is absolute with sign.

        When switched on, the current is checked in potentiostatic primitives, such as ramps or polarization.
        When the limit is reached, it continues to the next primitive and the state of the device is
        ok and it has no error.

        This can be used, for example, to wait until the voltage is only as small as required (settling process).

        :SCPI-COMMAND: :PARA:ILIM:STAT <ON|OFF>
        :param state: The state of check. True means turned on.
        :returns: The response string from the device.
        :rtype: string
        """
        return self._writeCommandToInterfaceAndReadLine(
            ":PARA:ILIM:STAT ON" if state else ":PARA:ILIM:STAT OFF"
        )

    def setMaximumVoltageParameter(self, value: float) -> str:
        """Set the maximum voltage parameter for primitives.

        The voltage is absolute and independent of OCP/OCV.

        If the monitoring is switched on, the primitive is successfully aborted when
        the maximum voltage is exceeded or the minimum voltage is undershot.
        It returns with the response ok.

        :SCPI-COMMAND: :PARA:ULIM:MAX <value>
        :param value: The voltage value.
        :returns: The response string from the device.
        :rtype: string
        """
        return self._writeCommandToInterfaceAndReadLine(":PARA:ULIM:MAX " + str(value))

    def setMinimumVoltageParameter(self, value: float) -> str:
        """Set the minimum voltage parameter for primitives.

        The voltage is absolute and independent of OCP/OCV.

        If the monitoring is switched on, the primitive is successfully aborted when
        the maximum voltage is exceeded or the minimum voltage is undershot.
        It returns with the response ok.

        :SCPI-COMMAND: :PARA:ULIM:MIN <value>
        :param value: The voltage value.
        :returns: The response string from the device.
        :rtype: string
        """
        return self._writeCommandToInterfaceAndReadLine(":PARA:ULIM:MIN " + str(value))

    def setMaximumCurrentParameter(self, value: float) -> str:
        """Set the maximum currerent parameter for primitives.

        The current is absolute with sign.

        If the monitoring is switched on, the primitive is successfully aborted when
        the maximum current is exceeded or the minimum current is undershot.
        It returns with the response ok.

        :SCPI-COMMAND: :PARA:ILIM:MAX <value>
        :param value: The current value.
        :returns: The response string from the device.
        :rtype: string
        """
        return self._writeCommandToInterfaceAndReadLine(":PARA:ILIM:MAX " + str(value))

    def setMinimumCurrentParameter(self, value: float) -> str:
        """Set the minimum current parameter for primitives.

        The current is absolute with sign.

        If the monitoring is switched on, the primitive is successfully aborted when
        the maximum current is exceeded or the minimum current is undershot.
        It returns with the response ok.

        :SCPI-COMMAND: :PARA:ILIM:MAX <value>
        :param value: The current value.
        :returns: The response string from the device.
        :rtype: string
        """
        return self._writeCommandToInterfaceAndReadLine(":PARA:ILIM:MIN " + str(value))

    def setGlobalLimitCheckToleranceTime(self, time: float) -> str:
        """Setting the time for which operation outside the limits is allowed.

        By default this parameter is 0.
        It will be aborted at the latest at the next integer multiple of the sampling period duration.
        For this time, it is allowed to exceed or fall below the global current and voltage limits.

        Enter the parameter as for :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.setTimeParameter`.

        :SCPI-COMMAND: :SESO:UILT <value>
        :param state: The time in seconds.
        :returns: The response string from the device.
        :rtype: string
        """
        time = self._processTimeInput(time)
        return self._writeCommandToInterfaceAndReadLine(":SESO:UILT " + str(time))

    def setGlobalVoltageCheckEnabled(self, state: bool = True) -> str:
        """Switch global voltage check on or off.

        The voltage is absolute and independent of OCP/OCV.

        When this is enabled, the voltage in potentiostatic and galvanostatic is checked for the global limits.
        If the limits are exceeded, the potentiostat is switched off and the primitive returns an error condition.

        New primitives cannot be measured until the error state of the device has been reset.
        The state can be reset with :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.clearState`.

        :SCPI-COMMAND: :SESO:ULIM:STAT <ON|OFF>
        :param state: The state of check. True means turned on.
        :returns: The response string from the device.
        :rtype: string
        """
        return self._writeCommandToInterfaceAndReadLine(
            ":SESO:ULIM:STAT ON" if state else ":SESO:ULIM:STAT OFF"
        )

    def setGlobalCurrentCheckEnabled(self, state: bool = True) -> str:
        """Switch global current check on or off.

        The current is absolute with sign.

        When this is enabled, the current in potentiostatic and galvanostatic is checked for the global limits.
        If the limits are exceeded, the potentiostat is switched off and the primitive returns an error condition.

        New primitives cannot be measured until the error state of the device has been reset.
        The state can be reset with :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.clearState`.

        :SCPI-COMMAND: :SESO:ILIM:STAT <ON|OFF>
        :param state: The state of check. True means turned on.
        :returns: The response string from the device.
        :rtype: string
        """
        return self._writeCommandToInterfaceAndReadLine(
            ":SESO:ILIM:STAT ON" if state else ":SESO:ILIM:STAT OFF"
        )

    def setMaximumVoltageGlobal(self, value: float) -> str:
        """Set the maximum voltage for the device.

        The voltage is absolute and independent of OCP/OCV.

        If the monitoring is switched on, the primitive is aborted when
        the maximum voltage is exceeded or the minimum voltage is undershot.

        :SCPI-COMMAND: :SESO:ULIM:MAX <value>
        :param value: The voltage value.
        :returns: The response string from the device.
        :rtype: string
        """
        return self._writeCommandToInterfaceAndReadLine(":SESO:ULIM:MAX " + str(value))

    def setMinimumVoltageGlobal(self, value: float) -> str:
        """Set the minimum voltage for the device.

        The voltage is absolute and independent of OCP/OCV.

        If the monitoring is switched on, the primitive is aborted when
        the maximum voltage is exceeded or the minimum voltage is undershot.

        :SCPI-COMMAND: :SESO:ULIM:MIN <value>
        :param value: The voltage value.
        :returns: The response string from the device.
        :rtype: string
        """
        return self._writeCommandToInterfaceAndReadLine(":SESO:ULIM:MIN " + str(value))

    def setMaximumCurrentGlobal(self, value: float) -> str:
        """Set the maximum current for the device.

        The current is absolute with sign.

        If the monitoring is switched on, the primitive is aborted when
        the maximum current is exceeded or the minimum voltage is undershot.

        :SCPI-COMMAND: :SESO:ILIM:MAX <value>
        :param value: The current value.
        :returns: The response string from the device.
        :rtype: string
        """
        return self._writeCommandToInterfaceAndReadLine(":SESO:ILIM:MAX " + str(value))

    def setMinimumCurrentGlobal(self, value: float) -> str:
        """Set the minimum current for the device.

        The current is absolute with sign.

        If the monitoring is switched on, the primitive is aborted when
        the maximum current is exceeded or the minimum voltage is undershot.

        :SCPI-COMMAND: :SESO:ILIM:MIN <value>
        :param value: The current value.
        :returns: The response string from the device.
        :rtype: string
        """
        return self._writeCommandToInterfaceAndReadLine(":SESO:ILIM:MIN " + str(value))

    def setSamplingFrequency(self, frequency: float) -> str:
        """Set the the sampling frequency.

        This frequency is used for all primitives except IE stairs.

        :SCPI-COMMAND: :SESO:SFRQ <value>
        :param frequency: The sampling frequency in Hz.
        :returns: The response string from the device.
        :rtype: string
        """
        return self._writeCommandToInterfaceAndReadLine(":SESO:SFRQ " + str(frequency))

    def setToleranceBreakEnabled(self, value: bool = True) -> str:
        """Allowing tolerance break for primitive.

        The primitive potentiostatic and galvanostatic polarization or OCVScan can be aborted if the absolute change tolerance
        has been fallen below. In the case of IE steps, this applies to the individual steps of the primitive.

        The tolerances apply to the complementary quantity, i.e. potentiostatic to current changes
        and galvanostatic to voltage changes. OCV it is related to the voltage.

        The absolute tolerances are always in V/s or A/s.
        The relative tolerance is a factor of 1/s.
        The current change is divided by the size at the start and is therefore set in the relative
        ratio of the start size at primitve start.

        The tolerances are calculated according to the following formulas, where X is current or
        voltage as the case requires.

        Absolute Tolerance = (Xn-Xn-1)/(tn-tn-1)
        Relative Tolerance = (Absolute Tolerance)/(X0)

        :SCPI-COMMAND: :PARA:TOL:STAT <0|1>
        :param value: The sate of tolerance break. True means enabled.
        :returns: The response string from the device.
        :rtype: string
        """
        return self._writeCommandToInterfaceAndReadLine(
            ":PARA:TOL:STAT 1" if value else ":PARA:TOL:STAT 0"
        )

    def setAbsoluteTolerance(self, value: float) -> str:
        """Set the absolute tolerance.

        Documentation is with the method :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.setToleranceBreakEnabled`.

        :SCPI-COMMAND: :PARA:TOL:ABS <value>
        :param value: The value of absolute tolerance in V/s or A/s.
        :returns: The response string from the device.
        :rtype: string
        """
        return self._writeCommandToInterfaceAndReadLine(":PARA:TOL:ABS " + str(value))

    def setRelativeTolerance(self, value: float) -> str:
        """Set the relative tolerance.

        Documentation is with the method :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.setToleranceBreakEnabled`.

        :SCPI-COMMAND: :PARA:TOL:REL <value>
        :param value: The value of relative tolerance in 1/s.
        :returns: The response string from the device.
        :rtype: string
        """
        return self._writeCommandToInterfaceAndReadLine(":PARA:TOL:REL " + str(value))

    def setChargeBreakEnabled(self, value: bool = True) -> str:
        """Allowing charge break for primitive.

        With primitive potentiostatic and galvanostatic polarization, you can set an upper charge limit and a lower
        charge limit. These are absolute signed values.

        For each primitive these values count separately and for each primitive the charge starts at 0.

        If you want to know the charge, the current must be integrated manually.

        :SCPI-COMMAND: :PARA:CHAR:STAT <0|1>
        :param value: The sate of charge break. True means enabled.
        :returns: The response string from the device.
        :rtype: string
        """
        return self._writeCommandToInterfaceAndReadLine(
            ":PARA:CHAR:STAT 1" if value else ":PARA:CHAR:STAT 0"
        )

    def setMaximumCharge(self, value: float) -> str:
        """Set the maximum charge parameter for primitives.

        If the monitoring is switched on, the primitive is successfully aborted when
        the maximum charge is exceeded or the minimum charge is undershot.
        It returns with the response ok.

        :SCPI-COMMAND: :PARA:CHAR:MAX <value>
        :param value: The charge value.
        :returns: The response string from the device.
        :rtype: string
        """
        return self._writeCommandToInterfaceAndReadLine(":PARA:CHAR:MAX " + str(value))

    def setMinimumCharge(self, value: float) -> str:
        """Set the minimum charge parameter for primitives.

        If the monitoring is switched on, the primitive is successfully aborted when
        the maximum charge is exceeded or the minimum charge is undershot.
        It returns with the response ok.

        :SCPI-COMMAND: :PARA:CHAR:MIN <value>
        :param value: The charge value.
        :returns: The response string from the device.
        :rtype: string
        """
        return self._writeCommandToInterfaceAndReadLine(":PARA:CHAR:MIN " + str(value))

    def getTemperature(self) -> float:
        """Read temperatur from the connected thermoelement.

        For this command, a thermocouple must be connected to the back of the device.
        Otherwise an exception is thrown because the response string contains the text
        that no temperature sensor is connected.

        This is used to query the temperature. A recording of the temperature during measurements
        is not yet supported.

        :SCPI-COMMAND: :MEAS:TEMP?
        :returns: The measured temperature in degree celsius.
        :rtype: float
        """
        return self._writeCommandToInterfaceAndReadValue(":MEAS:TEMP?")

    def setStepSize(self, value: float) -> str:
        """Set the step size for primitives.

        This parameter is used only by the IEStairs.
        It can be the step size in V for potentiostatic stairs or in A for galvanostatic stairs.

        :SCPI-COMMAND: :PARA:STEP <value>
        :param value: The step size in V or A.
        :returns: The response string from the device.
        :rtype: string
        """
        return self._writeCommandToInterfaceAndReadLine(":PARA:STEP " + str(value))

    def measureRampValueInTime(
        self,
        targetValue: Optional[float] = None,
        duration: Optional[float] = None,
    ) -> str:
        """Measuring a ramp with a target value in a duration.

        Potentiostatic or galvanostatic ramps are possible. With these ramps, the device selects the
        step size as small as possible.

        Before starting the ramp, a setpoint must always be specified, at which the ramp then starts.
        It is not necessary to switch on the potentiostat, it is sufficient to set a voltage value
        with the method :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.setVoltageValue`
        or a current value with the method :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.setCurrentValue`,
        depending on whether the ramp is galvanostatic or potentiostatic. Alternatively, the ramp
        starts from the final value of the last executed pimitive.
        However, if the last primitive had a different coupling, a new value must be specified.
        Within the duration the targetValue is then driven.

        If targetValue is not specified, the value from the last method call of :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.setVoltageParameter`
        or :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.setCurrentParameter` is used, depending on how the coupling was set when the call was made.
        The same applies to duration there the value of the method :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.setTimeParameter` is used.

        The ramp can be aborted with the minimum or maximum values.

        In addition to the dead time at the end of the ramp, as with all primitives, there are a few
        milliseconds at the beginning of the ramp that are needed to initialize the ramp, this is not
        necessary with POGA for example.

        Used setup methods/parameters:

        * :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.setCoupling`
        * :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.setVoltageParameterRelation`
        * :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.setVoltageParameter`
        * :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.setCurrentParameter`
        * :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.setTimeParameter`
        * :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.setMinMaxVoltageParameterCheckEnabled`
        * :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.setMinMaxCurrentParameterCheckEnabled`
        * :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.setMaximumVoltageParameter`
        * :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.setMinimumVoltageParameter`
        * :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.setMaximumCurrentParameter`
        * :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.setMinimumCurrentParameter`

        :SCPI-COMMAND: :MEAS:RMPT?
        :param targetValue: The target targetValue or None to use the old parameter.
        :param duration: The duration of the ramp or None to use the old time parameter.
        :returns: The response string from the device.
        :rtype: string
        """
        if duration != None:
            self.setTimeParameter(duration)
        if targetValue != None:
            if self._coupling == COUPLING.GALVANOSTATIC:
                self.setCurrentParameter(targetValue)
            else:
                self.setVoltageParameter(targetValue)
        return self._writeCommandToInterfaceAndReadLine(":MEAS:RMPT?")

    def measureRampValueInScanRate(
        self,
        targetValue: Optional[float] = None,
        scanrate: Optional[float] = None,
    ) -> str:
        """Measuring a ramp to a target value with a scanrate.

        Potentiostatic or galvanostatic ramps are possible. With these ramps, the device selects the
        step size as small as possible.

        Before starting the ramp, a setpoint must always be specified, at which the ramp then starts.
        It is not necessary to switch on the potentiostat, it is sufficient to set a voltage value
        with the method :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.setVoltageValue`
        or a current value with the method :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.setCurrentValue`,
        depending on whether the ramp is galvanostatic or potentiostatic. Alternatively, the ramp
        starts from the final value of the last executed pimitive.
        However, if the last primitive had a different coupling, a new value must be specified.

        If targetValue is not specified, the targetValue from the last method call of :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.setVoltageParameter`
        or :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.setCurrentParameter` is used, depending on how the coupling was set when the call was made.
        The same applies to scanrate there the last value of the method :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.setScanRateParameter` is used.

        The absolute value of the scan rate is used. The unit is in V/s or A/s depending on whether
        the command is called galvanostatically or potentiostatically.

        The ramp can be aborted with the minimum or maximum values.

        In addition to the dead time at the end of the ramp, as with all primitives, there are a few
        milliseconds at the beginning of the ramp that are needed to initialize the ramp, this is not
        necessary with POGA for example.

        Used setup methods/parameters:

        * :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.setCoupling`
        * :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.setVoltageParameterRelation`
        * :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.setVoltageParameter`
        * :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.setCurrentParameter`
        * :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.setScanRateParameter`
        * :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.setMinMaxVoltageParameterCheckEnabled`
        * :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.setMinMaxCurrentParameterCheckEnabled`
        * :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.setMaximumVoltageParameter`
        * :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.setMinimumVoltageParameter`
        * :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.setMaximumCurrentParameter`
        * :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.setMinimumCurrentParameter`

        :SCPI-COMMAND: :MEAS:RMPS?
        :param targetValue: The target targetValue or None to use the old parameter.
        :param scanrate: The scanrate to the target value.
        :returns: The response string from the device.
        :rtype: string
        """
        if scanrate != None:
            self.setScanRateParameter(scanrate)
        if targetValue != None:
            if self._coupling == COUPLING.GALVANOSTATIC:
                self.setCurrentParameter(targetValue)
            else:
                self.setVoltageParameter(targetValue)
        return self._writeCommandToInterfaceAndReadLine(":MEAS:RMPS?")

    def measureRampScanRateForTime(
        self,
        scanrate: Optional[float] = None,
        time: Optional[float] = None,
    ) -> str:
        """Measuring with a scanrate for a time.

        Potentiostatic or galvanostatic ramps are possible. With these ramps,
        the device selects the step size as small as possible.

        Before starting the ramp, a setpoint must always be specified, at which the ramp then starts.
        It is not necessary to switch on the potentiostat, it is sufficient to set a voltage value
        with the method :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.setVoltageValue`
        or a current value with the method :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.setCurrentValue`,
        depending on whether the ramp is galvanostatic or potentiostatic. Alternatively, the ramp
        starts from the final value of the last executed pimitive.
        However, if the last primitive had a different coupling, a new value must be specified.

        If the scanrate is not specified the last value of the method :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.setScanRateParameter` is used.
        The same applies to duration where the value of the method :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.setTimeParameter` is used.

        Here the sign of the ramp is important and indicates the direction of the ramp.
        The unit is in V/s or A/s depending on whether the command is called galvanostatic or potentiostatic.

        The ramp can be aborted with the minimum or maximum values.

        In addition to the dead time at the end of the ramp, as with all primitives, there are a few
        milliseconds at the beginning of the ramp that are needed to initialize the ramp, this is not
        necessary with POGA for example.

        Used setup methods/parameters:

        * :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.setCoupling`
        * :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.setTimeParameter`
        * :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.setScanRateParameter`
        * :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.setMinMaxVoltageParameterCheckEnabled`
        * :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.setMinMaxCurrentParameterCheckEnabled`
        * :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.setMaximumVoltageParameter`
        * :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.setMinimumVoltageParameter`
        * :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.setMaximumCurrentParameter`
        * :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.setMinimumCurrentParameter`

        :SCPI-COMMAND: :MEAS:RMPV?
        :param targetValue: The target targetValue or None to use the old target targetValue.
        :param scanrate: The scanrate to the target value.
        :returns: The response string from the device.
        :rtype: string
        """
        if time != None:
            self.setTimeParameter(time)
        if scanrate != None:
            self.setScanRateParameter(scanrate)
        return self._writeCommandToInterfaceAndReadLine(":MEAS:RMPV?")

    def measurePolarization(self) -> str:
        """POGA - Measurement of a potentiostatic or galvanostatic polarization.

        This primitive outputs constant current or constant voltage for a maximum time, depending on
        what has been set.

        However, the primitive can be aborted prematurely if the complementary quantity, e.g. the
        current in potentiostatic operation, exceeds a specified maximum current or falls below a
        minimum current.

        Likewise, the primitive can be aborted prematurely when the change of the complementary
        quantity per time has fallen below a set value. For the abortion on a change, one can still
        set a minimum duration of the primitive, which expires before the tolerance is checked.

        With primitive potentiostatic and galvanostatic polarization, you can set an upper charge limit and a lower
        charge limit. These are absolute signed values. For each primitive these values count
        separately and for each primitive the charge starts at 0.

        Used setup methods/parameters:

        * :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.setCoupling`
        * :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.setVoltageParameterRelation`
        * :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.setVoltageParameter`
        * :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.setCurrentParameter`
        * :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.setMaximumTimeParameter`
        * :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.setMinMaxVoltageParameterCheckEnabled`
        * :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.setMinMaxCurrentParameterCheckEnabled`
        * :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.setMaximumVoltageParameter`
        * :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.setMinimumVoltageParameter`
        * :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.setMaximumCurrentParameter`
        * :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.setMinimumCurrentParameter`
        * :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.setToleranceBreakEnabled`
        * :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.setMinimumTimeParameter`
        * :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.setAbsoluteTolerance`
        * :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.setRelativeTolerance`
        * :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.setChargeBreakEnabled`
        * :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.setMaximumCharge`
        * :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.setMinimumCharge`


        :SCPI-COMMAND: :MEAS:POGA?
        :returns: The response string from the device.
        :rtype: string
        """
        return self._writeCommandToInterfaceAndReadLine(":MEAS:POGA?")

    def measureOCVScan(self) -> str:
        """Measurement of open circuit voltage over time

        However, the primitive can be aborted prematurely if the voltage in potentiostatic operation,
        exceeds a  maximum or falls below a minimum.

        Likewise, the primitive can be aborted prematurely when the change of the voltage per time
        has fallen below a set value. For the abortion on a change, one can still set a minimum
        duration of the primitive, which expires before the tolerance is checked.

        Used setup methods/parameters:

        * :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.setMaximumTimeParameter`
        * :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.setMinMaxVoltageParameterCheckEnabled`
        * :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.setMinMaxCurrentParameterCheckEnabled`
        * :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.setMaximumVoltageParameter`
        * :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.setMinimumVoltageParameter`
        * :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.setMaximumCurrentParameter`
        * :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.setMinimumCurrentParameter`
        * :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.setToleranceBreakEnabled`
        * :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.setMinimumTimeParameter`
        * :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.setAbsoluteTolerance`
        * :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.setRelativeTolerance`

        :SCPI-COMMAND: :MEAS:OCVS?
        :returns: The response string from the device.
        :rtype: string
        """
        return self._writeCommandToInterfaceAndReadLine(":MEAS:OCVS?")

    def measureOCV(self) -> str:
        """Measurement of open circuit voltage.

        The potentiostat is automatically switched off by this method.

        This method measures the open circuit voltage, and sets this open circuit voltage as a
        reference for subsequent measurements when a voltage is to be referenced to OCV.

        :SCPI-COMMAND: :MEAS:OCV?
        :returns: The open circuit voltage.
        :rtype: float
        """
        return self._writeCommandToInterfaceAndReadValue(":MEAS:OCV?")

    def measureIEStairs(self) -> str:
        """Measurement of a voltage or current staircase.

        This primitive outputs a voltage or current staircase from the current current or voltage
        value to a target value.

        By default, only one measured value is recorded at the end of the step. The duration and
        size of the step can be set. As with polarization, change tolerances and a minimum time after
        which the next step is continued can also be set.

        However, the primitive can be aborted prematurely if the complementary quantity, e.g. the
        current in potentiostatic operation, exceeds a specified maximum current or falls below a
        minimum current.

        Used setup methods/parameters:

        * :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.setCoupling`
        * :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.setVoltageParameterRelation`
        * :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.setVoltageParameter`
        * :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.setCurrentParameter`
        * :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.setMaximumTimeParameter`
        * :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.setMinMaxVoltageParameterCheckEnabled`
        * :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.setMinMaxCurrentParameterCheckEnabled`
        * :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.setMaximumVoltageParameter`
        * :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.setMinimumVoltageParameter`
        * :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.setMaximumCurrentParameter`
        * :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.setMinimumCurrentParameter`
        * :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.setToleranceBreakEnabled`
        * :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.setMinimumTimeParameter`
        * :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.setAbsoluteTolerance`
        * :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.setRelativeTolerance`


        :SCPI-COMMAND: :MEAS:IESC?
        :returns: The response string from the device.
        :rtype: string
        """
        return self._writeCommandToInterfaceAndReadLine(":MEAS:IESC?")

    """
    Method which were composed from primitve as an example.
    """

    def checkConnectionPolarity(self) -> bool:
        """Check that the object is connected with the correct polarity.

        This function is only to simplify the development of measurement methods from primitives,
        for example, that a battery has a positive open circuit voltage.
        This eliminates the need to handle cases when the OCV is negative, making everything clearer
        and simpler.

        :returns: True if the polarity is correct, else raise ValueError().
        :rtype: float
        """
        voltage = self.getVoltage()
        if voltage < 0:
            raise ValueError("OCP/OCV must be positive. Change polarity.")
        return True

    def measureCharge(
        self,
        current: float,
        stopVoltage: float,
        maximumTime: Union[float, str],
        minimumVoltage: float = 0,
    ) -> str:
        """Charge an object.

        It is charged with a positive current until a maximum voltage is reached. A maximum
        time can also be defined. In theory, you should not need the minimum voltage, as the voltage
        should increase during charging.

        Global limits can be defined outside this method before the function call. Where the limits
        should be chosen slightly larger, that the functional terminations with the lower priority
        are used instead of the global terminations.

        :param current: The charging current. The absolute value is used.
        :param stopVoltage: The voltage up to which charging is to take place.
        :param maximumTime: The maximum charging time.
        :param minimumVoltage: You should not need the minimum voltage, as the voltage should
                    increase during charging.
        :returns: The response string from the device, from :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.measurePolarization`.
        :rtype: string
        """
        self.checkConnectionPolarity()
        self.setCoupling("gal")
        if current < 0:
            raise ValueError("The current must be positive.")
        self.setCurrentParameter(abs(current))
        self.setMaximumVoltageParameter(stopVoltage)
        self.setMinimumTimeParameter(0)
        self.setMaximumTimeParameter(maximumTime)
        self.setMinimumVoltageParameter(minimumVoltage)
        self.setMinMaxVoltageParameterCheckEnabled(True)
        return self.measurePolarization()

    def measureDischarge(
        self,
        current: float,
        stopVoltage: float,
        maximumTime: Union[float, str],
        maximumVoltage: Union[float, str] = 1000,
    ) -> str:
        """Discharge an object.

        It is discharged with a negative current until a minimum voltage is reached. A maximum
        time can also be defined. In theory, you should not need the maximum voltage, as the voltage
        should decrease during discharging.

        Global limits can be defined outside this method before the function call. Where the limits
        should be chosen slightly larger, that the functional terminations with the lower priority
        are used instead of the global terminations.

        :param current: The discharging current. The absolute value * -1.0 is used.
        :param stopVoltage: The voltage down to which discharging is to take place.
        :param maximumTime: The maximum charging time.
        :param maximumVoltage: You should not need the maximum voltage, as the voltage should
                    decrease during discharging.
        :returns: The response string from the device, from :func:`~zahner_potentiostat.scpi_control.control.SCPIDevice.measurePolarization`.
        :rtype: string
        """
        self.checkConnectionPolarity()
        self.setCoupling("gal")
        if current > 0:
            raise ValueError("The current must be negative.")
        self.setCurrentParameter(-1 * abs(current))
        self.setMinimumVoltageParameter(stopVoltage)
        self.setMaximumVoltageParameter(maximumVoltage)
        self.setMinimumTimeParameter(0)
        self.setMaximumTimeParameter(maximumTime)
        self.setMinMaxVoltageParameterCheckEnabled(True)
        return self.measurePolarization()

    def measureProfile(
        self,
        profileDict: list[dict[str, float]],
        coupling: COUPLING,
        scalingFactor: float = 1,
        outputPrimitive: str = "pol",
    ) -> None:
        """Output a sequence of POGA or ramps.

        With this command a defined number of potentiostatic or galvanostatic polarizations or ramps can be output
        one after the other. Galvanostatic and potentiostatic cannot be mixed at the moment.

        The profile must be passed with the following data structure:
            [{"time": 0, "value": 0.1},{"time": 1, "value": 0.4},{"time": 2, "value": 0.3}]

        The structure is an array with a dictionary for each step. The dictionary has two keys:
            time: The time point of the value.
            value: The value, current or voltage, depending on the parameter coupling.

        There is also an example to import data from an drive cycle.
        driveCycle = :func:`~zahner_potentiostat.drivecycle.cycle_importer.getNormalisedCurrentTableForHUDDSCOL`

        Note that this method is composed of calls to the individual primitives including their limitations
        and peculiarities. Short dead times where no measurements are taken for data processing.

        :param profileDict: Profile support points, see documentation above.
        :param coupling: Coupling of measurement.
        :type coupling: :class:`~zahner_potentiostat.scpi_control.control.COUPLING`
        :param scalingFactor: Multiplier for the values from the dictionary, default 1, especially
                for current normalization. But can also be used to multiply the voltage by a factor.
        :param outputPrimitive: Default "pol" that means POGA, but "ramp" is also possible.
        :rtype: None
        """
        timestamp = profileDict[0]["time"]
        value = profileDict[0]["value"]
        lastTime = -100

        self.setCoupling(coupling)
        self.setMinimumTimeParameter(0)
        if self._coupling == COUPLING.GALVANOSTATIC:
            self.setCurrentParameter(value * scalingFactor)
        else:
            self.setVoltageParameter(value * scalingFactor)
        self.setPotentiostatEnabled(True)

        for point in profileDict[1:]:
            nextTimestamp = point["time"]
            if self._coupling == COUPLING.GALVANOSTATIC:
                self.setCurrentParameter(value * scalingFactor)
            else:
                self.setVoltageParameter(value * scalingFactor)

            time = nextTimestamp - timestamp
            if "pol" in outputPrimitive:
                if time != lastTime:
                    self.setMaximumTimeParameter(time)
                self.measurePolarization()
            else:
                if time != lastTime:
                    self.setTimeParameter(time)
                self.measureRampValueInTime()
            lastTime = time
            value = point["value"]
            timestamp = nextTimestamp

        self.setPotentiostatEnabled(False)
        return

    def measurePITT(
        self,
        targetVoltage: float,
        endVoltage: float,
        stepVoltage: float,
        onTime: Union[float, str],
        openCircuitTime: Union[float, str],
        startWithOCVScan: bool = True,
        measureOnTargetVoltage: bool = False,
    ) -> None:
        """PITT - Potentiostatic Intermittent Titration Technique

        This is a simple basic implementation of PITT.
        Global current and voltage interrupts can be set outside the method.
        The functionality can be easily extended by additional parameters of the methods, such as
        abort on change tolerances.

        :param targetVoltage: The upper reverse voltage.
        :param endVoltage: The voltage to finish the measurement.
        :param stepVoltage: The voltage  step size.
        :param onTime: The time for the constant voltage phase.
        :param openCircuitTime: The time for open circuit phase.
        :param startWithOCVScan: Start with scan of the start potential, if false start with first step.
        :param measureOnTargetVoltage: if True, then a measurement is made on the target voltage,
            depending on the step size, the last step can then be smaller. If False, then the
            last voltage measurement points can be between targetVoltage and
            (targetVoltage - stepVoltage) size. With false the points are on the same
            potential in the up and down cycle.
        :rtype: None
        """

        """
        Prepare Measurement
        Charge break and Tolerance break are not supported.
        """
        self.checkConnectionPolarity()
        if stepVoltage <= 0:
            raise ValueError("Step size must be bigger than 0.")
        self.setMinimumTimeParameter(0)
        self.setChargeBreakEnabled(False)
        self.setToleranceBreakEnabled(False)
        self.setCoupling("pot")
        self.setVoltageParameterRelation(RELATION.ZERO)
        self.setParameterLimitCheckToleranceTime(0.1)

        currentVoltage = self.measureOCV()
        """
        Up Cycle
        """
        if startWithOCVScan:
            self.setMaximumTimeParameter(openCircuitTime)
            self.measureOCVScan()

        currentVoltage += stepVoltage
        while currentVoltage <= targetVoltage:
            self.setMaximumTimeParameter(onTime)
            self.setVoltageParameter(currentVoltage)
            self.measurePolarization()
            self.setMaximumTimeParameter(openCircuitTime)
            self.measureOCVScan()
            currentVoltage += stepVoltage

        """
        Down Cycle
        """
        if measureOnTargetVoltage == True:
            currentVoltage = targetVoltage
        else:
            currentVoltage -= 2 * stepVoltage
        while currentVoltage >= endVoltage:
            self.setMaximumTimeParameter(onTime)
            self.setVoltageParameter(currentVoltage)
            self.measurePolarization()
            self.setMaximumTimeParameter(openCircuitTime)
            self.measureOCVScan()
            currentVoltage -= stepVoltage

        self.setPotentiostatEnabled("off")
        return

    def measureGITT(
        self,
        targetVoltage: float,
        endVoltage: float,
        current: float,
        onTime: Union[float, str],
        openCircuitTime: Union[float, str],
        startWithOCVScan: bool = False,
    ) -> None:
        """GITT - Galvanostatic Intermittent Titration Technique

        This is a simple basic implementation of PITT.
        The functionality can be easily extended by additional parameters of the methods, such as
        abort on change tolerances.

        The software voltage limit of the device is used as the voltage limit. If this is exceeded,
        the device returns an error condition. This error condition must be reset for further measurement.
        To avoid false triggering of the limits, the limits that are not required are switched over.

        :param targetVoltage: The upper reverse voltage.
        :param endVoltage: The voltage to finish the measurement.
        :param current: The value of current.
        :param onTime: The time for the constant voltage phase.
        :param openCircuitTime: The time for open circuit phase.
        :param startWithOCVScan: Start with scan of the start potential, if false start with first step.
        :rtype: None
        """
        """
        Prepare Measurement
        Charge break and Tolerance break are not supported.
        """
        self.checkConnectionPolarity()
        self.setMinimumTimeParameter(0)
        self.setChargeBreakEnabled(False)
        self.setToleranceBreakEnabled(False)
        self.setCoupling("gal")
        self.setCurrentParameter(abs(current))
        self.setParameterLimitCheckToleranceTime(0.1)
        self.setGlobalLimitCheckToleranceTime(0.1)

        """
        The errors are needed by this function and are processed.
        Error 12 means limit reached.
        """
        oldRaiseOnErrorState = self.getRaiseOnErrorEnabled()
        self.setRaiseOnErrorEnabled(False)

        self.setMinMaxCurrentParameterCheckEnabled(False)
        self.setMinMaxVoltageParameterCheckEnabled(False)

        answerFromDevice = ""
        currentVoltage = self.measureOCV()

        self.setMaximumVoltageGlobal(targetVoltage)
        if currentVoltage > endVoltage:
            """
            Set the limit slightly lower to avoid erroneous errors.
            """
            self.setMinimumVoltageGlobal(endVoltage * 0.9)
        else:
            self.setMinimumVoltageGlobal(currentVoltage * 0.9)
        self.setGlobalVoltageCheckEnabled(True)
        self.setGlobalCurrentCheckEnabled(False)

        """
        Up Cycle - Charge
        """
        if startWithOCVScan:
            self.setMaximumTimeParameter(openCircuitTime)
            self.measureOCVScan()

        while "error" not in answerFromDevice:
            self.setMaximumTimeParameter(onTime)
            answerFromDevice = self.measurePolarization()
            if "error" in answerFromDevice:
                """
                Voltage Limit Reached

                Set the limit slightly higher to avoid erroneous errors.
                The voltage should become higher as the charge is applied.
                """
                self.clearState()
                self.setMaximumVoltageGlobal(targetVoltage * 1.1)
            self.setMaximumTimeParameter(openCircuitTime)
            self.measureOCVScan()

        """
        Down Cycle - Discharge
        """
        answerFromDevice = ""
        self.setCurrentParameter(-1 * abs(current))
        self.setMinimumVoltageGlobal(endVoltage)

        while "error" not in answerFromDevice:
            self.setMaximumTimeParameter(onTime)
            answerFromDevice = self.measurePolarization()
            if "error" in answerFromDevice:
                """
                Voltage Limit Reached

                Set the limit slightly lower to avoid erroneous errors.
                """
                self.clearState()
                self.setMinimumVoltageGlobal(endVoltage * 0.9)
            self.setMaximumTimeParameter(openCircuitTime)
            self.measureOCVScan()

        self.setPotentiostatEnabled("off")

        """
        Reset the original error output.
        """
        self.setRaiseOnErrorEnabled(oldRaiseOnErrorState)
        return

    """
    Private internal used functions.
    """

    def _processTimeInput(self, time: Union[float, str]) -> float:
        """Private function to process time inputs.

        This function processes the input to a floating point number with a time specification in
        seconds. All methods which set time parameters process the parameter with this method.

        Times can then be passed as in the following examples:

        * _processTimeInput(3.1415)         Input as seconds.
        * _processTimeInput("3.1415 s")     Input as seconds.
        * _processTimeInput("3.1415 m")     Input as minutes.
        * _processTimeInput("3.1415 min")   Input as minutes.
        * _processTimeInput("3.1415 h")     Input as hours.

        :param time: Time in format as described in the previous section.
        :returns: Time in seconds as float value.
        """
        retval = None
        if isinstance(time, str):
            """
            Now interpreting the string as time to process seconds minutes and hours.
            """
            timeRegex = re.compile("([0-9]+[.,]?[0-9]*)[ ]*((min)|([mhs]))")
            timeMatch = timeRegex.match(time)
            if timeMatch.group(1) != None and timeMatch.group(2) != None:
                valueString = timeMatch.group(1)
                valueString.replace(",", ".")
                retval = float(valueString)

                if timeMatch.group(2) in "min" or timeMatch.group(2) in "m":
                    retval *= 60.0
                elif timeMatch.group(2) in "h":
                    retval *= 3600.0
            else:
                raise ValueError("Specified time incorrect")
        else:
            retval = time
        return retval

    def _writeCommandToInterfaceAndReadValue(self, string: str) -> float:
        """Private function to send a command to the device and read a float.

        This function sends the data to the device with the class SerialCommandInterface and waits
        for a response. This response is then converted to a float.

        :param string: String with command, without the line feed.
        :returns: Float value.
        :rtype: float
        """
        line = self._writeCommandToInterfaceAndReadLine(string)
        return float(line)

    def _writeCommandToInterfaceAndReadLine(self, string: str) -> str:
        """Private function to send a command to the device and read a string.

        This function sends the data to the device with the class SerialCommandInterface and waits
        for a response.

        This function also manages the possibility to send abort or reset in a second thread in
        parallel to the first request to abort the primitive or to reset the device.

        :raises ZahnerSCPIError: Error number.
        :param string: String with command, without the line feed.
        :returns: Response string from the device.
        :rtype: string
        """

        if "ABOR" in string or "*RST" in string:
            line = self._commandInterface.sendStringAndWaitForReplyString(
                string, CommandType.CONTROL
            )
        else:
            line = self._commandInterface.sendStringAndWaitForReplyString(
                string, CommandType.COMMAND
            )

        if "error" in line:
            if DEBUG == True:
                line = self._commandInterface.getLastCommandWithAnswer()
            if self._raiseOnError == True:
                errorNumber = 42  # undefined error
                numberRegex = re.compile(r".*?([0-9]+).*")
                numberMatch = numberRegex.match(line)
                if numberMatch.group(1) != None:
                    errorNumber = int(numberMatch.group(1))
                raise ZahnerSCPIError(errorNumber)

        return line
