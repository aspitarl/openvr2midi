import shutil
import sys
import os
import argparse

config_folders_path = r'VR Config Shortcuts'
config_folders_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), config_folders_path)

choices = [f for f in os.listdir(config_folders_path) if os.path.isdir(os.path.join(config_folders_path,f))]

print(choices)

parser = argparse.ArgumentParser()
parser.add_argument("option", type=str, default='normal', choices=choices, 
    help="Which controller")


option = parser.parse_args().option

print("Switching to option: {}".format(option))


steamvr_settings_out = r'C:\Program Files (x86)\Steam\config\steamvr.vrsettings'
null_driver_out = r'C:\Program Files (x86)\Steam\steamapps\common\SteamVR\drivers\null\resources\settings\default.vrsettings'

#Run normal_nopower to keep base stations on then switch to no_hmd...not working
# option = 'normal_nopower' #Can't gt to work. Seems have to switch power settins in steamvr and nohmd cannot wake base stations.

config_folder = os.path.join(config_folders_path, option)

shutil.copy(os.path.join(config_folder, 'steamvr.vrsettings'), steamvr_settings_out)
shutil.copy(os.path.join(config_folder, 'default.vrsettings'), null_driver_out)




    
