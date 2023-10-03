from PyQt5.QtWidgets import *
from PyQt5 import QtWidgets

default_enabled_dict = {
    'x': True,
    'y': True,
    'z': True,
    'yaw': True,
    'pitch': False,
    'roll': False,
    'trigger':True,
    # 'tpy':26,
}

class OSCLayout(QtWidgets.QVBoxLayout):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.enable_OSC = QCheckBox("Enable OSC")

        self.addWidget(self.enable_OSC)

        self.ip = '192.168.10.255'
        self.port = 10000


class SignalSelectLayout(QtWidgets.QVBoxLayout):
    def __init__(self, default_cc_dict, *args, **kwargs):
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

        # Radio buttons
        self.solo_group = QButtonGroup()
        self.solo_group.setExclusive(False) # You cannot apparently have exclusive and allow for deselection

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
            send_checkbox.setChecked(default_enabled_dict[sig])
            send_checkbox.stateChanged.connect(self.update_cc_dict)
            self.cc_layout_widget_dict[sig]['send_checkbox'] = send_checkbox
            hlayout.addWidget(send_checkbox)

            solo_radio = QCheckBox()
            solo_radio.sig_name = sig
            solo_radio.setChecked(False)
            solo_radio.stateChanged.connect(self.update_solo)
            self.solo_group.addButton(solo_radio)
            hlayout.addWidget(solo_radio)


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
    
    def set_cc_vals(self, cc_dict):
        for sig in cc_dict:
            self.cc_layout_widget_dict[sig]['cc_spinbox'].setValue(cc_dict[sig])

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

    def update_solo(self):

        #TODO: make enable dict use this method
        #https://stackoverflow.com/questions/35819538/using-lambda-expression-to-connect-slots-in-pyqt
        soloed_checkbox = self.sender()

        is_checked = soloed_checkbox.isChecked()
        sig_name = soloed_checkbox.sig_name

        for solo_checkbox in self.solo_group.buttons():
            if solo_checkbox != soloed_checkbox:
                solo_checkbox.blockSignals(True)
                solo_checkbox.setChecked(False)
                solo_checkbox.blockSignals(False)

        if is_checked:
            for sig in self.cc_layout_widget_dict:
                widgets = self.cc_layout_widget_dict[sig]
                if sig == sig_name:
                    self.cc_dict[sig] = widgets['cc_spinbox'].value()
                else:
                    self.cc_dict[sig] = None
        else:
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
