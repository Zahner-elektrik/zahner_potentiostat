# zahner_potentiostat

zahner_potentiostat is a library to control external [Zahner Potentiostats](https://zahner.de/products#external-potentiostats) like **PP212, PP222, PP242, XPOT2 or EL1002**.

It was developed to **easily integrate** external Zahner Potentiostats into Python scripts for more **complex measurement** tasks and for **automation purposes**.

The control concept is that there are different primitives which can be combined for different electrochemical measurement methods.  
These primitives can all be configured differently to match the application. In the documentation in the respective function all possible configuration setter methods are listed. The complete documentation of the functions can be found on the [API documentation website](https://doc.zahner.de/zahner_potentiostat/).  

> [!NOTE]  
> **Only with this library and a PP212, PP222, PP242, EL1002 or XPOT2 device you can not use AC methods. For AC methods like EIS a [Zennium](https://zahner.de/products#potentiostats) with [EPC](https://zahner.de/products-details/addon-cards/epc42) and the [thales_remote](https://github.com/Zahner-elektrik/Thales-Remote-Python) library is necessary.**

**The following [primitives](https://en.wikipedia.org/wiki/Language_primitive) are available to compose methods with:**  

* Potentiostatic or galvanostatic polarization  
  * [measurePolarization()](https://doc.zahner.de/zahner_potentiostat/scpi_control/control.html#zahner_potentiostat.scpi_control.control.SCPIDevice.measurePolarization)  
* Open circuit voltage/potential scan  
  * [measureOCV()](https://doc.zahner.de/zahner_potentiostat/scpi_control/control.html#zahner_potentiostat.scpi_control.control.SCPIDevice.measureOCV)  
  * [measureOCVScan()](https://doc.zahner.de/zahner_potentiostat/scpi_control/control.html#zahner_potentiostat.scpi_control.control.SCPIDevice.measureOCVScan)  
* Ramps potentiostatic or galvanostatic  
  * [measureRampValueInTime()](https://doc.zahner.de/zahner_potentiostat/scpi_control/control.html#zahner_potentiostat.scpi_control.control.SCPIDevice.measureRampValueInTime)  
  * [measureRampValueInScanRate()](https://doc.zahner.de/zahner_potentiostat/scpi_control/control.html#zahner_potentiostat.scpi_control.control.SCPIDevice.measureRampValueInScanRate)  
  * [measureRampScanRateForTime()](https://doc.zahner.de/zahner_potentiostat/scpi_control/control.html#zahner_potentiostat.scpi_control.control.SCPIDevice.measureRampScanRateForTime)  
* Staircase potentiostatic or galvanostatic  
  * [measureIEStairs()](https://doc.zahner.de/zahner_potentiostat/scpi_control/control.html#zahner_potentiostat.scpi_control.control.SCPIDevice.measureIEStairs)  
  
**And as an example, the following methods were developed from the primitives:**  

* Charge or discharge something  
  * [measureCharge()](https://doc.zahner.de/zahner_potentiostat/scpi_control/control.html#zahner_potentiostat.scpi_control.control.SCPIDevice.measureCharge)  
  * [measureDischarge()](https://doc.zahner.de/zahner_potentiostat/scpi_control/control.html#zahner_potentiostat.scpi_control.control.SCPIDevice.measureDischarge)  
* Output potentiostatic or galvanostatic profile as potentiostatic or galvanostatic polarizations or ramps  
  * [measureProfile()](https://doc.zahner.de/zahner_potentiostat/scpi_control/control.html#zahner_potentiostat.scpi_control.control.SCPIDevice.measureProfile)  
* PITT Potentiostatic Intermittent Titration Technique  
  * [measurePITT()](https://doc.zahner.de/zahner_potentiostat/scpi_control/control.html#zahner_potentiostat.scpi_control.control.SCPIDevice.measurePITT)  
* GITT Galvanostatic Intermittent Titration Technique  
  * [measureGITT()](https://doc.zahner.de/zahner_potentiostat/scpi_control/control.html#zahner_potentiostat.scpi_control.control.SCPIDevice.measureGITT)  

Further measurements like EIS and CV can be done in connection with a Zennium with the package [thales_remote](https://github.com/Zahner-elektrik/Thales-Remote-Python).

# 🔧 Installation

The package can be installed via pip.

```
pip install zahner_potentiostat
```

# 🔨 Basic Usage

```python

'''
Search the Zahner Potentiostat
'''
deviceSearcher = SCPIDeviceSearcher()
deviceSearcher.searchZahnerDevices()
commandSerial, dataSerial = deviceSearcher.selectDevice("35000")

'''
Connect to the Potentiostat
'''
ZahnerPP2x2 = SCPIDevice(SerialCommandInterface(commandSerial), SerialDataInterface(dataSerial))

'''
Setup measurement
'''
ZahnerPP2x2.setSamplingFrequency(25)
ZahnerPP2x2.setCoupling(COUPLING.POTENTIOSTATIC)
ZahnerPP2x2.setMaximumTimeParameter(15)

'''
Start measurement
'''
ZahnerPP2x2.setVoltageParameter(0)
ZahnerPP2x2.measurePolarization()
```

# 📖 Examples

The application of the library is shown in the example repository [Zahner-Remote-Python](https://github.com/Zahner-elektrik/Zahner-Remote-Python).

# 📧 Having a question?

Send an <a href="mailto:support@zahner.de?subject=Zahner-Remote-Python Question&body=Your Message">e-mail</a> to our support team.

# ⁉️ Found a bug or missing a specific feature?

Feel free to **create a new issue** with a respective title and description on the the [Zahner-Remote-Python](https://github.com/Zahner-elektrik/Zahner-Remote-Python/issues) repository. If you already found a solution to your problem, **we would love to review your pull request**!

# ✅ Requirements

Programming is done with the latest python version at the time of commit.  
The only mandatory library is the [pySerial](https://pyserial.readthedocs.io/en/latest/) library. Also numpy and matplotlib are needed if you want to plot the data.
