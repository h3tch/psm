import argparse
import glob
import matplotlib.colors
import matplotlib.pyplot as plt
import numpy as np
import os
import sys


parser = argparse.ArgumentParser(description='Evaluate study data.')

parser.add_argument('--user', help='Evaluate a single user.')
parser.add_argument('--stairs', help='Show the staircase plot.', action="store_true")
parser.add_argument('--thresholds', help='Show the threshold plot.', action="store_true")

if len(sys.argv) > 1:
    args = parser.parse_args(sys.argv[1:])
else:
    args = parser.parse_args(['--threshold', '--stairs'])

user_filter = '*' if args.user is None else args.user
files = glob.glob(os.path.join('data', f'{user_filter}.csv'))

tables = [np.genfromtxt(f, delimiter=',', names=True, dtype=None, encoding='utf-8') for f in files]
table = np.concatenate(tables)

if args.stairs:
    data = table[table['is_reference'] == False]

    user = data['user']
    unique_user = np.unique(data['user'])
    label = data['label']
    unique_label = np.unique(label)
    radius = data['intensity'] * data['filter_radius']

    fig = plt.figure("Stairs")
    ax = plt.axes()
    for user_index, user_name in enumerate(unique_user):
        user_color = (user_index + 1) / len(unique_user)
        for label_index, label_name in enumerate(unique_label):
            label_color = (label_index + 1) / len(unique_label)
            color = matplotlib.colors.hsv_to_rgb((label_color, user_color, 0.8))
            ax.plot(radius[(user == user_name) & (label == label_name)], color=color)

if args.thresholds:
    data = table[table['is_reference'] == False]

    user = data['user']
    unique_user = np.unique(data['user'])
    label = data['label']
    unique_label = np.unique(label)
    radius = data['intensity'] * data['filter_radius']
    trial_id = data['questTrialId']

    fig = plt.figure("Thresholds")
    ax = plt.axes()
    for user_index, user_name in enumerate(unique_user):
        user_color = (user_index + 1) / len(unique_user)
        for label_index, label_name in enumerate(unique_label):
            r = radius[(user == user_name) & (label == label_name)]
            label_color = (label_index + 1) / len(unique_label)
            color = matplotlib.colors.hsv_to_rgb((label_color, user_color, 0.8))
            ax.plot(r[-1], 'o', color=color)

plt.show()
