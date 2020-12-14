import os
import sys

from PyQt5 import QtCore, QtWidgets, QtWebEngineWidgets, uic

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    path_ui = os.path.join(os.path.dirname(__file__), "mainWdw.ui")
    window = uic.loadUi(path_ui)
    window.tabWidget.widget(0).findChildren(QtWebEngineWidgets.QWebEngineView)[0].load(QtCore.QUrl("https://www.google.com"))
    window.show()
    sys.exit(app.exec_())