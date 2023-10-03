import shutil
import sys
import os

config_folders_path = r'VR Config Shortcuts'

steamvr_settings = r'C:\Program Files (x86)\Steam\config\steamvr.vrsettings'
null_driver = r'C:\Program Files (x86)\Steam\steamapps\common\SteamVR\drivers\null\resources\settings\default.vrsettings'

new_name = 'seated'

config_folder = os.path.join(config_folders_path, new_name)

if not os.path.exists(config_folder): os.makedirs(config_folder)

shutil.copy(steamvr_settings, os.path.join(config_folder, 'steamvr.vrsettings'))
shutil.copy(null_driver, os.path.join(config_folder, 'default.vrsettings'))
