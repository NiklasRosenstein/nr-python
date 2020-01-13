
from Qt.QtWidgets import QApplication
from Qt.QtWidgets import QWidget
from six.moves import configparser
import sys

def main():
  app = QApplication(sys.argv)
  wnd = QWidget()
  wnd.show()
  app.exec_()

if __name__ == '__main__':
  main()
