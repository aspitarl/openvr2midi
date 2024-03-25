import sys
import pandas as pd
from PyQt5.QtCore import Qt, QAbstractTableModel, QVariant, pyqtSignal
from PyQt5.QtWidgets import QApplication, QMainWindow, QTableView, QHeaderView, QHBoxLayout, QVBoxLayout, QWidget, QPushButton, QFileDialog, QGridLayout, QLabel, QSpinBox, QLineEdit, QComboBox, QCheckBox, QDateEdit, QDateTimeEdit, QTimeEdit, QDoubleSpinBox
import os

# missing imports

from PyQt5.QtGui import QValidator

class PandasTableModel(QAbstractTableModel):

    _new_data = pyqtSignal(object) # this is a separate signal for when the data is changed from outside the model

    def __init__(self, data, parent=None):
        super().__init__(parent)
        self._data = data

    def rowCount(self, parent):
        return self._data.shape[0]

    def columnCount(self, parent):
        return self._data.shape[1]

    def data(self, index, role):
        if role == Qt.DisplayRole:
            row = index.row()
            col = index.column()
            return str(self._data.iloc[row, col])
        return QVariant()

    def headerData(self, section, orientation, role):
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return str(self._data.columns[section])
            elif orientation == Qt.Vertical:
                return str(section + 1)
        return QVariant()

    def setData(self, index, value, role):
        if role == Qt.EditRole:
            row = index.row()
            col = index.column()
            self._data.iloc[row, col] = value
            self.dataChanged.emit(index, index, [Qt.DisplayRole])
            return True
        return False

    def flags(self, index):
        return Qt.ItemIsEditable | Qt.ItemIsEnabled | Qt.ItemIsSelectable
        
    def set_new_data(self, data):
        self._data = data
        self._new_data.emit(data)

class AlphaNumericValidator(QValidator):
    def validate(self, input_str, pos):
        if input_str.isalnum():
            return QValidator.Acceptable, input_str, pos
        else:
            return QValidator.Invalid, input_str, pos

class PandasGridLayout(QVBoxLayout):
    def __init__(self, parent=None):
        super().__init__(parent)

        default_filename = 'default'

        self._load_button = QPushButton("Load")
        self._load_button.clicked.connect(self.load_data)
        self._save_button = QPushButton("Save")
        self._save_button.clicked.connect(self.save_data)

        self._fileselect_combo = QComboBox()
        # Add all files in the settings directory to the combo box
        self._fileselect_combo.addItems([f.split('.')[0] for f in os.listdir('settings') if f.endswith('.csv')])
        self._fileselect_combo.currentIndexChanged.connect(self.update_line_edit)

        self._new_filename_line_edit = QLineEdit()
        self._new_filename_line_edit.setValidator(AlphaNumericValidator(self._new_filename_line_edit))
        self.update_line_edit(0)

        df_initial = pd.read_csv('settings/' + default_filename + ".csv")
        self._grid_widget = PandasGridWidget(df_initial)

        self._button_layout = QHBoxLayout()
        self._button_layout.addWidget(self._fileselect_combo)
        self._button_layout.addWidget(self._load_button)
        self._button_layout.addWidget(self._save_button)
        self._button_layout.addWidget(self._new_filename_line_edit)
        self._layout = QVBoxLayout()
        self._layout.addWidget(self._grid_widget)
        self._layout.addLayout(self._button_layout)
        self.addLayout(self._layout)

    def save_data(self):
        file_path = 'settings/' + self._new_filename_line_edit.text() + ".csv"
        if file_path:
            self._data = self._grid_widget._table_model._data

            # Make sure the solor and send data columns are bools

            self._data['solo'] = self._data['solo'].astype(bool)
            self._data['send'] = self._data['send'].astype(bool)

            self._data.to_csv(file_path, index=False)

    def load_data(self):
        # file_path = 'settings/' + self._new_filename_line_edit.text() + ".csv"
        file_path = 'settings/' + self._fileselect_combo.currentText() + ".csv"

        if file_path:
            self._data = pd.read_csv(file_path)
            self._grid_widget.set_data(self._data)

    def update_line_edit(self, index):
        # Get the current text in the combo box
        current_text = self._fileselect_combo.itemText(index)
        # Set the text in the line edit
        self._new_filename_line_edit.setText(current_text)


class PandasGridWidget(QWidget):
    def __init__(self, data, parent=None):
        super().__init__(parent)

        
        self._current_solo_checkbox = None

        self._table_model = PandasTableModel(data)
        self._table_model._new_data.connect(self._load_data)
        self._grid_layout = QGridLayout()
        self._widgets = []
        self._widget_types = {
            'int64': QSpinBox,
            'float64': QDoubleSpinBox,
            'object': QLineEdit,
            'category': QComboBox,
            'bool': QCheckBox,
            'datetime64[ns]': QDateTimeEdit,
            'timedelta64[ns]': QTimeEdit
        }
        self._load_data()
        self.setLayout(self._grid_layout)

    def _load_data(self):
        self._widgets = []
        data = self._table_model._data
        for i, col in enumerate(data.columns):
            label = QLabel(col)
            self._grid_layout.addWidget(label, 0, i)


            for j, val in enumerate(data[col]):
                widget_type = self._widget_types[str(data.dtypes[col])]
                widget = widget_type()

                if widget_type == QDoubleSpinBox:
                    widget.setDecimals(2)
                    widget.setSingleStep(0.1)
                    widget.setMaximum(999.99)
                    widget.setMinimum(-999.99)

                widget = set_value_widget_type(widget, val)
                signal = get_widget_change_signal(widget)

                if widget_type == QCheckBox:
                    signal.connect(lambda state, i=i, j=j: self._table_model.setData(self._table_model.index(j, i), bool(state), Qt.EditRole))
                else:
                    signal.connect(lambda value, i=i, j=j: self._table_model.setData(self._table_model.index(j, i), value, Qt.EditRole))

                if col == 'solo':
                    widget.stateChanged.connect(lambda state, row=j: self._disable_send_checkboxes(state, row))

                self._grid_layout.addWidget(widget, j+1, i)
                self._widgets.append(widget)

    def _disable_send_checkboxes(self, state, row):
        send_checkbox_column = 2
        send_column_offset = send_checkbox_column*len(self._table_model._data.columns)

        solo_checkbox_column = 3
        solo_column_offset = solo_checkbox_column*len(self._table_model._data.columns)
        if state == Qt.Checked:
            if self._current_solo_checkbox is not None:
                self._current_solo_checkbox.setChecked(False)
            self._current_solo_checkbox = self._widgets[row+solo_column_offset]

            self.presolo_send_states = []
            for i in range(len(self._table_model._data)):
                if i != row:
                    send_widget = self._widgets[i+send_column_offset]
                    self.presolo_send_states.append((i, send_widget.isChecked(), send_widget.isEnabled()))
                    send_widget.setChecked(False)
                    send_widget.setEnabled(False)
        else:
            self._current_solo_checkbox = None
            for i, checked, enabled in self.presolo_send_states:
                send_widget = self._widgets[i+send_column_offset]
                send_widget.setEnabled(enabled)
                send_widget.setChecked(checked)


    def set_data(self, data):
        self._table_model._data = data
        self._load_data()
              



def get_widget_change_signal(widget):
    if isinstance(widget, QComboBox):
        return widget.currentIndexChanged
    elif isinstance(widget, QDateTimeEdit):
        return widget.dateTimeChanged
    elif isinstance(widget, QTimeEdit):
        return widget.timeChanged
    elif isinstance(widget, QDateEdit):
        return widget.dateChanged
    elif isinstance(widget, QCheckBox):
        return widget.stateChanged
    elif isinstance(widget, QLineEdit):
        return widget.textChanged
    else:
        return widget.valueChanged
    
def set_value_widget_type(widget, value):
    if isinstance(widget, QComboBox):
        widget.setCurrentIndex(value)
    elif isinstance(widget, QDateTimeEdit):
        widget.setDateTime(value)
    elif isinstance(widget, QTimeEdit):
        widget.setTime(value)
    elif isinstance(widget, QDateEdit):
        widget.setDate(value)
    elif isinstance(widget, QCheckBox):
        widget.setChecked(value)
    elif isinstance(widget, QLineEdit):
        widget.setText(value)
    else:
        widget.setValue(value)
    return widget


if __name__ == "__main__":
    app = QApplication(sys.argv)
    widget = PandasGridLayout()
    widget.show()
    sys.exit(app.exec_())