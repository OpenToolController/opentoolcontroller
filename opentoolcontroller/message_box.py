from PyQt5 import QtCore, QtGui, QtWidgets
#from opentoolcontroller.flags import TestingFlags

class MessageBox(QtWidgets.QMessageBox):
    def __init__(self, text, *argv):

        app = QtWidgets.QApplication.instance()

        if app is None:
            print('\nError: ',text)
            for arg in argv:
                print(arg)

        else:
            super().__init__()
            self.setText(text)
            self.setStandardButtons(QtWidgets.QMessageBox.Ok)
            btn = self.button(QtWidgets.QMessageBox.Ok)

            detailed_text = ""

            for arg in argv:
                try:
                    detailed_text += str(arg)

                except Exception as e:
                    print(e)

            if detailed_text is not "":
                self.setDetailedText(detailed_text)


            #if TestingFlags.AUTO_CLOSE_MESSAGE_BOX:
            #    QtCore.QTimer.singleShot(0, btn.clicked)
            self.exec_()
