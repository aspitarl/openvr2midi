# openvr2midi

Simple tool to pull controller coordinates with openvr and send them as midi data with rtmidi. Tested with Valve Index sending to loopMIDI. 

## Installation

`pip install -r requirements.txt`

# Overview

`steamvr_config_utils/quickswitch_steamvr.py` is a script to quickly change the configuration of steamvr between configurations as created with `new_config.py`. e.g. `python quickswitch_steamvr.py no_hmd` to switch to no_hmd mode. 

Power management needs to be turned off before starting steamvr in no_hmd mode. i.e. start steamvr in normal mode, turn off base station power management, turn off steam vr, then switch to no_hmd mode. 

`openvr2midi/midivr_gui.py` is the main program. 