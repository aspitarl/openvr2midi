from PyQt5.QtWidgets import *
from PyQt5.QtGui import QIntValidator, QGuiApplication
from PyQt5 import QtCore
from PyQt5 import QtWidgets
import sys
import time

import mido

from triad_openvr import triad_openvr


import json

from gui_fns import DataThread


class MainWidget(QtWidgets.QWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        layout = QVBoxLayout()

        self.pushbutton_discover = QPushButton('Discover Objects')
        self.pushbutton_discover.clicked.connect(self.discover_objects)


        layout.addWidget(self.pushbutton_discover)


        self.combobox_objects = QComboBox()

        layout.addWidget(self.combobox_objects)

        self.pushbutton_connect = QPushButton('Connect')
        self.pushbutton_connect.clicked.connect(self.connect_object)

        layout.addWidget(self.pushbutton_connect)

        self.pushbutton_disconnect = QPushButton('Disconnect')
        self.pushbutton_disconnect.clicked.connect(self.disconnect_object)
        layout.addWidget(self.pushbutton_disconnect)


        # MIDI

        self.combobox_midichans = QComboBox()
        available_ports = mido.get_output_names()
        available_ports = [p for p in available_ports if 'Right' in p] #TODO: temporary
        self.combobox_midichans.addItems(available_ports)

        
        layout.addWidget(self.combobox_midichans)


        # Debug Console
        self.debug_console = QTextEdit()
        self.debug_console.setReadOnly(True)
        self.debug_console.setPlainText('')

        self.checkbox_debug = QCheckBox('Enable Debugging')
        self.checkbox_debug.setChecked(False)
        self.checkbox_debug.stateChanged.connect(self.enable_debug)


        layout.addWidget(self.checkbox_debug)
        layout.addWidget(self.debug_console)

        # Signal selection and data thread 

        select_layout = SignalSelectLayout()
        layout.addLayout(select_layout)

        #TODO: don't pass these references? https://stackoverflow.com/questions/21857935/pyqt-segmentation-fault-sometimes
        self.datathread = DataThread()
        self.datathread.cc_dict = select_layout.cc_dict
        self.datathread.cube_ranges = select_layout.cube_ranges

        # self.debug_thread = TextUpdateThread(self.debug_console)
        # self.datathread.data_obtained.connect(self.debug_thread.update_text)

        self.datathread.debug_signal.connect(self.debug_console.setText)

        self.setLayout(layout)

    def enable_debug(self):
        if self.checkbox_debug.isChecked():
            self.datathread.debug = True
            # self.debug_thread.start()
        else:
            self.datathread.debug = False
            # self.debug_thread.stop()

    def discover_objects(self):

        self.v = triad_openvr.triad_openvr()
        # self.v.print_discovered_objects()

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
        print("connecting to " + controller_name)
        self.contr = self.v.devices[controller_name]


        midi_port = self.combobox_midichans.currentText()
        print('Connecting to midi port: ' + midi_port)
        self.midiout = mido.open_output(midi_port)



        self.datathread.contr = self.contr
        self.datathread.midiout = self.midiout
        self.datathread.start()



    def disconnect_object(self):
        #TODO: need to duplicate these?
        self.contr = None
        self.midiout.close()


        self.datathread.midiout = None
        self.datathread.contr = self.contr
        self.datathread.stop()

from controller_midi import cc_dict as default_cc_dict

class SignalSelectLayout(QtWidgets.QVBoxLayout):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # layout = QVBoxLayout()

        with open('ranges_dict_right.json', 'r') as f:
            self.cube_ranges = json.load(f)

        self.cc_layout_widget_dict = {}
        self.cc_dict = {}

        for sig in default_cc_dict:
            self.cc_layout_widget_dict[sig] = {}


            hlayout = QHBoxLayout()
            hlayout.addWidget(QLabel(sig))
            
            cc_spinbox = QSpinBox()
            cc_spinbox.setValue(default_cc_dict[sig])
            cc_spinbox.valueChanged.connect(self.update_cc_dict)
            hlayout.addWidget(cc_spinbox)
            self.cc_layout_widget_dict[sig]['cc_spinbox'] = cc_spinbox
            

            send_checkbox = QCheckBox()
            send_checkbox.setChecked(False)
            send_checkbox.stateChanged.connect(self.update_cc_dict)
            hlayout.addWidget(send_checkbox)
            self.cc_layout_widget_dict[sig]['send_checkbox'] = send_checkbox

            if sig in self.cube_ranges:
                min_range = QLineEdit()
                min_range.setFixedWidth(50)
                min_range.setText("{:.3f}".format(self.cube_ranges[sig]['min']))
                min_range.setAlignment(QtCore.Qt.AlignLeft)
                hlayout.addWidget(min_range)

                max_range = QLineEdit()
                max_range.setFixedWidth(50)
                max_range.setText("{:.3f}".format(self.cube_ranges[sig]['max']))
                max_range.setAlignment(QtCore.Qt.AlignLeft)
                hlayout.addWidget(max_range)


            self.addLayout(hlayout)

            self.update_cc_dict()

    def update_cc_dict(self):

        for sig in self.cc_layout_widget_dict:
            widgets = self.cc_layout_widget_dict[sig]
            if widgets['send_checkbox'].isChecked():
                self.cc_dict[sig] = widgets['cc_spinbox'].value()
            else:
                self.cc_dict[sig] = None
                


        # self.setLayout(layout)

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setWindowTitle('trc File Viewer')

        menuBar = QMenuBar(self)
        self.setMenuBar(menuBar)

        self.main_widget = MainWidget()
        self.setCentralWidget(self.main_widget)

## How to get to work?
# from controller_midi import signal_handler
# import signal
# signal.signal(signal.SIGINT, signal_handler)

def main():



    app = QtWidgets.QApplication(sys.argv)
    mainwindow = MainWindow()
    mainwindow.show()
    sys.exit(app.exec_())



if __name__ == '__main__':
    main()