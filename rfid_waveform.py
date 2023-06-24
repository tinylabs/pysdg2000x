#!/bin/env python3
#
# Generate arbitrary RFID waveform
#
# Tiny Labs Inc
# 2023
#
from pysdg2000x import *
import numpy as np
import matplotlib.pyplot as plt
import struct
import time
class RFIDWaveform:

    def __init__(self, name, pts, data=None):
        ''' pts = points per sinewave '''
        self.name = name
        self.pts = pts
        self.ts = 2*np.pi / pts
        self.data = data
        self.amp = None

    # TODO: Add PSK phase shift support
    def generate (self, modulation=0.5, scale=2**15, psk=False):
        ''' Generate RF data '''
        modulation = 1 - modulation
        if self.data:
            self.time = np.arange(0, self.ts * self.pts * len (self.data), self.ts)
            amp = []
            time = np.arange (0, 2*np.pi, self.ts)

            # Loop through data
            for n, bit in enumerate (self.data):
                # Set modulation
                mod = modulation if bit else 1
                
                # Generate amplitude
                amp += [x * mod * scale for x in np.sin(time)]
            self.amp = amp
            if len (self.time) != len (self.amp):
                self.time = self.time[:-1]

    def int16 (self):
        quant = [int (x) for x in self.amp]
        quant = [32767 if x == 32768 else x for x in quant]
        return quant

    def plot (self):
        plt.plot (self.time, self.amp)
        plt.title (self.name, color='b')
        plt.xlabel('Time'+ r'$\rightarrow$')
        plt.ylabel('Amp(time) '+ r'$\rightarrow$')
        plt.grid ()
        plt.axhline(y=0, color='k')
        plt.axvline(x=0, color='k')
        plt.show ()
        
if __name__ == '__main__':

    psk = RFIDWaveform ('psk', 200, [1, 0, 1, 0, 1, 0, 0, 1, 0, 1, 1, 0, 1, 0, 1, 0])
    psk.generate (modulation=0.6, psk=True)
    psk.plot ()
    data = psk.int16()
    '''
    with SDG2000X ('192.168.1.150') as sig:
        print (sig.getID())
        sig.saveWaveform ('psk', data)
        sig.setArbWaveform ('psk')
    '''
