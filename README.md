# zahner_potentiostat

zahner_potentiostat is a library to control external [Zahner Potentiostats](http://zahner.de/products/external-potentiostats.html) like **PP212, PP222, PP242 or a XPOT2**.

It was developed to **easily integrate** external Zahner Potentiostats into Python scripts for more **complex measurement** tasks and for **automation purposes**.

The control concept is that there are different primitives which can be combined for different electrochemical measurement methods.  
These primitives can all be configured differently to match the application. In the documentation in the respective function all possible configuration setter methods are listed.

**The following [primitives](https://en.wikipedia.org/wiki/Language_primitive) are available to compose methods with:**  
* Potentiostatic or galvanostatic polarization  
  * [measurePolarization()](http://zahner.de/documentation/zahner_potentiostat/scpi_control/control.html#zahner_potentiostat.scpi_control.control.SCPIDevice.measurePolarization)  
* Open circuit voltage/potential scan  
  * [measureOCV()](http://zahner.de/documentation/zahner_potentiostat/scpi_control/control.html#zahner_potentiostat.scpi_control.control.SCPIDevice.measureOCV)  
  * [measureOCVScan()](http://zahner.de/documentation/zahner_potentiostat/scpi_control/control.html#zahner_potentiostat.scpi_control.control.SCPIDevice.measureOCVScan)  
* Ramps potentiostatic or galvanostatic  
  * [measureRampValueInTime()](http://zahner.de/documentation/zahner_potentiostat/scpi_control/control.html#zahner_potentiostat.scpi_control.control.SCPIDevice.measureRampValueInTime)  
  * [measureRampValueInScanRate()](http://zahner.de/documentation/zahner_potentiostat/scpi_control/control.html#zahner_potentiostat.scpi_control.control.SCPIDevice.measureRampValueInScanRate)  
  * [measureRampScanRateForTime()](http://zahner.de/documentation/zahner_potentiostat/scpi_control/control.html#zahner_potentiostat.scpi_control.control.SCPIDevice.measureRampScanRateForTime)  
* Staircase potentiostatic or galvanostatic  
  * [measureIEStairs()](http://zahner.de/documentation/zahner_potentiostat/scpi_control/control.html#zahner_potentiostat.scpi_control.control.SCPIDevice.measureIEStairs)  
  

**And as an example, the following methods were developed from the primitives:**  
* Charge or discharge something  
  * [measureCharge()](http://zahner.de/documentation/zahner_potentiostat/scpi_control/control.html#zahner_potentiostat.scpi_control.control.SCPIDevice.measureCharge)  
  * [measureDischarge()](http://zahner.de/documentation/zahner_potentiostat/scpi_control/control.html#zahner_potentiostat.scpi_control.control.SCPIDevice.measureDischarge)  
* Output potentiostatic or galvanostatic profile as potentiostatic or galvanostatic polarizations or ramps  
  * [measureProfile()](http://zahner.de/documentation/zahner_potentiostat/scpi_control/control.html#zahner_potentiostat.scpi_control.control.SCPIDevice.measureProfile)  
* PITT Potentiostatic Intermittent Titration Technique  
  * [measurePITT()](http://zahner.de/documentation/zahner_potentiostat/scpi_control/control.html#zahner_potentiostat.scpi_control.control.SCPIDevice.measurePITT)  
* GITT Galvanostatic Intermittent Titration Technique  
  * [measureGITT()](http://zahner.de/documentation/zahner_potentiostat/scpi_control/control.html#zahner_potentiostat.scpi_control.control.SCPIDevice.measureGITT)  

Additional detailed documentation of the individual commands can be found in the python modules.  
The complete documentation of the individual functions can be found on the [API documentation website](http://zahner.de/documentation/zahner_potentiostat/index.html).  

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

# 📧 Haveing a question?
Send an <a href="mailto:support@zahner.de?subject=Zahner-Remote-Python Question&body=Your Message">e-mail</a> to our support team.

# ⁉️ Found a bug or missing a specific feature?
Feel free to **create a new issue** with a respective title and description on the the [Zahner-Remote-Python](https://github.com/Zahner-elektrik/Zahner-Remote-Python/issues) repository. If you already found a solution to your problem, **we would love to review your pull request**!

# ✅ Requirements
Programming is done with the latest python version at the time of commit.  
The only mandatory library is the [pySerial](https://pyserial.readthedocs.io/en/latest/) library. Also numpy and matplotlib are needed if you want to plot the data.