import os
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
    debug_signal = QtCore.pyqtSignal(str)

    def __init__(self):
        QtCore.QThread.__init__(self)
        self.data = []
        self._isRunning = False

        #TODO: these are overwritten with references after initializing instance in the 'containing' class. This is just here to throw errors if that doesn't work. can they be accessed without doing this? 
        self.contr = None
        self.cc_dict = None
        self.cube_ranges = None
        self.midiout = None

        self.debug_console = None
        self.debug = False

        # self.data_obtained.connect(self.send_data)

    def run(self):
        """Long-running task."""

        if self.contr:
            self._isRunning = True
            while self._isRunning:
                
                inputs, pose = get_inputs_and_pose(self.contr)

                if self.debug:
                    # self.data_obtained.emit(inputs, pose)
                    debug_str = str(inputs) + '\n\n' + str(pose)
                    self.debug_signal.emit(debug_str)
                    #TODO: how to remove this sleep here, can't figure out how to regulate handling of this signal in parent
                    sleep(1)
                    # os.system('cls')
                    # print(inputs)
                    # print(pose)

                if pose is not None:   
                    if inputs['trackpad_touched']:                    

                        
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

class TextUpdateThread(QtCore.QThread):
    def __init__(self, text_edit_object: QtWidgets.QTextEdit):
        QtCore.QThread.__init__(self)

        self._isRunning = False
        self.text_edit_object = text_edit_object
        self.display_text = ''

    def run(self):
        self._isRunning = True
        while self._isRunning:
            self.text_edit_object.setText(self.display_text)
            sleep(1) # this would be replaced by real code, producing the new text...

    def stop(self):
        self._isRunning = False

    def update_text(self, input, pose):
        text = str(input) + '\n\n ' + str(pose)
        self.display_text = text