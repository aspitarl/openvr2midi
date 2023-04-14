from PyQt5.QtWidgets import *
from PyQt5.QtGui import QIntValidator, QGuiApplication
from PyQt5 import QtCore
from PyQt5 import QtWidgets
import sys

import mido
import json

from triad_openvr import triad_openvr
from gui_fns import DataThread

class MainWidget(QtWidgets.QWidget):
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

        #TODO: don't pass cc_dict reference? Could we replace this with a data model? See select_layout. https://stackoverflow.com/questions/21857935/pyqt-segmentation-fault-sometimes
        # also, datathread splits data into two dictionaries....
        self.datathread = DataThread()
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

from controller_midi import cc_dict as default_cc_dict

class SignalSelectLayout(QtWidgets.QVBoxLayout):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        #TODO: This cc dict is acting like a model. Move to a Table model? or custom model with a custom view of widgets? 
        # here we are having to add a signal to each widget to update cc_dict, such that the data thread can read the state of the widgets.
        # https://stackoverflow.com/questions/17748546/pyqt-column-of-checkboxes-in-a-qtableview
        # https://stackoverflow.com/questions/44603119/how-to-display-a-pandas-data-frame-with-pyqt5-pyside2

        self.cc_layout_widget_dict = {}
        self.cc_dict = {}

        vlayout = QVBoxLayout()

        self.pushbutton_change_all = QPushButton('enable/disable all')
        self.pushbutton_change_all.clicked.connect(self.enable_disable_all)

        self.all_enabled = True

        vlayout.addWidget(self.pushbutton_change_all)

        for sig in default_cc_dict:
            self.cc_layout_widget_dict[sig] = {}

            hlayout = QHBoxLayout()

            hlayout.addWidget(QLabel(sig))
            
            cc_spinbox = QSpinBox()
            cc_spinbox.setValue(default_cc_dict[sig])
            cc_spinbox.valueChanged.connect(self.update_cc_dict)
            self.cc_layout_widget_dict[sig]['cc_spinbox'] = cc_spinbox
            hlayout.addWidget(cc_spinbox)

            send_checkbox = QCheckBox()
            send_checkbox.setChecked(self.all_enabled)
            send_checkbox.stateChanged.connect(self.update_cc_dict)
            self.cc_layout_widget_dict[sig]['send_checkbox'] = send_checkbox
            hlayout.addWidget(send_checkbox)

            if sig not in ['trigger']:
                min_range = QLineEdit()
                min_range.setFixedWidth(50)
                min_range.setReadOnly(True)
                self.cc_layout_widget_dict[sig]['min_range_line_edit'] = min_range
                hlayout.addWidget(min_range)

                max_range = QLineEdit()
                max_range.setFixedWidth(50)
                max_range.setReadOnly(True)
                self.cc_layout_widget_dict[sig]['max_range_line_edit'] = max_range
                hlayout.addWidget(max_range)

            vlayout.addLayout(hlayout)

        self.update_cc_dict()
        self.addLayout(vlayout)

    def enable_disable_all(self):
        if self.all_enabled:
            self.all_enabled = False
        else:
            self.all_enabled = True

        for sig in self.cc_layout_widget_dict:
            self.cc_layout_widget_dict[sig]['send_checkbox'].blockSignals(True)
            self.cc_layout_widget_dict[sig]['send_checkbox'].setChecked(self.all_enabled)
            self.cc_layout_widget_dict[sig]['send_checkbox'].blockSignals(False)
        
        self.update_cc_dict()

    def update_cc_dict(self):

        for sig in self.cc_layout_widget_dict:
            widgets = self.cc_layout_widget_dict[sig]
            if widgets['send_checkbox'].isChecked():
                self.cc_dict[sig] = widgets['cc_spinbox'].value()
            else:
                self.cc_dict[sig] = None
                
    def update_range_widgets(self, range_dict): 
        for sig in range_dict:
            self.cc_layout_widget_dict[sig]['min_range_line_edit'].setText(
                "{:.3f}".format(range_dict[sig]['min'])
            )

            self.cc_layout_widget_dict[sig]['max_range_line_edit'].setText(
                "{:.3f}".format(range_dict[sig]['max'])
            )
        # self.setLayout(layout)

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