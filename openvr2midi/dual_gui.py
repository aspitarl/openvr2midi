from PyQt5 import QtWidgets
import sys

from midivr_gui import MainWidget

class SideBySideMainWindow(QtWidgets.QMainWindow):
    def __init__(self, parent=None):
        super(SideBySideMainWindow, self).__init__(parent)
        
        # Create a central widget and set a horizontal layout
        central_widget = QtWidgets.QWidget(self)
        self.setCentralWidget(central_widget)
        layout = QtWidgets.QHBoxLayout(central_widget)
        
        # Create and add two MainWidget instances to the layout
        self.main_widget1 = MainWidget()
        self.main_widget2 = MainWidget()
        layout.addWidget(self.main_widget1)
        layout.addWidget(self.main_widget2)

def main():
    app = QtWidgets.QApplication(sys.argv)
    
    # Use the SideBySideMainWindow instead of MainWindow
    main_window = SideBySideMainWindow()
    main_window.show()
    
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()