#!/bin/env python3
#
# Interface with siglent sdg2000x arbitrary waveform generator
#
#
import sys
import socket
import time
import re
import string
import struct
from itertools import pairwise
from contextlib import suppress

class SDG2000XNetworkException(Exception):
    pass

class SDG2000XParameterException(Exception):
    pass


class SDG2000X:

    PORT = 5025

    def __init__(self, ip, port=PORT):
        self.ip = ip
        self.rSocket = None
        try:
            self.rSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        except socket.error:
            raise SDG2000XNetworkException ('Failed to create socket')
        try:
            self.rSocket.connect ((self.ip, 5025))
            self.rSocket.settimeout (2.0)
        except socket.error:
            raise SDG2000XNetworkException (f'Failed to connect to: {self.ip}')

        # Get builtin and user waveforms
        self.builtins = self.getBuiltinWaveforms ()
        self.user = self.getUserWaveforms ()
        
    def __enter__(self):
        return self

    def __exit__ (self, exc_type, exc_value, traceback):
        self.cleanup ()

    def cleanup (self):
        if self.rSocket != None:
            self.rSocket.close ()
            self.rSocket = None

    def _send(self, cmd, binary=None):
        if self.rSocket is None:
            raise SDG2000XNetworkException ('Network connection is closed')
        try:
            cmd = cmd.encode('ascii')
            print (cmd)
            self.rSocket.sendall (cmd)
            if binary:
                self.rSocket.sendall (binary)
            self.rSocket.sendall (b'\n')
            time.sleep (0.2)
        except:
            raise SDG2000XNetworkException ('Failed to send data')

    def _recv(self, cnt):
        try:
            return self.rSocket.recv (cnt)
        except:
            raise SDG2000XNetworkException ('Failed to get response')
        
    def _sendRecv(self, cmd, decode=None) -> dict:
        try:
            self._send (cmd)
            resp = self.rSocket.recv (8192)
        except:
            raise SDG2000XNetworkException ('Failed to get response')
        if decode:
            resp = resp.decode (decode)
        return resp.strip()
    
    def toDict(self, keys, vals) -> dict:
        if not isinstance (vals, list):
            vals = vals.split (',')
        if len (keys) != len (vals):
            raise SDG2000XParameterException ('key_len != returned val_len')
        return dict(zip (keys, vals))

    def getID(self) -> dict:
        '''
        *IDN
        Siglent Technologies,SDG2122X,0123456789,2.01.01.37R6
        '''
        resp = self._sendRecv ('*IDN?', decode='ascii')
        return self.toDict (['manufacturer','model','serial','version'], resp)

    def getBuiltinWaveforms(self) -> dict:
        '''
        STL?
        STL Mxx, Name1, Myy, Name2
        '''
        d = {}
        resp = self._sendRecv ('STL?', decode='ascii')[4:].split (',')
        it = pairwise (resp)
        for idx, name in it:
            d[name.strip()] = idx.strip()
            with suppress (Exception):
                next (it)
        return d

    def getUserWaveforms(self) -> list:
        resp = self._sendRecv ('STL? USER', decode='ascii')[9:].split (',')
        return resp

    def getWaveformList(self) -> list:
        return list(self.builtins.keys()) + self.user
    
    def getWaveform(self, name) -> dict:
        '''
        WVDT? Mn or WVDT? USER,name
        WVDT POS,storage, WVNM, name, LENGTH, nnnB, TYPE n, WAVEDATA, int16 binary
        '''
        # Check if builtin
        if name in self.builtins:
            _name = self.builtins[name]
        # Must be user waveform
        elif name in self.user:
            _name = f'USER,{name}'

        # Get header and parse
        try:
            resp = self._sendRecv (f'WVDT? {_name}')
        except SDG2000XNetworkException:
            raise SDG2000XParameterException (f'Waveform not found: {name}')
        
        end = resp.find(b'WAVEDATA')+9
        binary = resp[end:]
        header = resp[5:end].decode ('ascii').split (',')
        keys = [x.strip() for x in header[::2]]
        vals = [x.strip() for x in header[1::2]]
        
        # Create dict
        d = self.toDict (keys, vals)
        d['LENGTH'] = int(d['LENGTH'][:-1])
        d['TYPE'] = int(d['TYPE'])

        # Get rest of data
        if len(binary) < d['LENGTH']:
            binary += self._recv (d['LENGTH'] - len(binary))
        cnt = int (len (binary) / 2)
        d['WAVEDATA'] = list(struct.unpack (f'<{cnt}h', binary))
        return d

    def saveWaveform(self, name, data, ch=1) -> None:
        '''
        Stores int16 data as waveform name
        '''
        if not isinstance (data, list):
            raise SDG2000XParameterException ('Invalid data format')
        # Convert to binary
        print (data)
        binary = struct.pack (f'<{len(data)}h', *data)
        print (binary)
        # Send to siggen
        # Why do we need channel here?
        self._send (f'C{ch}:WVDT WVNM,{name},WAVEDATA,',binary=binary)
        # Append to user waveforms
        self.user.append (name)
        
    def setArbWaveform(self, name, ch=1):
        if name in self.builtins.keys():
            _cmd = f'INDEX,{self.builtins[name][1:]}'
        elif name in self.user:
            _cmd = f'NAME,{name}'
        else:
            raise SDG2000XParameterException (f'Waveform {name} not found')
        self._send (f'C{ch}:ARWV {_cmd}')
    
    def outputEnable(self, ch=1, load='50'):
        if load != '50' and load != 'HZ':
            raise SDG2000XParameterException ('Load must be 50 or HZ')
        self._send (f'C{ch}:OUTP ON,LOAD,{load}')

    def outputDisable(self, ch=1):
        self._send (f'C{ch}:OUTP OFF')
    
if __name__ == '__main__':

    with SDG2000X ('192.168.1.150') as sig:
        print (sig.getID())
        #sig.saveWaveform ('test2', [0x0, 0x7000, 0x7000, 0x0, 0x0])
        #print (sig.getUserWaveforms ())
        sig.outputDisable (ch=1)
        sig.setArbWaveform ('psk')
        sig.outputEnable (ch=1)
