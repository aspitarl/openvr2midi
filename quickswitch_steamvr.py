import shutil
import sys
import os

config_folders_path = r'VR Config Shortcuts'

# config_folders = {
#     'no_hmd': os.path.join(config_folders_path, 'no_hmd'),
#     'normal': os.path.join(config_folders_path, 'normal'),
#     'normal_nopower': os.path.join(config_folders_path, 'normal_nopower'),
# }

# config_folder = config_folders[option]

steamvr_settings_out = r'C:\Program Files (x86)\Steam\config\steamvr.vrsettings'
null_driver_out = r'C:\Program Files (x86)\Steam\steamapps\common\SteamVR\drivers\null\resources\settings\default.vrsettings'

#Run normal_nopower to keep base stations on then switch to no_hmd...not working
# 
option = 'normal'
# option = 'seated'
# option = 'normal_nopower' #Can't gt to work. Seems have to switch power settins in steamvr and nohmd cannot wake base stations.
# option = 'no_hmd'

config_folder = os.path.join(config_folders_path, option)

shutil.copy(os.path.join(config_folder, 'steamvr.vrsettings'), steamvr_settings_out)
shutil.copy(os.path.join(config_folder, 'default.vrsettings'), null_driver_out)




    
