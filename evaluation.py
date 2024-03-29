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
parser.add_argument('--users', nargs='+', help='Evaluate a selection of users.')
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
    sys.argv[1:] if len(sys.argv) > 1 else ['--users', 'll', 'lw', 'mh'])

files = glob.glob(os.path.join('data', '*.csv'))

table = csv2np.load(files)

if args.nouser:
    table = table[table['user'] != args.nouser]

if args.users:
    pass

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
    # sort_index = np.argsort(data['line_angle'])
    # data[sort_index, :]
    data['filter_radius'] = data['filter_radius'].astype(np.float64) / data['artifact_size'].astype(np.float64)
    figures.boxplot(data)
    # figures.boxplot(data[(data['filter_noise'] == 0) & (data['line_angle'] == np.deg2rad(1))])
    # figures.boxplot(data[(data['filter_noise'] == 0) & (data['artifact_size'] == 8)])

if args.user:
    table = table[table['user'] == args.user]

if args.stairs:
    data = table[table['is_reference'] == False]
    figures.stairs(data, legend=True)

if args.thresholds:
    data = table[table['is_reference'] == False]
    figures.thresholds(data)

plt.show()
