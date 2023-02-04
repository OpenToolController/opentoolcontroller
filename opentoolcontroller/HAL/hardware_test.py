#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import subprocess
import time
import sys
from PyQt5 import QtCore, QtGui, QtWidgets

def halSetup():

    subprocess.call(['halcmd', 'stop'])
    subprocess.call(['halcmd', 'unload', 'all'])

    subprocess.call(['halcmd', 'loadusr', '-W', 'lcec_conf', 'ethercat_config.xml'])
    subprocess.call(['halcmd', 'loadrt', 'lcec'])

    subprocess.call(['halcmd', 'loadrt', 'threads', 'name1=servo', 'period1=1000000', 'name2=gui', 'period2=100000000'])
    subprocess.call(['halcmd', 'show', 'thread'])


    subprocess.call(['halcmd', 'addf', 'lcec.read-all', 'servo'])
    subprocess.call(['halcmd', 'addf', 'lcec.write-all', 'servo'])



    ##### Sampler #####
    subprocess.call(['halcmd', 'loadrt', 'sampler', 'depth=100', 'cfg=b'])
    subprocess.call(['halcmd', 'net', 'test_net', 'lcec.0.1.din-1', '=>','sampler.0.pin.0'])

    subprocess.call(['halcmd', 'setp', 'sampler.0.enable', 'True'])
    subprocess.call(['halcmd', 'addf', 'sampler.0', 'gui'])


    #subprocess.call(['halcmd', 'loadusr', 'halsampler', '-c', '0', 'test_samples.txt'])

    #try:
    #    output = subprocess.check_output(['halcmd', 'loadusr', 'halsampler', '-c', '0'])
    #except subprocess.CalledProcessError as e:
    #    output = e.output
    #print(output)

    subprocess.call(['halcmd', 'start'])
    subprocess.call(['halcmd', 'loadusr', 'halmeter'])

    #output = subprocess.Popen(['halcmd', 'loadusr', 'halsampler', '-c', '0', '-n', '1', '-t'], stdout=subprocess.PIPE,
    #                                                                                           stderr=subprocess.STDOUT)


    #for line in iter(output.stdout.readline, b''):
    #    print(">>> " + line.rstrip())





    #subprocess.call(['halcmd', 'setp', 'lcec.0.3.dout-3','True'])


    #for i in range(0,5):
    #    subprocess.call(['halcmd', 'setp', 'lcec.0.3.dout-3','True'])
    #    time.sleep(.1)
    #    subprocess.call(['halcmd', 'setp', 'lcec.0.3.dout-0','False'])
    #    time.sleep(.1)





class Form(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QtWidgets.QVBoxLayout()
        self.b1 = QtWidgets.QPushButton("1-ON")
        self.b2 = QtWidgets.QPushButton("1-OFF")
        self.b3 = QtWidgets.QPushButton("2-ON")
        self.b4 = QtWidgets.QPushButton("2-OFF")

        self.in_1 = QtWidgets.QLabel('unknown')

        layout.addWidget(self.b1)
        layout.addWidget(self.b2)
        layout.addWidget(self.b3)
        layout.addWidget(self.b4)
        layout.addWidget(self.in_1)

        self.b1.clicked.connect(self.DOUT_1_ON)
        self.b2.clicked.connect(self.DOUT_1_OFF)
        self.b3.clicked.connect(self.DOUT_2_ON)
        self.b4.clicked.connect(self.DOUT_2_OFF)

        #self.b2.clicked.connect(lambda:self.whichbtn(self.b2))
        self.setWindowTitle("Testing halcmd interface")

        self.setLayout(layout)

        #self.timer = QtCore.QTimer()
        #self.timer.timeout.connect(self.update_in_1)
        #self.timer.start(500)



 #       self.p = subprocess.Popen(['halcmd', 'loadusr', 'halsampler', '-c', '0','-t'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)

        #self.timer2 = QtCore.QTimer()
        #self.timer2.timeout.connect(self.buffer_test)
        #self.timer2.start(2000)


        self.thread = SamplerThread()
        #self.thread.finished.connect(app.exit)
        self.thread.signal.connect(self.update)
        self.thread.start()
        self.update("ham")

    def update(self, value):
        self.in_1.setText(value)


    def DOUT_1_ON(self):
        subprocess.call(['halcmd', 'setp', 'lcec.0.3.dout-0','True'])

    def DOUT_1_OFF(self):
        subprocess.call(['halcmd', 'setp', 'lcec.0.3.dout-0','False'])

    def DOUT_2_ON(self):
        subprocess.call(['halcmd', 'setp', 'lcec.0.3.dout-1','True'])

    def DOUT_2_OFF(self):
        subprocess.call(['halcmd', 'setp', 'lcec.0.3.dout-1','False'])


    def update_in_1(self):
        print('update_in_1')
        output = subprocess.check_output(['halcmd', 'getp', 'lcec.0.1.din-0'])
        output =  output.decode('ascii')
        output = output.strip()

        if output == 'TRUE':
            self.in_1.setText('On')
        else:
            self.in_1.setText('Off')


        #output = subprocess.check_output(['halcmd', 'loadusr', 'halsampler', '-c', '0', '-n', '4', '-t'])
        #output =  output.decode('ascii')


class SamplerThread(QtCore.QThread):
    signal = QtCore.pyqtSignal('PyQt_PyObject')

    def __init__(self):
        QtCore.QThread.__init__(self)



    def run(self):
        #self.p = subprocess.Popen(['halcmd', 'loadusr', 'halsampler', '-c', '0','-t'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)


        while True:
            output = subprocess.check_output(['halcmd', 'loadusr', 'halsampler', '-c', '0', '-n', '5', '-t'])
            output =  output.decode('ascii')

            self.signal.emit(output)
            time.sleep(.5)







def main():
    halSetup()

    app = QtWidgets.QApplication(sys.argv)

    form = Form()
    form.show()

    ret = app.exec_()

    subprocess.call(['halcmd', 'stop'])
    subprocess.call(['halcmd', 'unload', 'all'])

    sys.exit(ret)

if __name__ == '__main__':
    main()



#try:
#    output = subprocess.check_output(['halcmd', 'status'], universal_newlines=True)
#except subprocess.CalledProcessError as e:
#    output = e.output
#print(output)
