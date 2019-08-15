import argparse
import glob
import matplotlib.colors
import matplotlib.pyplot as plt
import numpy as np
import os
import sys
import csv2np
import figures
import statistics
import scipy.stats

parser = argparse.ArgumentParser(description='Evaluate study data.')
parser.add_argument(
    '--outlierremoval',
    help='Remove statistical outliers before performing any analysis.',
    action="store_true")
parser.add_argument('--user', help='Evaluate a single user.')
parser.add_argument('--nouser', help='Remove a single user.')
parser.add_argument('--stairs',
                    help='Show the staircase plot.',
                    action="store_true")
parser.add_argument('--thresholds',
                    help='Show the threshold plot.',
                    action="store_true")
parser.add_argument('--boxplot', help='Show the boxplot.', action="store_true")
parser.add_argument('--qqplot', help='Show the QQ-plot.', action="store_true")

args = parser.parse_args(
    sys.argv[1:] if len(sys.argv) > 1 else ['--boxplot'])

files = glob.glob(os.path.join('data', '*.csv'))

table = csv2np.load(files)

if args.nouser:
    table = table[table['user'] != args.nouser]

if args.qqplot:
    data = table[table['is_reference'] == False]
    labels, radii, outlier = statistics.thresholds(data)
    if args.outlierremoval:
        labels = labels[~outlier]
        radii = radii[~outlier]
    labels = figures.relabel(labels)
    fig = plt.figure('QQ-Plots')
    for i, label in enumerate(np.unique(labels)):
        r = radii[labels == label]
        statistic, pvalue = scipy.stats.shapiro(r)
        ax = fig.add_subplot(4, 5, i + 1)
        scipy.stats.probplot(r, plot=ax)
        ax.title.set_text(f'{label} (p:{np.round(pvalue, 2)})')

if args.boxplot:
    data = table[table['is_reference'] == False]
    figures.boxplot(data)

if args.user:
    table = table[table['user'] == args.user]

if args.stairs:
    data = table[table['is_reference'] == False]
    figures.stairs(data, legend=True)

if args.thresholds:
    data = table[table['is_reference'] == False]
    figures.thresholds(data)

plt.show()
