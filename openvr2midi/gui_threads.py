import os
import time
from PyQt5 import QtWidgets
from PyQt5 import QtCore

from utils import get_inputs_and_pose_dict, scale_data
from utils import MIDI_CC_MAX, SEND_DATA_BUTTON, RANGE_SET_BUTTON, WAIT_INTERVAL

import mido

import debugpy

class DataThread(QtCore.QThread):
    # https://stackoverflow.com/questions/9957195/updating-gui-elements-in-multithreaded-pyqt

    data_obtained = QtCore.pyqtSignal(object, object)
    debug_signal = QtCore.pyqtSignal(str)

    def __init__(self, table_model, *args, **kwargs):
        QtCore.QThread.__init__(self)
        self._table_model = table_model
        self.update_dicts()
        self._table_model.dataChanged.connect(self.update_dicts)

        self._isRunning = False

        #TODO: these are overwritten with references after initializing instance in the 'containing' class. This is just here to throw errors if that doesn't work. can they be accessed without doing this? 
        self.contr = None
        self.midiout = None

        self.debug_console = None
        self.debug = False

        self.save_range_dict = False

        self.enable_half_y = True
        self.OSC_client = None
        self.enable_haptic = True
        self.always_send = False
        self.manual_range_set = False

        self.yaw_y_factor = 1.0
        self.yaw_x_factor = 1.0

        self.input_dict = None
        self.pose_dict = None

    def update_dicts(self):
        df_table = self._table_model._data
        df_table = df_table[df_table['send'].astype(bool) == True]
        self.cc_dict = dict(zip(df_table['dim'], df_table['CC']))

        self.cube_ranges = {   
            row['dim']: {'min': df_table['min_range'][idx], 'max': df_table['max_range'][idx]} for idx, row in df_table.iterrows()
        }


    def update_table_model_cube_ranges(self):
        df_table = self._table_model._data
        for i, dim in enumerate(self.cube_ranges):
            df_table.loc[i, 'min_range'] = self.cube_ranges[dim]['min']
            df_table.loc[i, 'max_range'] = self.cube_ranges[dim]['max']

        self._table_model.set_new_data(df_table)

    def run(self):
        """Long-running task."""

        # debugpy.debug_this_thread()

        if self.contr:
            haptic_loop_counter = 0
            self._isRunning = True
            while self._isRunning:
                if self.enable_haptic: haptic_loop_counter += 1
                start = time.time()
                
                self.input_dict, self.pose_dict = get_inputs_and_pose_dict(self.contr, self.yaw_x_factor, self.yaw_y_factor)

                if self.debug:
                    debug_str = str(self.input_dict) + '\n\n' + str(self.pose_dict) + '\n\n' + str(self.cube_ranges)
                    self.debug_signal.emit(debug_str)
                    #TODO: how to remove this sleep here, can't figure out how to regulate handling of this signal in parent
                    time.sleep(1)

                #TODO: Move this into it's own class function here?
                if (self.input_dict['button'] == RANGE_SET_BUTTON or self.manual_range_set) and self.pose_dict != None:
                    #enter range set mode
                    self.range_set_mode(self.contr)
                    self.update_table_model_cube_ranges()

                if self.pose_dict is not None:   
                    if self.input_dict['trackpad_touched'] or self.always_send:                    
                        trigger = self.input_dict['trigger']

                        for dim in self.cc_dict:
                            if self.cc_dict[dim]:
                                if dim == 'trigger':
                                    data_scaled = int(trigger)*MIDI_CC_MAX
                                else:
                                    if self.enable_half_y:
                                        half_mode = True if (dim == 'y') and (trigger == 1) else False
                                    else:
                                        half_mode = False
                                        
                                    data_scaled = scale_data(self.pose_dict, self.cube_ranges, dim, half=half_mode)

                                cc = mido.Message('control_change',control=self.cc_dict[dim], value=data_scaled)
                                self.midiout.send(cc)            


                                if self.OSC_client != None:
                                    self.OSC_client.send_message("/{}/{}".format('VR', dim), data_scaled/127)

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

        inputs, pose_dict = get_inputs_and_pose_dict(contr, self.yaw_x_factor, self.yaw_y_factor)

        self.cube_ranges = {
            'x': {'min': pose_dict['x'], 'max': pose_dict['x']},
            'y': {'min': pose_dict['y'], 'max': pose_dict['y']},
            'z': {'min': pose_dict['z'], 'max': pose_dict['z']},
            'yaw': {'min': pose_dict['yaw'], 'max': pose_dict['yaw']},
            'pitch': {'min': pose_dict['pitch'], 'max': pose_dict['pitch']},
            'roll': {'min': pose_dict['roll'], 'max': pose_dict['roll']}
        }      

        while(inputs['button'] == RANGE_SET_BUTTON or self.manual_range_set):

            inputs, pose_dict = get_inputs_and_pose_dict(contr, self.yaw_x_factor, self.yaw_y_factor)

            if pose_dict is not None:
                for dim in pose_dict:
                    if pose_dict[dim] < self.cube_ranges[dim]['min']:
                        self.cube_ranges[dim]['min'] = pose_dict[dim]
                    elif pose_dict[dim] > self.cube_ranges[dim]['max']:
                        self.cube_ranges[dim]['max'] = pose_dict[dim]

            sleep_time = WAIT_INTERVAL-(time.time()-start)
            if sleep_time>0:
                time.sleep(sleep_time)


        self.debug_signal.emit("exited range set mode with ranges: \n" + str(self.cube_ranges))
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

    def update_text(self, input, pose_dict):
        text = str(input) + '\n\n ' + str(pose_dict)
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
        