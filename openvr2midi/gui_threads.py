import os
import time
from PyQt5 import QtWidgets
from PyQt5 import QtCore

from utils import get_inputs_and_pose, scale_data
from utils import MIDI_CC_MAX, SEND_DATA_BUTTON, RANGE_SET_BUTTON, WAIT_INTERVAL

import mido



class DataThread(QtCore.QThread):
    # https://stackoverflow.com/questions/9957195/updating-gui-elements-in-multithreaded-pyqt

    data_obtained = QtCore.pyqtSignal(object, object)
    debug_signal = QtCore.pyqtSignal(str)

    cube_ranges_update_signal = QtCore.pyqtSignal(dict)

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

        self.save_range_dict = False

        self.enable_half_y = True
        self.OSC_client = None
        self.enable_haptic = True

    def run(self):
        """Long-running task."""

        if self.contr:
            haptic_loop_counter = 0
            self._isRunning = True
            while self._isRunning:
                if self.enable_haptic: haptic_loop_counter += 1
                start = time.time()
                
                inputs, pose = get_inputs_and_pose(self.contr)

                if self.debug:
                    debug_str = str(inputs) + '\n\n' + str(pose) + '\n\n' + str(self.cube_ranges)
                    self.debug_signal.emit(debug_str)
                    #TODO: how to remove this sleep here, can't figure out how to regulate handling of this signal in parent
                    time.sleep(1)

                #TODO: Move this into it's own class function here?
                if inputs['button'] == RANGE_SET_BUTTON and pose != None:
                    #enter range set mode
                    self.range_set_mode(self.contr)
                    self.cube_ranges_update_signal.emit(self.cube_ranges)

                if pose is not None:   
                    if inputs['trackpad_touched']:                    
                        trigger = inputs['trigger']

                        for dim in self.cc_dict:
                            if self.cc_dict[dim]:
                                if dim == 'trigger':
                                    data_scaled = int(trigger)*MIDI_CC_MAX
                                else:
                                    if self.enable_half_y:
                                        half_mode = True if (dim == 'y') and (trigger == 1) else False
                                    else:
                                        half_mode = False
                                        
                                    data_scaled = scale_data(pose, self.cube_ranges, dim, half=half_mode)

                                cc = mido.Message('control_change',control=self.cc_dict[dim], value=data_scaled)
                                self.midiout.send(cc)            


                                if self.OSC_client != None:
                                    self.OSC_client.send_message("/{}/{}".format('right', dim), data_scaled/127)

                                if dim == 'y':
                                    haptic_threshold = 40
                                    if self.enable_haptic:
                                        if haptic_loop_counter > 10:
                                            if (data_scaled > haptic_threshold):
                                                scaled_y_vib = int(data_scaled-haptic_threshold)*30
                                                self.contr.trigger_haptic_pulse(duration_micros=scaled_y_vib)
                                                haptic_loop_counter = 0
                
                sleep_time = WAIT_INTERVAL-(time.time()-start)
                if sleep_time>0:
                    time.sleep(sleep_time)

    def stop(self):
        self._isRunning = False

    def range_set_mode(self, contr):

        self.debug_signal.emit("entering range set mode")
        start = time.time()

        inputs, pose = get_inputs_and_pose(contr)

        self.cube_ranges = {
            'x': {'min': pose['x'], 'max': pose['x']},
            'y': {'min': pose['y'], 'max': pose['y']},
            'z': {'min': pose['z'], 'max': pose['z']},
            'yaw': {'min': pose['yaw'], 'max': pose['yaw']},
            'pitch': {'min': pose['pitch'], 'max': pose['pitch']},
            'roll': {'min': pose['roll'], 'max': pose['roll']}
        }      

        while(inputs['button'] == RANGE_SET_BUTTON):

            inputs, pose = get_inputs_and_pose(contr)

            if pose is not None:
                for dim in pose:
                    if pose[dim] < self.cube_ranges[dim]['min']:
                        self.cube_ranges[dim]['min'] = pose[dim]
                    elif pose[dim] > self.cube_ranges[dim]['max']:
                        self.cube_ranges[dim]['max'] = pose[dim]

            sleep_time = WAIT_INTERVAL-(time.time()-start)
            if sleep_time>0:
                time.sleep(sleep_time)

class TextUpdateThread(QtCore.QThread):
    """
    Unsuccessful attempt to enable debugging with a parallel thread that would update the debug texteditwidget
    """

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



## Pitchbend archive

# ## Not sure exactly how pitchbend works in mido, use 'pitch wheel'?

#     if inputs['trackpad_touched']:
#         tpy = int(inputs['trackpad_y']*64+64)

#         # cctpy = [CONTROL_CHANGE, cc_dict['tpy'], tpy]
#         # midiout.send_message(cctpy)  


#         pb = tpy
#         # pb = [PITCH_BEND, 0 , pb]
#         pb = mido.Message('pitchwheel', value=pb)
#         midiout.send(pb)

#         # if debug: debugstr = debugstr + '\npb Message: ' + str(pb)
#         trackpad_reset = True
# else:
#     if trackpad_reset:
#         # cctpy = [CONTROL_CHANGE, cc_dict['tpy'], 64]
#         cctpy= mido.Message('control_change',control=cc_dict['tpy'], value=64)
#         midiout.send(cctpy)
#         trackpad_reset = False
        