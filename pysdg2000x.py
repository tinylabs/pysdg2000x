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

        # Store builtins
        self.builtins = self.getBuiltinWaveforms ()
        
    def __enter__(self):
        return self

    def __exit__ (self, exc_type, exc_value, traceback):
        self.cleanup ()

    def cleanup (self):
        if self.rSocket != None:
            self.rSocket.close ()
            self.rSocket = None

    def _send(self, cmd):
        cmd += '\n'
        if self.rSocket is None:
            raise SDG2000XNetworkException ('Network connection is closed')
        try:
            cmd = cmd.encode('ascii')
            self.rSocket.sendall (cmd)
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

    def getWaveform(self, name) -> dict:
        '''
        WVDT? Mn or WVDT? USER,name
        WVDT POS,storage, WVNM, name, LENGTH, nnnB, TYPE n, WAVEDATA, int16 binary
        '''
        # Check if builtin
        if name in self.builtins:
            name = self.builtins[name]
        # Must be user waveform
        else:
            name = f'USER,{name}'

        # Get header and parse
        resp = self._sendRecv (f'WVDT? {name}')
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

    def outputEnable(self, channel=1):
        pass
    
if __name__ == '__main__':

    with SDG2000X ('192.168.1.150') as sig:
        print (sig.getID())
        print (sig.getBuiltinWaveforms())
        print (sig.getWaveform ('demo1_16k'))
