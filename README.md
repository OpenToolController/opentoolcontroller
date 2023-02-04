# OpenTool Controller
This software is intended to control equipment often used in the semiconductor industry
... and is also a very early version and far from complete

##Development Install
- `python3 -m venv venv` install a virtual environment
- `source venv/bin/activate`
- `pip install -r requirements.txt` install all the needed python packages
- `pip install -e .`  - install the opentoolcontroller code as a package


##Notes
- `pytest 'tests/test_device_manual_view.py' -k 'test_two' -s` - Run tests starting with test_two

This project also makes use of the hal module from LinuxCNC for IO access
- `sudo halcompile --install opentoolcontroller/HAL/hardware_sim.comp` - compiles the hal file for testing / making fake pins

