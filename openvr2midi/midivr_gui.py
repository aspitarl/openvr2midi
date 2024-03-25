from PyQt5.QtWidgets import *
from PyQt5.QtGui import QIntValidator, QGuiApplication
from PyQt5 import QtCore
from PyQt5.QtCore import pyqtSignal
from PyQt5 import QtWidgets
from PyQt5.QtGui import QValidator
import sys
import os
import pandas as pd
import json

import mido
import json
from pythonosc import udp_client

from triad_openvr import triad_openvr
from gui_threads import DataThread
from gui_layouts import  OSCLayout

from pandasgrid import PandasGridWidget

default_cc_dict_controllers = {
    'Right Controller' : {
    'x': 22,
    'y': 23,
    'z': 24,
    'yaw': 25,
    'pitch': 26,
    'roll': 27,
    'trigger':28,
},
    'Left Controller': {
    'x': 32,
    'y': 33,
    'z': 34,
    'yaw': 35,
    'pitch': 36,
    'roll': 37,
    'trigger':38,
    }
}


class AlphaNumericValidator(QValidator):
    def validate(self, input_str, pos):
        if input_str.isalnum():
            return QValidator.Acceptable, input_str, pos
        else:
            return QValidator.Invalid, input_str, pos

settings_dir = 'settings/'

class MainWidget(QtWidgets.QWidget):

    midi_channel_changed_signal = pyqtSignal(name='midi_channel_changed')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.midiout = None

        layout = QVBoxLayout()



        #OpenVR layout
        openvr_hlayout = QHBoxLayout()
        self.pushbutton_discover = QPushButton('Discover OpenVR Objects')
        self.pushbutton_discover.clicked.connect(self.discover_objects)

        self.combobox_objects = QComboBox()
        openvr_hlayout.addWidget(self.pushbutton_discover)
        openvr_hlayout.addWidget(self.combobox_objects)

        layout.addLayout(openvr_hlayout)

        # MIDI
        self.combobox_midichans = QComboBox()
        available_ports = mido.get_output_names()
        available_ports = [p for p in available_ports if 'Controller' in p] #TODO: temporary
        self.combobox_midichans.addItems(available_ports)
        layout.addWidget(self.combobox_midichans)

        connect_hlayout = QHBoxLayout()

        # Connect midi and OpenVR
        self.pushbutton_connect = QPushButton('Connect')
        self.pushbutton_connect.clicked.connect(self.connect_object)
        connect_hlayout.addWidget(self.pushbutton_connect)

        # Disconnect midi and OpenVR
        self.pushbutton_connect = QPushButton('Disconnect')
        self.pushbutton_connect.clicked.connect(self.disconnect_objects)
        connect_hlayout.addWidget(self.pushbutton_connect)

        self.checkbox_isconnected = QCheckBox('Connected?')
        self.checkbox_isconnected.setEnabled(False)
        # self.checkbox_isconnected.set
        connect_hlayout.addWidget(self.checkbox_isconnected)

        layout.addLayout(connect_hlayout)

        self.combobox_midichans.currentIndexChanged.connect(self.midi_channel_changed) #TODO: Hacky way of talking to signal select layout

        # settings saving
        # TODO: save settings for each controller and load them when selected, was previously done with midi_channel_changed

        self.settings_layout = QHBoxLayout()

        self._load_button = QPushButton("Load")
        self._load_button.clicked.connect(self.load_data)
        self._save_button = QPushButton("Save")
        self._save_button.clicked.connect(self.save_data)

        self._fileselect_combo = QComboBox()
        # Add all files in the settings directory to the combo box
        self._fileselect_combo.addItems([f.split('.')[0] for f in os.listdir('settings') if f.endswith('.csv')])
        self._fileselect_combo.currentIndexChanged.connect(self.update_line_edit)

        self._new_filename_line_edit = QLineEdit()
        self._new_filename_line_edit.setValidator(AlphaNumericValidator(self._new_filename_line_edit))
        self.update_line_edit(0)
        # # Signal selection and data thread 

        self.settings_layout.addWidget(self._fileselect_combo)
        self.settings_layout.addWidget(self._load_button)
        self.settings_layout.addWidget(self._save_button)
        self.settings_layout.addWidget(self._new_filename_line_edit)

        layout.addLayout(self.settings_layout)

        # use first file in settings directory as default 
        df_initial = pd.read_csv('settings/' + self._fileselect_combo.currentText() + ".csv")
        self.CC_grid_widget = PandasGridWidget(df_initial)

        layout.addWidget(self.CC_grid_widget)

        #Thread for obtaining and sending out data
        self.datathread = DataThread(table_model=self.CC_grid_widget._table_model)

        self.OSC_layout = OSCLayout()
        layout.addLayout(self.OSC_layout)
        self.OSC_layout.enable_OSC.setChecked(False)
        self.OSC_layout.enable_OSC.stateChanged.connect(self.enable_disable_OSC)

        # Extra settings

        #TODO: these also are janky data communications between mainwidget and thread, like signal select layout. 
        self.checkbox_ymode = QCheckBox('Enable Half Y mode')
        self.checkbox_ymode.setChecked(self.datathread.enable_half_y)
        self.checkbox_ymode.stateChanged.connect(self.enable_disable_ymode)

        self.checkbox_debug = QCheckBox('Enable Debugging')
        self.checkbox_debug.setChecked(False)
        self.checkbox_debug.stateChanged.connect(self.enable_debug)

        # make a two checkboxes that set the yaw x and y factors to 1 or -1 depending on the state of the checkbox, setting the yaw_x_factor and yaw_y_factor variables in the data thread

        self.checkbox_yaw_x_factor = QCheckBox('Invert Yaw X')
        self.checkbox_yaw_x_factor.setChecked(False)
        self.checkbox_yaw_x_factor.stateChanged.connect(lambda: setattr(self.datathread, 'yaw_x_factor', -1 if self.checkbox_yaw_x_factor.isChecked() else 1))

        self.checkbox_yaw_y_factor = QCheckBox('Invert Yaw Y')
        self.checkbox_yaw_y_factor.setChecked(False)
        self.checkbox_yaw_y_factor.stateChanged.connect(lambda: setattr(self.datathread, 'yaw_y_factor', -1 if self.checkbox_yaw_y_factor.isChecked() else 1))

        # make a grid layout for all extra settings checkboxes and add it to the main layout

        extra_settings_layout = QGridLayout()
        extra_settings_layout.addWidget(self.checkbox_ymode, 0, 0)
        extra_settings_layout.addWidget(self.checkbox_debug, 0, 1)
        extra_settings_layout.addWidget(self.checkbox_yaw_x_factor, 1, 0)
        extra_settings_layout.addWidget(self.checkbox_yaw_y_factor, 1, 1)

        layout.addLayout(extra_settings_layout)

        # Debug Console
        self.debug_console = QTextEdit()
        self.debug_console.setReadOnly(True)
        self.debug_console.setPlainText('')
        layout.addWidget(self.debug_console)

        self.datathread.debug_signal.connect(self.debug_console.setText)

        self.setLayout(layout)

    def get_selected_controller_name(self):
        # The midi port seems to have random numbers at the end, so just extract the name to use in dicts etc.
        current_midi_chan = self.combobox_midichans.currentText()
        contr_name = 'Right Controller' if 'Right Controller' in current_midi_chan else 'Left Controller'

        return contr_name

    def midi_channel_changed(self):
        self.midi_channel_changed_signal.emit() # To tell the main window to update the title

    #TODO: These functions probably can be replaced by lambda, but also would be fixed by using a data model
    def enable_disable_OSC(self):
        if self.OSC_layout.enable_OSC.isChecked():
            self.debug_console.setText("Sending osc messages to IP: {} over port {}".format(self.OSC_layout.ip, self.OSC_layout.port))
            self.datathread.OSC_client = udp_client.SimpleUDPClient(self.OSC_layout.ip, self.OSC_layout.port)
        else:
            self.debug_console.setText("Disabling OSC")
            self.datathread.OSC_client = None

    def enable_disable_ymode(self):
        if self.checkbox_ymode.isChecked():
            self.datathread.enable_half_y = True
        else:
            self.datathread.enable_half_y = False

    def enable_debug(self):
        if self.checkbox_debug.isChecked():
            self.datathread.debug = True
        else:
            self.datathread.debug = False

    def discover_objects(self):

        self.v = triad_openvr.triad_openvr()

        #Indicate what controller belongs to which hand...Must be a more elegant way...
        present_controllers = [key for key in self.v.devices if 'controller' in key]
        try:
            self.models = {controller: self.v.devices[controller].get_model() for controller in present_controllers}
        except OSError as e:
            raise e
        else:
            self.combobox_objects.clear()
            display_text = ["{}: {}".format(c, str(self.models[c])) for c in self.models.keys()]
            self.combobox_objects.addItems(display_text)

    def connect_object(self):
        controller_idx = self.combobox_objects.currentIndex()
        model_keys = list(self.models.keys())
        controller_name = model_keys[controller_idx]
        self.debug_console.setText("connecting to " + str(controller_name))
        self.contr = self.v.devices[controller_name]

        midi_port = self.combobox_midichans.currentText()
        self.debug_console.append('Connecting to midi port: ' + midi_port)
        self.midiout = mido.open_output(midi_port)

        self.datathread.contr = self.contr
        self.datathread.midiout = self.midiout
        self.datathread.start()

        self.checkbox_isconnected.setChecked(True)

    def close_midi(self):
        if self.midiout:
            self.midiout.close()

    def disconnect_objects(self):
        #TODO: need to duplicate these?
        self.contr = None
        self.close_midi()

        self.datathread.midiout = None
        self.datathread.contr = self.contr
        self.datathread.stop()

        self.checkbox_isconnected.setChecked(False)

    def save_data(self):
        file_path = 'settings/' + self._new_filename_line_edit.text() + ".json"
        if file_path:
            self._data = self.CC_grid_widget._table_model._data

            # Make sure the solor and send data columns are bools
            self._data['solo'] = self._data['solo'].astype(bool)
            self._data['send'] = self._data['send'].astype(bool)

            # Convert the DataFrame to a JSON string
            df_json = self._data.to_json(orient='split')

            # Create a settings dictionary
            settings = {
                'dataframe': df_json,
                'half_y_mode': self.checkbox_ymode.isChecked(),
                'yaw_x_factor': self.checkbox_yaw_x_factor.isChecked(),
                'yaw_y_factor': self.checkbox_yaw_y_factor.isChecked(),
            }

            # Write the settings dictionary to the JSON file
            with open(file_path, 'w') as f:
                json.dump(settings, f)

    def load_data(self):
        file_path = 'settings/' + self._fileselect_combo.currentText() + ".json"
        if os.path.exists(file_path):
            # Read the settings dictionary from the JSON file
            with open(file_path, 'r') as f:
                settings = json.load(f)

            # Get the DataFrame JSON string from the settings dictionary
            df_json = settings['dataframe']

            # Convert the DataFrame JSON string to a DataFrame
            self._data = pd.read_json(df_json, orient='split')

            # Load the DataFrame into the grid widget
            self.CC_grid_widget.set_data(self._data)

            # # Load the other settings
            self.checkbox_ymode.setChecked(settings['half_y_mode'])
            self.checkbox_yaw_x_factor.setChecked(settings['yaw_x_factor'])
            self.checkbox_yaw_y_factor.setChecked(settings['yaw_y_factor'])

    def update_line_edit(self, index):
        # Get the current text in the combo box
        current_text = self._fileselect_combo.itemText(index)
        # Set the text in the line edit
        self._new_filename_line_edit.setText(current_text)


from PyQt5.QtGui import QCloseEvent

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setWindowTitle('OpenVR to MIDI')

        menuBar = QMenuBar(self)
        self.setMenuBar(menuBar)

        self.main_widget = MainWidget()
        self.setCentralWidget(self.main_widget)
        self.main_widget.midi_channel_changed_signal.connect(self.update_title)
        self.update_title()

    def closeEvent(self, a0: QCloseEvent) -> None:
        print('Recieved Close event, Disconnecting Objects')
        self.main_widget.disconnect_objects()
        return super().closeEvent(a0)
    
    def update_title(self):
        contr_name = self.main_widget.get_selected_controller_name()
        self.setWindowTitle(contr_name)



def main():
    app = QtWidgets.QApplication(sys.argv)
    main_window = MainWindow()
    main_window.main_widget.main_window = main_window # Weird way to allow main widget to change window title...
    main_window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()