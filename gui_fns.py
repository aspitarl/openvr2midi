from time import sleep
#TODO: Improve imports and make consistent
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QApplication, QComboBox, QFileSystemModel, QHBoxLayout, QRadioButton, QTreeView, QWidget, QVBoxLayout, QSplitter, QMenuBar, QMenu, QAction, QFileDialog, QTableWidget, QTableWidgetItem, QLabel, QLineEdit, QFrame, QSizePolicy
from PyQt5 import QtCore
from PyQt5.QtGui import QDoubleValidator

from controller_midi import get_inputs_and_pose, scale_data, MIDI_CC_MAX


# MIDI_CC_MAX = 127

import mido

class DataThread(QtCore.QThread):
    # https://stackoverflow.com/questions/9957195/updating-gui-elements-in-multithreaded-pyqt

    data_obtained = QtCore.pyqtSignal(object, object)

    def __init__(self):
        QtCore.QThread.__init__(self)
        self.data = []
        self._isRunning = False

        self.contr = None
        self.cc_dict = None
        self.cube_ranges = None
        self.midiout = None

        # self.data_obtained.connect(self.send_data)

    def run(self):
        """Long-running task."""

        if self.contr:
            self._isRunning = True
            while self._isRunning:
                
                inputs, pose = get_inputs_and_pose(self.contr)
                if pose is not None:   
                    if inputs['trackpad_touched']:                    
                        # self.data_obtained.emit(inputs, pose)

                        
                        trigger = inputs['trigger']

                        for dim in self.cc_dict:
                            if self.cc_dict[dim]:

                                if dim == 'trigger':
                                    data_scaled = int(trigger)*MIDI_CC_MAX
                                else:
                                    half_mode = True if (dim == 'y') and (trigger == 1) else False
                                    data_scaled = scale_data(pose, self.cube_ranges, dim, half=half_mode)

                                cc = mido.Message('control_change',control=self.cc_dict[dim], value=data_scaled)
                                self.midiout.send(cc)            

                # sleep(.1)

    def stop(self):
        self._isRunning = False

    # def send_data(self, inputs, pose):
    #     # print(inputs)
    #     pass