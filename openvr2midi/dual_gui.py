import sys
import numpy as np
from PyQt5 import QtWidgets, QtCore
from midivr_gui import MainWidget
import mido

class PollingThread(QtCore.QThread):
    def __init__(self, main_widget1, main_widget2, parent):
        super().__init__()
        self.main_widget1 = main_widget1
        self.main_widget2 = main_widget2
        self.running = False
        self.parent = parent

    def run(self):
        self.running = True
        pose_dict1 = None
        pose_dict2 = None

        while self.running:
            input_dict1 = self.main_widget1.datathread.input_dict
            input_dict2 = self.main_widget2.datathread.input_dict


            if input_dict1 is None or input_dict2 is None:
                # restart the loop
                self.msleep(100)
                continue

            if input_dict1['trackpad_touched'] or input_dict2['trackpad_touched']:
                # one is enabled, calculate the difference

                # Poll pose_dict from each main_widget
                # TODO: hacky way to allow for calculation based on previous pose_dict, by checking if the trackpad is touched for each controller and using the previous value if not
                temp_pose_dict1 = self.main_widget1.datathread.pose_dict
                temp_pose_dict2 = self.main_widget2.datathread.pose_dict

                if input_dict1['trackpad_touched']:
                    pose_dict1 = temp_pose_dict1
                if input_dict2['trackpad_touched']:
                    pose_dict2 = temp_pose_dict2

                #TODO: this wont be None after the first iteration, handle better. 
                if pose_dict1 is None or pose_dict2 is None:
                    # restart the loop
                    self.msleep(100)  # Sleep for 100 milliseconds
                    continue

                # Calculate the difference between the two pose_dicts
                pose_diff = {dim: pose_dict1[dim] - pose_dict2[dim] for dim in pose_dict1 if dim in ['x', 'y', 'z']}

                distance = np.linalg.norm(list(pose_diff.values()))

                # update the distance indicator

                dist_range = self.parent.range_spin_box.value()
                cc_value = self.parent.cc_number.value()
                invert = self.parent.invert_checkbox.isChecked()

                dist_norm = distance / dist_range

                self.parent.distance_label.setText(f"Distance: {dist_norm:.2f}")

                cc_out = int(dist_norm*127)

                # floor at 0 and ceiling at 127
                cc_out = max(0, min(127, cc_out))

                if invert:
                    cc_out = 127 - cc_out

                cc = mido.Message('control_change', control=cc_value, value=cc_out)
                # Just send out widget 2's (right) cc for now...
                self.main_widget2.datathread.midiout.send(cc)            

                #TODO: this is needed to not have the main thread freeze, but it's not the best way to do it
                self.msleep(5)

    def stop(self):
        self.running = False

class DistanceLayout(QtWidgets.QHBoxLayout):
    def __init__(self, parent):
        super(DistanceLayout, self).__init__(parent)

        # Create a checkbox to start and stop the polling thread
        self.checkbox = QtWidgets.QCheckBox("Start Position Difference Polling")
        self.checkbox.stateChanged.connect(self.toggle_thread)
        self.addWidget(self.checkbox)
        
        # Create a label to show the distance
        self.distance_label = QtWidgets.QLabel("Distance: 0.0")
        self.addWidget(self.distance_label)

        # Create a slider to set the range from 0.0 to 5.0 with a display of 0.1
        self.range_label = QtWidgets.QLabel("Range:")
        self.range_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.addWidget(self.range_label)
        
        self.range_spin_box = QtWidgets.QDoubleSpinBox()
        self.range_spin_box.setRange(0.1, 5.0)
        self.range_spin_box.setSingleStep(0.1)
        self.range_spin_box.setValue(1.5)
        self.addWidget(self.range_spin_box)

        self.cc_number_label = QtWidgets.QLabel("CC Number:")
        self.cc_number_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.addWidget(self.cc_number_label)
        
        self.cc_number = QtWidgets.QSpinBox()
        self.cc_number.setRange(0, 127)
        self.cc_number.setValue(30)
        self.addWidget(self.cc_number)

        self.invert_checkbox = QtWidgets.QCheckBox("Invert")
        self.invert_checkbox.setChecked(True)
        self.addWidget(self.invert_checkbox)


        # Create the polling thread
        self.polling_thread = PollingThread(parent.main_widget1, parent.main_widget2, parent=self)

    def toggle_thread(self, state):
        if state == QtCore.Qt.Checked:
            self.polling_thread.start()
        else:
            self.polling_thread.stop()



class SideBySideMainWindow(QtWidgets.QMainWindow):
    def __init__(self, parent=None):
        super(SideBySideMainWindow, self).__init__(parent)
        
        # Create a central widget and set a vertical layout
        central_widget = QtWidgets.QWidget(self)
        self.setCentralWidget(central_widget)
        layout = QtWidgets.QVBoxLayout(central_widget)
        
        # #thin top layout for global conrol
        # top_layout = QtWidgets.QHBoxLayout()

        # initialize_button = QtWidgets.QPushButton("Initialize")
        # initialize_button.clicked.connect(self.initial_setup_and_connect)

        # top_layout.addWidget(initialize_button)
        # layout.addLayout(top_layout)

        
        # Create a horizontal layout for the main widgets
        main_widgets_layout = QtWidgets.QHBoxLayout()
        layout.addLayout(main_widgets_layout)
        
        # Create and add two MainWidget instances to the layout
        self.main_widget1 = MainWidget()
        self.main_widget2 = MainWidget()
        main_widgets_layout.addWidget(self.main_widget1)
        main_widgets_layout.addWidget(self.main_widget2)


        self.distance_layout = DistanceLayout(parent=self)
        layout.addLayout(self.distance_layout)

        self.initial_setup_and_connect()

    def initial_setup_and_connect(self):

        try:

            self.main_widget1.combobox_midichans.setCurrentIndex(1)
            self.main_widget2.combobox_midichans.setCurrentIndex(0)

            self.main_widget1.discover_objects()
            self.main_widget2.discover_objects()

            # get the list of strings from the comboboxes

            cb1_strings = [self.main_widget1.combobox_objects.itemText(i) for i in range(self.main_widget1.combobox_objects.count())]
        
            # If 'Left' is in the list, set the index to that
            for i, s in enumerate(cb1_strings):
                if 'Left' in s:
                    self.main_widget1.combobox_objects.setCurrentIndex(i)
                    self.main_widget1.connect_object()

            cb2_strings = [self.main_widget2.combobox_objects.itemText(i) for i in range(self.main_widget2.combobox_objects.count())]

            # If 'Right' is in the list, set the index to that
            for i, s in enumerate(cb2_strings):
                if 'Right' in s:
                    self.main_widget2.combobox_objects.setCurrentIndex(i)
                    self.main_widget2.connect_object()

        except Exception as e:
            print(f"Initialization Error: {e}")



def main():
    app = QtWidgets.QApplication(sys.argv)
    
    # Use the SideBySideMainWindow instead of MainWindow
    main_window = SideBySideMainWindow()
    main_window.show()
    
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()