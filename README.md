# OpenTool Controller
This software is in early development, but is intended for controlling equipment often used in the semiconductor industry.  It should be installed on a system that is setup to run LinuxCNC, and makes use of the hal modeule to control IO.

##Development Install
- `git clone https://github.com/OpenToolController/opentoolcontroller.git` Download the project 
- `cd opentoolcontroller`
- `python3 -m venv venv` make a new python virtual environment
- `source venv/bin/activate` actiate the virtural environment
- `pip install -r requirements.txt` install all the needed python packages
- `pip install -e .`  install the opentoolcontroller code as a package
- `python opentoolcontroller/main.py`  launch Open Tool Controller


##Notes
- `pytest 'tests/test_device_manual_view.py' -k 'test_two' -s` - Run tests starting with test_two

This project also makes use of the hal module from LinuxCNC for IO access
- `sudo halcompile --install opentoolcontroller/HAL/hardware_sim.comp` - compiles the hal file for testing / making fake pins

