# openvr2midi

Simple tool to pull controller coordinates with openvr and send them as midi data with rtmidi. Tested with Valve Index sending to loopMIDI. 

## Installation

`pip install -r requirements.txt`

# Overview

`steamvr_config_utils/quickswitch_steamvr.py` is a script to quickly change the configuration of steamvr between configurations as created with `new_config.py`. e.g. `python quickswitch_steamvr.py no_hmd` to switch to no_hmd mode. 

`openvr2midi/midivr_gui.py` is the main program. 