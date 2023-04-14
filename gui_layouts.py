from PyQt5.QtWidgets import *
from PyQt5 import QtWidgets
from controller_midi import cc_dict as default_cc_dict

class OSCLayout(QtWidgets.QVBoxLayout):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.enable_OSC = QCheckBox("Enable OSC")

        self.addWidget(self.enable_OSC)

        self.ip = '192.168.0.255'
        self.port = 10000



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
