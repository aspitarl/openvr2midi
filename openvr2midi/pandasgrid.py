import sys
import pandas as pd
from PyQt5.QtCore import Qt, QAbstractTableModel, QVariant
from PyQt5.QtWidgets import QApplication, QMainWindow, QTableView, QHeaderView, QHBoxLayout, QVBoxLayout, QWidget, QPushButton, QFileDialog, QGridLayout, QLabel, QSpinBox, QLineEdit, QComboBox, QCheckBox, QDateEdit, QDateTimeEdit, QTimeEdit, QDoubleSpinBox

# missing imports

from PyQt5.QtGui import QValidator

class PandasTableModel(QAbstractTableModel):
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

class AlphaNumericValidator(QValidator):
    def validate(self, input_str, pos):
        if input_str.isalnum():
            return QValidator.Acceptable, input_str, pos
        else:
            return QValidator.Invalid, input_str, pos

class PandasGridLayout(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        default_filename = 'default'

        self._load_button = QPushButton("Load")
        self._load_button.clicked.connect(self.load_data)
        self._save_button = QPushButton("Save")
        self._save_button.clicked.connect(self.save_data)
        self._file_edit = QLineEdit()
        self._file_edit.setValidator(AlphaNumericValidator(self._file_edit))
        self._file_edit.setText(default_filename)

        df_initial = pd.read_csv('settings/' + default_filename + ".csv")
        self._grid_widget = PandasGridWidget(df_initial)

        self._button_layout = QHBoxLayout()
        self._button_layout.addWidget(self._load_button)
        self._button_layout.addWidget(self._save_button)
        self._button_layout.addWidget(self._file_edit)
        self._layout = QVBoxLayout()
        self._layout.addWidget(self._grid_widget)
        self._layout.addLayout(self._button_layout)
        self.setLayout(self._layout)

    def save_data(self):
        file_path = 'settings/' + self._file_edit.text() + ".csv"
        if file_path:
            print(file_path)
            self._data = self._grid_widget._data
            self._data.to_csv(file_path, index=False)

    def load_data(self):
        file_path = 'settings/' + self._file_edit.text() + ".csv"
        if file_path:
            self._data = pd.read_csv(file_path)
            self._grid_widget.set_data(self._data)




class PandasGridWidget(QWidget):
    def __init__(self, data, parent=None):
        super().__init__(parent)

        self._table_model = PandasTableModel(data)
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
        data = self._table_model._data
        for i, col in enumerate(data.columns):
            label = QLabel(col)
            self._grid_layout.addWidget(label, 0, i)


            for j, val in enumerate(data[col]):
                widget_type = self._widget_types[str(data.dtypes[col])]
                widget = widget_type()
                widget = set_value_widget_type(widget, val)
                signal = get_widget_change_signal(widget)
                signal.connect(lambda value, i=i, j=j: self._table_model.setData(self._table_model.index(j, i), value, Qt.EditRole))
                if col == 'solo':
                    widget.stateChanged.connect(lambda state, row=j: self._disable_send_checkboxes(state, row))
                self._grid_layout.addWidget(widget, j+1, i)
                self._widgets.append(widget)


    def set_data(self, data):
        self._table_model._data = data
        self._load_data()


    def _disable_send_checkboxes(self, state, row):

        send_checkbox_column = 2
        widget_offset = send_checkbox_column*len(self._table_model._data.columns)
        if state == Qt.Checked:
            self.presolo_send_states = []
            for i in range(len(self._table_model._data)):
                if i != row:
                    send_widget = self._widgets[i+widget_offset]
                    self.presolo_send_states.append((i, send_widget.isChecked(), send_widget.isEnabled()))
                    send_widget.setChecked(False)
                    send_widget.setEnabled(False)
        else:
            for i, checked, enabled in self.presolo_send_states:
                send_widget = self._widgets[i+widget_offset]
                send_widget.setEnabled(enabled)
                send_widget.setChecked(checked)                    



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