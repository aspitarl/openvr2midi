from PyQt5.QtWidgets import *
from PyQt5.QtGui import QIntValidator, QGuiApplication
from PyQt5 import QtCore
from PyQt5 import QtWidgets
import sys

import mido
import json
from pythonosc import udp_client

from triad_openvr import triad_openvr
from gui_threads import DataThread
from gui_layouts import SignalSelectLayout, OSCLayout

class MainWidget(QtWidgets.QWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.midiout = None

        layout = QVBoxLayout()

        #Thread for obtaining and sending out data
        self.datathread = DataThread()

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
        available_ports = [p for p in available_ports if 'Right' in p] #TODO: temporary
        self.combobox_midichans.addItems(available_ports)
        layout.addWidget(self.combobox_midichans)

        # Connect midi and OpenVR
        self.pushbutton_connect = QPushButton('Connect')
        self.pushbutton_connect.clicked.connect(self.connect_object)
        layout.addWidget(self.pushbutton_connect)

        # Signal selection and data thread 

        self.select_layout = SignalSelectLayout()
        layout.addLayout(self.select_layout)

        self.OSC_layout = OSCLayout()
        layout.addLayout(self.OSC_layout)
        self.OSC_layout.enable_OSC.setChecked(False)
        self.OSC_layout.enable_OSC.stateChanged.connect(self.enable_disable_OSC)

        #TODO: don't pass cc_dict reference? Could we replace this with a data model? See select_layout. https://stackoverflow.com/questions/21857935/pyqt-segmentation-fault-sometimes
        # also, datathread splits data into two dictionaries....
        self.datathread.cc_dict = self.select_layout.cc_dict
        self.datathread.cube_ranges_update_signal.connect(self.update_cube_ranges)

        #TODO: these also are janky data communications between mainwidget and thread, like signal select layout. 
        self.checkbox_ymode = QCheckBox('Enable Half Y mode')
        self.checkbox_ymode.setChecked(self.datathread.enable_half_y)
        self.checkbox_ymode.stateChanged.connect(self.enable_disable_ymode)
        layout.addWidget(self.checkbox_ymode)

        self.checkbox_debug = QCheckBox('Enable Debugging')
        self.checkbox_debug.setChecked(False)
        self.checkbox_debug.stateChanged.connect(self.enable_debug)
        layout.addWidget(self.checkbox_debug)

        # Debug Console
        self.debug_console = QTextEdit()
        self.debug_console.setReadOnly(True)
        self.debug_console.setPlainText('')
        layout.addWidget(self.debug_console)

        self.datathread.debug_signal.connect(self.debug_console.setText)

        self.setLayout(layout)

        self.load_cube_ranges()

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

    def disconnect_objects(self):
        #TODO: need to duplicate these?
        self.contr = None
        if self.midiout:
            self.midiout.close()

        self.datathread.midiout = None
        self.datathread.contr = self.contr
        self.datathread.stop()

    def load_cube_ranges(self):
        with open('ranges_dict_right.json', 'r') as f:
            self.cube_ranges = json.load(f)
        
        self.select_layout.update_range_widgets(self.cube_ranges)
        self.datathread.cube_ranges = self.cube_ranges
    
    def update_cube_ranges(self, range_dict):
        self.select_layout.update_range_widgets(range_dict)

from PyQt5.QtGui import QCloseEvent

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setWindowTitle('OpenVR to MIDI')

        menuBar = QMenuBar(self)
        self.setMenuBar(menuBar)

        self.main_widget = MainWidget()
        self.setCentralWidget(self.main_widget)

    def closeEvent(self, a0: QCloseEvent) -> None:
        print('Recieved Close event, Disconnecting Objects')
        self.main_widget.disconnect_objects()
        return super().closeEvent(a0)


def main():
    app = QtWidgets.QApplication(sys.argv)
    mainwindow = MainWindow()
    mainwindow.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()