#!/usr/bin/env python
from __future__ import print_function

import argparse
import math
import sys
import pyBigWig

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-t', help='Percentage of top bins to evaluate', default=10, type=int)
    parser.add_argument('-p', help='Top bins max percentage', default=30, type=int)
    parser.add_argument('-b', help='Bin size', default=25, type=int)
    parser.add_argument('input', help='Input bigWig file')
    options = parser.parse_args()

    bw = pyBigWig.open(options.input)
    if not bw.isBigWig():
        print('%s is not a bigWig' % options.input)
        sys.exit(2)
    percentageTopBins = check_top_bins_percentage(options.b, options.t, bw)

    if percentageTopBins < options.p:
        print('Top %i%% bins under %i%%: %f%%' % (options.t, options.p, percentageTopBins))
        sys.exit(1)

    print('Top %i%% bins is over %i%%: %f%%' % (options.t, options.p, percentageTopBins))
    sys.exit(0)


def get_top_bins_percentage(bin_size, top_bins_to_check, filepath):
    bw = pyBigWig.open(filepath)

    if not bw.isBigWig():
        raise Exception('%s is not a bigWig' % filepath)

    chroms = bw.chroms()

    bins = []
    for chrom, length in chroms.items()[0:4]:
        values = bw.values(chrom, 1, length)
        currentBins = make_bins(bin_size, values)
        bins.extend(currentBins)
    bins.sort()

    nbTopBins = len(bins) * top_bins_to_check / 100

    sumTopBins    = sum(bins[len(bins) - nbTopBins:])
    sumBottomBins = sum(bins[:len(bins) - nbTopBins])
    sumTotalBins = sumTopBins + sumBottomBins

    percentageTopBins = sumTopBins / sumTotalBins

    return percentageTopBins * 100

def make_bins(bin_size, values):
    bins = []
    currentBin = 0.0
    remainingValues = bin_size

    for value in values:
        if math.isnan(value):
            continue

        currentBin += value
        remainingValues -= 1

        if remainingValues == 0:
            bins.append(currentBin)
            currentBin = 0.0
            remainingValues = bin_size

    return bins



if __name__ == '__main__':
    main()
