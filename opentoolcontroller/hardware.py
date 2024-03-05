#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import subprocess
import time
import os

from threading import Thread
from queue import Queue, Empty

from PyQt5 import QtCore, QtWidgets, QtGui
from opentoolcontroller.tool_data import HalNode

from opentoolcontroller.strings import col, typ
from opentoolcontroller.strings import defaults
import ctypes
#use ctypes.c_ulong, c_long and c_float


class HalReaderGroup():
    def __init__(self, reader_periods_ms=[100]):
        super().__init__()
        self._hal_reader_periods_ms = reader_periods_ms
        self._hal_config_file = '/hal/hal_config.hal'
        self._hal_exists = False
        self._hal_readers = []

        try:
            self.setupHal()
            self.findPins()
            self._hal_exists = True
            
            for i, period_ms in enumerate(reader_periods_ms):
                self._hal_readers.append(HalReader(period_ms, i))

        except OSError as e:
            self._hal_exists = False



    def setupHal(self):
        subprocess.call(['halcmd', 'stop'])
        subprocess.check_output(['halcmd', 'unload', 'all']) #wait until cmd finishes
        time.sleep(1) #Give time for hal to unload everything
        

        period_ns_string = ''
        name_string = ''

        for i, period_ms in enumerate(self._hal_reader_periods_ms):
            n = i+1
            period_ns_string += 'period%i=%i ' % (n, 1e6*period_ms)
            name_string += 'name%i=gui_%i ' % (n, n)


        #period_ns = 'period1=%i' % (1e6*period_ms)
        subprocess.call(['halcmd', 'loadrt', 'threads', name_string, period_ns_string])

        config_full_path = defaults.TOOL_DIR + self._hal_config_file
        if os.path.isfile(config_full_path):
            subprocess.call(['halcmd', '-f', config_full_path])
            

    def halExists(self):
        return self._hal_exists
    
    def running(self):
        return self._running

    def setModel(self, value):
        self._tool_model = value

        for reader in self._hal_readers:
            reader.setModel(self._tool_model)
    
    def model(self):
        return self._tool_model
    
    def start(self):
        if self.halExists():
            for reader in self._hal_readers:
                reader.start()
            
            subprocess.call(['halcmd', 'start'])
    
    def stop(self):
        if self.halExists():
            for reader in self._hal_readers:
                reader.stop()
            
            subprocess.check_output(['halcmd', 'stop']) #wait until cmd finishes
            subprocess.check_output(['halcmd', 'unload', 'all']) #wait until cmd finishes

    def loadHalMeter(self):
        if self.running():
            try:
                subprocess.call(['halcmd', 'loadusr', 'halmeter'])
            except:
                pass

    def loadHalScope(self):
        if self.running():
            try:
                subprocess.call(['halcmd', 'loadusr', 'halscope'])
            except:
                pass

    def findPins(self):
        pins = subprocess.check_output(['halcmd', 'show', 'pin']).splitlines()
        pins.pop(0) # "Component Pins:""

        #If we don't lose the reference to the initial list then everything will update correctly
        HalNode.hal_pins.clear()

        for pin in pins:
            try:
                line = pin.decode('utf-8')
                items = line.split()

                if items[1] in ['bit', 's32', 'u32', 'float'] and items[2] in ['IN','OUT']:
                    assert isinstance(items[4], str)
                    pin = (items[4], items[1], items[2]) #(name, bit, IN)
                    HalNode.hal_pins.append(pin)
            except:
                pass






#Only setData on HAL nodes here since this is the closest to the hardware
class HalReader():
    def __init__(self, period_ms, reader_number):
        self._hal_period_ms = int(period_ms)
        self._reader_number = int(reader_number)

        self.sampler_queue = Queue()
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.processData)

        self._tool_model = None
        self.connected_sampler_pins = []
        self.connected_streamer_pins = []
        self._previous_stream = []
        self._running = False


    def setModel(self, value):
        self._tool_model = value

    def model(self):
        return self._tool_model

    def running(self):
        return self._running


    def start(self):
        #Sampler is on all the used hal pins
        self.connected_sampler_pins = self.connectedPins(HalNode.hal_pins, self.samplerIndexes())
        if len(self.connected_sampler_pins) > 0:
            self.sampler_cfg = self.cfgFromPins(self.connected_sampler_pins)
            cfg = 'cfg=' + str(self.sampler_cfg)

            subprocess.call(['halcmd', 'loadrt', 'sampler', 'depth=100', cfg])
            print("\nSampler CFG: ", self.sampler_cfg)
            self.connectSamplerSignals(self.connected_sampler_pins)

        #Streamer is only on output hal pins that are used
        self.connected_streamer_pins = self.connectedPins(HalNode.hal_pins, self.streamerIndexes())
        if len(self.connected_streamer_pins) > 0:
            self.streamer_cfg = self.cfgFromPins(self.connected_streamer_pins)
            cfg = 'cfg=' + str(self.streamer_cfg)


            subprocess.call(['halcmd', 'loadrt', 'streamer', 'depth=100', cfg])
            print("\nStreamer CFG: ", self.streamer_cfg)
            self.connectStreamerSignals(self.connected_streamer_pins)

            self._previous_stream = self.baseStream(self.streamer_cfg)

        self.timer.start(self._hal_period_ms)
        self._running = True


    def stop(self):
        self.timer.stop()
        self._running = False



    '''Add something to check what streamer to use! '''
    def samplerIndexes(self):
        return self.model().indexesOfTypes([typ.D_IN_NODE, typ.D_OUT_NODE, typ.A_IN_NODE, typ.A_OUT_NODE])

        indexes = []
        if self.model() is not None:
            tool_model = self.model()
            tool_index = tool_model.index(0, 0, QtCore.QModelIndex())
            indexes += tool_model.indexesOfType(typ.D_IN_NODE, tool_index)
            indexes += tool_model.indexesOfType(typ.D_OUT_NODE, tool_index)
            indexes += tool_model.indexesOfType(typ.A_IN_NODE, tool_index)
            indexes += tool_model.indexesOfType(typ.A_OUT_NODE, tool_index)

        return indexes


    def streamerIndexes(self):
        indexes = []

        if self.model() is not None:
            tool_model = self.model()
            tool_index = tool_model.index(0, 0, QtCore.QModelIndex())
            indexes += tool_model.indexesOfType(typ.D_OUT_NODE, tool_index)
            indexes += tool_model.indexesOfType(typ.A_OUT_NODE, tool_index)

        return indexes


    def pinTypeToChar(self, pin_type):
        if pin_type == 'bit':
            return 'b'
        elif pin_type == 's32':
            return 's'
        elif pin_type == 'u32':
            return 'u'
        elif pin_type == 'float':
            return 'f'


    def pinNameToType(self, pin_name):
        all_pins = HalNode.hal_pins #list of (name, type, dir)
        pin_info = [item for item in all_pins if item[0] == pin_name]
        pin_type = pin_info[0][1]

        return pin_type


    def pinNameToChar(self, pin_name):
        return self.pinTypeToChar(self.pinNameToType(pin_name))


    def connectedPins(self, hal_pins, indexes):
        connected_pins = {}

        for pin_name, dir, type in hal_pins:
            pin_indexes = []

            for index in indexes:
                node = index.internalPointer()

                if pin_name == node.halPin:
                    pin_indexes.append(index)

            if pin_indexes:
                connected_pins[pin_name] = pin_indexes

        return connected_pins


    def cfgFromPins(self, connected_pins):
        cfg = ''
        for pin_name in connected_pins:
            cfg += self.pinNameToChar(pin_name)

        return cfg


    def connectSamplerSignals(self, connected_pins):
        for i, pin_name in enumerate(connected_pins):
            index = connected_pins[pin_name][0]
            node = index.internalPointer()

            signal_name = node.signalName()
            if len(connected_pins[pin_name]) > 1: #signify pin has multiple connections
                signal_name += '*'

            #subprocess.call(['halcmd', 'net', signal_name, pin_name, '=>','sampler.0.pin.'+str(i)])
            subprocess.call(['halcmd', 'net', signal_name, pin_name, '=>','sampler.'+str(self._reader_number)+'.pin.'+str(i)])

        #node.setSamplerPins(node_sampler_pins) # This is a list of indexes
        subprocess.call(['halcmd', 'setp', 'sampler.'+str(self._reader_number)+'.enable', 'True'])
        subprocess.call(['halcmd', 'addf', 'sampler.'+str(self._reader_number), 'gui'])


        # Sampler userspace component, stdbuf fixes bufering issue
        self.p_sampler = subprocess.Popen(['stdbuf', '-oL', 'halcmd', 'loadusr', 'halsampler', '-c', '0', '-t'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, bufsize=1)

        t = Thread(target=self.enqueue_sampler, args=(self.p_sampler.stdout, self.sampler_queue))
        t.daemon = True
        t.start()


    def connectStreamerSignals(self, connected_pins):
        for i, pin_name in enumerate(connected_pins):
            index = connected_pins[pin_name][0]
            node = index.internalPointer()

            signal_name = node.signalName()
            if len(connected_pins[pin_name]) > 1: #signify pin has multiple connections
                raise ValueError("Cannot have halpin connected from multiple output nodes")

            subprocess.call(['halcmd', 'net', signal_name, pin_name, '=>','streamer.'+str(self._reader_number)+'.pin.'+str(i)])

        #node.setSamplerPins(node_sampler_pins) # This is a list of indexes
        subprocess.call(['halcmd', 'setp', 'streamer.'+str(self._reader_number)+'.enable', 'True'])
        subprocess.call(['halcmd', 'addf', 'streamer.'+str(self._reader_number), 'gui'])


        # Streamer userspace component, stdbuf fixes bufering issue
        self.p_streamer = subprocess.Popen(['halcmd', 'loadusr', 'halstreamer', '-c', '0'], stdin=subprocess.PIPE, stderr=subprocess.STDOUT)



    def processData(self):
        if len(self.connected_sampler_pins) > 0:
            self.readSampler()

        if len(self.connected_streamer_pins) > 0:
            self.writeStreamer()


    def readSampler(self):
        number_reads = 0
        while not self.sampler_queue.empty():
            number_reads += 1
            data = self.sampler_queue.get_nowait()
            #print('sampler:', data)

            data = data.split(b' ')
            data.pop(-1) #remove trailing b'\n'
            current_sample = int(data[0])
            data.pop(0)

            #read pin value then send to model
            for i, pin in enumerate(self.connected_sampler_pins):

                if self.sampler_cfg[i] == 'b':
                    val = bool(int(data[i])) #b'0' to False, b'1' to True

                elif self.sampler_cfg[i] in ['s','u']:
                    val = int(data[i])

                elif self.sampler_cfg[i] == 'f':
                    val = float(data[i])

                for index in self.connected_sampler_pins[pin]:
                    if val != self._tool_model.data(index.siblingAtColumn(col.HAL_VALUE), QtCore.Qt.DisplayRole):
                        self._tool_model.setData(index.siblingAtColumn(col.HAL_VALUE), val)
                        #print("setting: ", 
                        #      index.internalPointer().name,  ': ', val, ' was ', 
                        #      self._tool_model.data(index.siblingAtColumn(col.HAL_VALUE), QtCore.Qt.DisplayRole))

        if number_reads > 1:
            print(number_reads, " sampler reads")

    def baseStream(self, cfg):
        stream = []
        for item in cfg:
            stream.append(0)
        return stream

    def writeStreamer(self):
        # Need to go throught the streamer pins and form the new stream
        new_stream = self._previous_stream[:]

        for i, pin in enumerate(self.connected_streamer_pins):
            index = self.connected_streamer_pins[pin][0] #outputs only have 1 index per signal
            node = index.internalPointer()

            new_val = node.halQueueGet()
            if new_val is not None:
                if node.halPinType() in ['bit','s32','u32']:
                    #print('halQueueGet', int(new_val))
                    new_val = int(new_val) #It wants a 0 or 1 for False/True
                elif node.halPinType() == 'float':
                    new_val = float(new_val)

                new_stream[i] = new_val

        if new_stream != self._previous_stream:
            print("new_stream: ", new_stream)
            tmp = ''
            for item in new_stream:
                tmp += str(item) #This might need some truncation
                tmp += ' '

            tmp = tmp[:-1]+'\n'

            self.p_streamer.stdin.write( tmp.encode() )#hstrip brackets, add \n and convert to bytes
            self.p_streamer.stdin.flush()
            self._previous_stream = new_stream


    def enqueue_sampler(self, out, queue):
        for line in iter(out.readline, b''):
            queue.put(line)
        out.close()










    #########################
    #old stuff
    #########################


    #sudo halcompile --install opentoolcontroller/HAL/hardware_sim.comp
    #subprocess.call(['halcmd', 'loadrt', 'hardware_sim'])

    #def setupHalEthercat(self):
    #    if self._hal_exists:
    #        subprocess.call(['halcmd', 'loadusr', '-W', 'lcec_conf', 'ethercat_config.xml'])
    #        subprocess.call(['halcmd', 'loadrt', 'lcec'])
    #        subprocess.call(['halcmd', 'addf', 'lcec.read-all', 'gui'])
    #        subprocess.call(['halcmd', 'addf', 'lcec.write-all', 'gui'])

    #def setupHalTesting(self):
    #    #Simulating a digital input with siggen.0.square in tool_model_1
    #    #subprocess.call(['halcmd', 'loadrt', 'siggen'])
    #    #subprocess.call(['halcmd', 'addf', 'siggen.0.update', 'gui'])
    #    #subprocess.call(['halcmd', 'setp', 'siggen.0.amplitude', '0.5'])
    #    #subprocess.call(['halcmd', 'setp', 'siggen.0.offset', '0.5'])
    #    #subprocess.call(['halcmd', 'setp', 'siggen.0.frequency', '0.5'])

    #    subprocess.call(['halcmd', 'loadrt', 'sim_encoder', 'num_chan=1'])
    #    subprocess.call(['halcmd', 'setp', 'sim-encoder.0.speed', '0.005'])
    #    subprocess.call(['halcmd', 'addf', 'sim-encoder.make-pulses', 'gui'])
    #    subprocess.call(['halcmd', 'addf', 'sim-encoder.update-speed', 'gui'])


