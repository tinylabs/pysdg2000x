#!/bin/env python3
#
#  Graph waveform from siglent sdg2000x siggen
#

from pysdg2000x import *
import matplotlib.pyplot as plt
import argparse
import sys

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument ('-n', '--name')
    parser.add_argument ('-l', '--list', action='store_true')
    args = parser.parse_args ()

    if not args.name and not args.list:
        parser.print_help ()
        sys.exit (-1)
        
    with SDG2000X ('192.168.1.150') as sig:
        if args.name:
            resp = sig.getWaveform (args.name)
            waveform = resp['WAVEDATA']

            # Create plot
            plt.plot (waveform)
            plt.show ()
        elif args.list:
            print (sig.getWaveformList ())
