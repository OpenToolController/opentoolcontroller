#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import subprocess
import time
import sys
from PyQt5 import QtCore, QtGui, QtWidgets

def halSetup():

    subprocess.call(['halcmd', 'stop'])
    subprocess.call(['halcmd', 'unload', 'all'])

    subprocess.call(['halcmd', 'loadrt', 'threads', 'name1=servo', 'period1=1000000', 'name2=gui', 'period2=100000000'])

    ##### Signal Generator #####
    subprocess.call(['halcmd', 'loadrt', 'siggen'])
    subprocess.call(['halcmd', 'addf', 'siggen.0.update', 'servo'])
    subprocess.call(['halcmd', 'setp', 'siggen.0.frequency', '0.1'])
    subprocess.call(['halcmd', 'setp', 'siggen.0.amplitude', '10.'])

    ##### Sampler #####
    subprocess.call(['halcmd', 'loadrt', 'sampler', 'depth=100', 'cfg=fff'])
    subprocess.call(['halcmd', 'addf', 'sampler.0', 'gui'])
    subprocess.call(['halcmd', 'setp', 'sampler.0.enable', 'True'])

    ##### Streamer #####
    subprocess.call(['halcmd', 'loadrt', 'streamer', 'depth=100', 'cfg=b'])
    subprocess.call(['halcmd', 'addf', 'streamer.0', 'gui'])
    subprocess.call(['halcmd', 'setp', 'streamer.0.enable', 'False'])
    subprocess.call(['halcmd', 'net', 'streamer_net', 'streamer.0.pin.0'])

    subprocess.call(['halcmd', 'net', 'net_1', 'siggen.0.sine', '=>','sampler.0.pin.0'])
    subprocess.call(['halcmd', 'net', 'net_2', 'siggen.0.cosine', '=>','sampler.0.pin.1'])
    subprocess.call(['halcmd', 'net', 'net_3', 'siggen.0.sawtooth', '=>','sampler.0.pin.2'])


    ###### EtherCAT ######
    #subprocess.call(['halcmd', 'loadusr', '-W', 'lcec_conf', 'ethercat_config.xml'])
    #subprocess.call(['halcmd', 'loadrt', 'lcec'])
    #subprocess.call(['halcmd', 'addf', 'lcec.read-all', 'servo'])
    #subprocess.call(['halcmd', 'addf', 'lcec.write-all', 'servo'])
    #subprocess.call(['halcmd', 'net', 'test_net', 'lcec.0.1.din-1', '=>','sampler.0.pin.0'])

    subprocess.call(['halcmd', 'start'])
    subprocess.call(['halcmd', 'loadusr', 'halmeter'])


class Form(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QtWidgets.QVBoxLayout()
        self.b1 = QtWidgets.QPushButton("1-ON")
        self.b2 = QtWidgets.QPushButton("1-OFF")
        self.b3 = QtWidgets.QPushButton("2-ON")
        self.b4 = QtWidgets.QPushButton("2-OFF")
        self.b5 = QtWidgets.QPushButton("Push True")
        self.b6 = QtWidgets.QPushButton("Push False")
        self.b7 = QtWidgets.QPushButton("STREAM")

        self.in_1 = QtWidgets.QLabel('unknown')
        self.in_2 = QtWidgets.QLabel('unknown')
        self.in_3 = QtWidgets.QLabel('unknown')

        layout.addWidget(self.b1)
        layout.addWidget(self.b2)
        layout.addWidget(self.b3)
        layout.addWidget(self.b4)
        layout.addWidget(self.b5)
        layout.addWidget(self.b6)
        layout.addWidget(self.b7)
        layout.addWidget(self.in_1)
        layout.addWidget(self.in_2)
        layout.addWidget(self.in_3)

        self.b1.clicked.connect(self.DOUT_1_ON)
        self.b2.clicked.connect(self.DOUT_1_OFF)
        self.b3.clicked.connect(self.DOUT_2_ON)
        self.b4.clicked.connect(self.DOUT_2_OFF)
        self.b5.clicked.connect(self.PUSH_TRUE)
        self.b6.clicked.connect(self.PUSH_FALSE)
        self.b7.clicked.connect(self.STREAM)

        #self.b2.clicked.connect(lambda:self.whichbtn(self.b2))
        self.setWindowTitle("Testing halcmd interface")

        self.setLayout(layout)

        #self.timer = QtCore.QTimer()
        #self.timer.timeout.connect(self.update_in_1)
        #self.timer.start(500)


        self.thread = SamplerThread()
        self.thread.signal_1.connect(self.update_1)
        self.thread.signal_2.connect(self.update_2)
        self.thread.signal_3.connect(self.update_3)
        self.thread.start()

    def update_1(self, value):
        self.in_1.setText(value)

    def update_2(self, value):
        self.in_2.setText(value)

    def update_3(self, value):
        self.in_3.setText(value)


    def DOUT_1_ON(self):
        subprocess.call(['halcmd', 'setp', 'sampler.0.enable', 'True'])
        #subprocess.call(['halcmd', 'setp', 'lcec.0.3.dout-0','True'])

    def DOUT_1_OFF(self):
        subprocess.call(['halcmd', 'setp', 'sampler.0.enable', 'False'])
        #subprocess.call(['halcmd', 'setp', 'lcec.0.3.dout-0','False'])

    def DOUT_2_ON(self):
        subprocess.call(['halcmd', 'setp', 'siggen.0.frequency', '0.1'])
        #subprocess.call(['halcmd', 'setp', 'lcec.0.3.dout-1','True'])

    def DOUT_2_OFF(self):
        subprocess.call(['halcmd', 'setp', 'siggen.0.frequency', '0.5'])
        #subprocess.call(['halcmd', 'setp', 'lcec.0.3.dout-1','False'])

    def PUSH_TRUE(self):
        cmd = ['halcmd', 'loadusr', 'halstreamer', '-c', '0']
        p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
        reply = p.communicate(input='1\n')[0]
        print(reply)

    def PUSH_FALSE(self):
        cmd = ['halcmd', 'loadusr', 'halstreamer', '-c', '0']
        p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
        reply = p.communicate(input='0\n')[0]
        print(reply)


    def STREAM(self):
        subprocess.call(['halcmd', 'setp', 'streamer.0.enable', 'True'])
        time.sleep(1)
        subprocess.call(['halcmd', 'setp', 'streamer.0.enable', 'False'])

    def update_in_1(self):
        print('update_in_1')
        output = subprocess.check_output(['halcmd', 'getp', 'lcec.0.1.din-0'])
        output =  output.decode('ascii')
        output = output.strip()

        if output == 'TRUE':
            self.in_1.setText('On')
        else:
            self.in_1.setText('Off')



class SamplerThread(QtCore.QThread):
    signal_1 = QtCore.pyqtSignal('PyQt_PyObject')
    signal_2 = QtCore.pyqtSignal('PyQt_PyObject')
    signal_3 = QtCore.pyqtSignal('PyQt_PyObject')

    def __init__(self):
        QtCore.QThread.__init__(self)

    def run(self):
        #the command returns after it's filled 'n' samples
        cmd  = ['halcmd', 'loadusr', 'halsampler', '-c', '0','-n', '1','-t']
        while True:
            p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
            #print('\nhalsampler')
            for line in p.stdout:
               # print('>>>> ', line, end='') # process line here
                self.signal_1.emit(line.split()[1])
                self.signal_2.emit(line.split()[2])
                self.signal_3.emit(line.split()[3])


def main():
    halSetup()

    app = QtWidgets.QApplication(sys.argv)

    form = Form()
    form.show()

    ret = app.exec_()

    subprocess.call(['halcmd', 'stop'])
    subprocess.call(['halcmd', 'unload', 'all'])
    subprocess.call(['halrun', '-U'])

    sys.exit(ret)

if __name__ == '__main__':
    main()



#try:
#    output = subprocess.check_output(['halcmd', 'status'], universal_newlines=True)
#except subprocess.CalledProcessError as e:
#    output = e.output
#print(output)
