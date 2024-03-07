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
    def __init__(self):
        super().__init__()
        self._tool_model = None
        self._realtime_period_ms = None
        self._hal_reader_periods_ms = []
        self._hal_config_file = '/hal/hal_config.hal'
        self._hal_exists = False
        self._hal_readers = []
        self._running = False

        try:
            subprocess.run(['halcmd'], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self._hal_exists = True
        except subprocess.CalledProcessError:
            self._hal_exists = False

    def setPeriods(self, realtime_period_ms=50, reader_periods_ms=[100]):
        self._realtime_period_ms = realtime_period_ms
        self._hal_reader_periods_ms = reader_periods_ms

        if self._hal_exists:
            self.setupHal()
            self.findPins()
            
    def buildReaders(self):
        for i, period_ms in enumerate(self._hal_reader_periods_ms):
            self._hal_readers.append(HalReader(period_ms, i))



    def setupHal(self):
        subprocess.call(['halcmd', 'stop'])
        subprocess.check_output(['halcmd', 'unload', 'all']) #wait until cmd finishes
        time.sleep(1) #Give time for hal to unload everything
        
        realtime_period_ns = self._realtime_period_ms * 1e6
        name_string_list = ['name1=ethercat']
        period_ns_string_list = ['period1=%i'%realtime_period_ns]

        for i, period_ms in enumerate(self._hal_reader_periods_ms):
            n = i+1
            name_string_list.append('name%i=gui_%i' % (n+1, n))
            period_ns_string_list.append('period%i=%i' % (n+1, 1e6*period_ms))


        combo = name_string_list + period_ns_string_list
        subprocess.call(['halcmd', 'loadrt', 'threads', *combo])

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
        if not self.halExists():
            return

        #Build the cfgs
        self._sampler_cfgs = []
        self._streamer_cfgs = []

        for reader in self._hal_readers:
            self._sampler_cfgs.append(reader.samplerCFG())
            self._streamer_cfgs.append(reader.streamerCFG())
            print("\n sampler:", reader.samplerCFG())
            print("\n streamer:", reader.streamerCFG())
           

        cfg = ','.join(self._sampler_cfgs)
        cfg = f"cfg={cfg}"

        subprocess.call(['halcmd', 'loadrt', 'sampler', 'depth=100', cfg])
        print(f"Sampler Config:  {cfg}")

        cfg = ','.join(self._streamer_cfgs)
        cfg = f"cfg={cfg}"

        subprocess.call(['halcmd', 'loadrt', 'streamer', 'depth=100', cfg])
        print(f"Streamer Config:  {cfg}")


        #Connect the signals and start
        for reader in self._hal_readers:
            reader.connectSamplerSignals()
            reader.connectStreamerSignals()
            reader.start()
        
        subprocess.call(['halcmd', 'start'])
        self._running = True
        


    
    def stop(self):
        if self.halExists():
            for reader in self._hal_readers:
                reader.stop()
            
            subprocess.check_output(['halcmd', 'stop']) #wait until cmd finishes
            subprocess.check_output(['halcmd', 'unload', 'all']) #wait until cmd finishes
        self._running = False

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
        self._previous_stream = []
        self._running = False

        self._sampler_cfg = ''
        self._connected_sampler_pins = ''
        self._connected_streamer_pins = '' 

    def setModel(self, value):
        self._tool_model = value
        self._connected_sampler_pins = self.connectedPins(HalNode.hal_pins, self.samplerIndexes())
        self._connected_streamer_pins = self.connectedPins(HalNode.hal_pins, self.streamerIndexes())

    def model(self):
        return self._tool_model

    def running(self):
        return self._running

    def samplerCFG(self):
        return self.cfgFromPins(self._connected_sampler_pins)

    def streamerCFG(self):
        return self.cfgFromPins(self._connected_streamer_pins)

    def start(self):
        if len(self._connected_streamer_pins) > 0:
            self._previous_stream = self.baseStream(self.streamerCFG())

        self.timer.start(self._hal_period_ms)
        self._running = True


        #Sampler is on all the used hal pins
        #self.connected_sampler_pins = self.connectedPins(HalNode.hal_pins, self.samplerIndexes())


#        if len(self.connected_sampler_pins) > 0:
#            self.sampler_cfg = self.cfgFromPins(self.connected_sampler_pins)
#            cfg = 'cfg=' + str(self.sampler_cfg)
#
#            subprocess.call(['halcmd', 'loadrt', 'sampler', 'depth=100', cfg])
#            print("\nSampler CFG: ", self.sampler_cfg)
#            self.connectSamplerSignals(self.connected_sampler_pins)
#
        #Streamer is only on output hal pins that are used
#        self.connected_streamer_pins = self.connectedPins(HalNode.hal_pins, self.streamerIndexes())
#        if len(self.connected_streamer_pins) > 0:
#            self.streamer_cfg = self.cfgFromPins(self.connected_streamer_pins)
#            cfg = 'cfg=' + str(self.streamer_cfg)
#
#
#            subprocess.call(['halcmd', 'loadrt', 'streamer', 'depth=100', cfg])
#            print("\nStreamer CFG: ", self.streamer_cfg)
#            self.connectStreamerSignals(self.connected_streamer_pins)






    
    def connectSamplerSignals(self):
        connected_pins = self._connected_sampler_pins + 1
        sampler_number = self._reader_number

        for i, pin_name in enumerate(connected_pins):
            index = connected_pins[pin_name][0]
            node = index.internalPointer()

            signal_name = node.signalName()
            if len(connected_pins[pin_name]) > 1: #signify pin has multiple connections
                signal_name += '*'

            #subprocess.call(['halcmd', 'net', signal_name, pin_name, '=>','sampler.0.pin.'+str(i)])
            subprocess.call(['halcmd', 'net', signal_name, pin_name, '=>','sampler.'+str(sampler_number)+'.pin.'+str(i)])

        #node.setSamplerPins(node_sampler_pins) # This is a list of indexes
        subprocess.call(['halcmd', 'setp', 'sampler.'+str(sampler_number)+'.enable', 'True'])
        subprocess.call(['halcmd', 'addf', 'sampler.'+str(sampler_number), 'gui'])


        # Sampler userspace component, stdbuf fixes bufering issue
        self.p_sampler = subprocess.Popen(['stdbuf', '-oL', 'halcmd', 'loadusr', 'halsampler', '-c', str(sampler_number), '-t'], 
                                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT, bufsize=1)

        t = Thread(target=self.enqueue_sampler, args=(self.p_sampler.stdout, self.sampler_queue))
        t.daemon = True
        t.start()


    def connectStreamerSignals(self):
        connected_pins = self._connected_streamer_pins + 1
        streamer_number = self._reader_number

        for i, pin_name in enumerate(connected_pins):
            index = connected_pins[pin_name][0]
            node = index.internalPointer()

            signal_name = node.signalName()
            if len(connected_pins[pin_name]) > 1: #signify pin has multiple connections
                raise ValueError("Cannot have halpin connected from multiple output nodes")

            subprocess.call(['halcmd', 'net', signal_name, pin_name, '=>','streamer.'+str(streamer_number)+'.pin.'+str(i)])

        #node.setSamplerPins(node_sampler_pins) # This is a list of indexes
        subprocess.call(['halcmd', 'setp', 'streamer.'+str(streamer_number)+'.enable', 'True'])
        subprocess.call(['halcmd', 'addf', 'streamer.'+str(streamer_number), 'gui'])

        # Streamer userspace component, stdbuf fixes bufering issue
        self.p_streamer = subprocess.Popen(['halcmd', 'loadusr', 'halstreamer', '-c', str(streamer_number)], 
                                           stdin=subprocess.PIPE, stderr=subprocess.STDOUT)



    def samplerIndexes(self):
        indexes = []
        
        for index in self.model().indexesOfTypes([typ.D_IN_NODE, typ.D_OUT_NODE, typ.A_IN_NODE, typ.A_OUT_NODE]):
            node = index.internalPointer()
            if node.parent().halReaderNumber == self._reader_number:
                indexes.append(index)

        return indexes


    def streamerIndexes(self):
        indexes = []
        
        for index in self.model().indexesOfTypes([typ.D_OUT_NODE, typ.A_OUT_NODE]):
            node = index.internalPointer()
            if node.parent().halReaderNumber == self._reader_number:
                indexes.append(index)

        return indexes


    def stop(self):
        self.timer.stop()
        self._running = False


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


    def cfgFromPins(self, connected_pins):
        cfg = ''
        for pin_name in connected_pins:
            cfg += self.pinNameToChar(pin_name)

        return cfg


    def processData(self):
        if len(self._connected_sampler_pins) > 0:
            self.readSampler()

        if len(self._connected_streamer_pins) > 0:
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
            for i, pin in enumerate(self._connected_sampler_pins):

                if self._sampler_cfg[i] == 'b':
                    val = bool(int(data[i])) #b'0' to False, b'1' to True

                elif self._sampler_cfg[i] in ['s','u']:
                    val = int(data[i])

                elif self._sampler_cfg[i] == 'f':
                    val = float(data[i])

                for index in self._connected_sampler_pins[pin]:
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
        new_stream = self._previous_stream[:] # Make a copy so it can be compared to the previous one

        for i, pin in enumerate(self.connected_streamer_pins):
            index = self.connected_streamer_pins[pin][0] #outputs only have 1 index per signal
            node = index.internalPointer()

            new_val = node.halQueueGet()
            if new_val is not None:
                if node.halPinType() in ['bit','s32','u32']:
                    new_val = int(new_val) #It wants a 0 or 1 for False/True
                elif node.halPinType() == 'float':
                    new_val = float(new_val)

                new_stream[i] = new_val

        if new_stream != self._previous_stream:
            print("new_stream: ", new_stream)
            tmp = ''
            for item in new_stream:
                tmp += str(item) #TODO This might need some truncation
                tmp += ' '

            tmp = tmp[:-1]+'\n'

            self.p_streamer.stdin.write( tmp.encode() )#hstrip brackets, add \n and convert to bytes
            self.p_streamer.stdin.flush()
            self._previous_stream = new_stream


    def enqueue_sampler(self, out, queue):
        for line in iter(out.readline, b''):
            queue.put(line)
        out.close()



