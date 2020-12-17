#!/usr/bin/env python

import argparse
import csv
import matplotlib.pyplot as plt
import pandas as pd

"""
Parse arguments
"""
def parse_arguments():
    parser = argparse.ArgumentParser(description='Draw graphs of income')
    parser.add_argument('-g', '--group',
                        help='grouping unit, possible values: day, week, month (default), year')
    parser.add_argument('-p', '--payee',
                        help='draw stacked charts for payees')
    parser.add_argument('source', nargs='+', type=argparse.FileType('r'))
    return parser.parse_args()

"""
Main part
"""
if __name__ == '__main__':

    args = parse_arguments()

    if args.source:
        for f in args.source:
            try:
                data.extend(read_file(f))
            except IOError as e:
                sys.stderr.write('Cannot open file: %s\n' % str(e))
    else:
        sys.stderr.write('Usage: %s [options] <source.csv>\n' % sys.argv[0])
        sys.exit(1)
