import numpy as np
import matplotlib.colors
import matplotlib.pyplot as plt


def relabel(labels):
    trim = '-samples1'
    labels = [
        l[:-len(trim)] if l.endswith(trim) else l for l in labels
    ]
    labels = [
        l.replace('artifact', 'A').replace('angle', 'α').replace('noise', 'λ').replace('speed', 'ν')
        for l in labels
    ]
    return np.array(labels)


def stairs(data, legend=False):
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
            color = matplotlib.colors.hsv_to_rgb(
                (label_color, user_color, 0.8))
            ax.plot(radius[(user == user_name) & (label == label_name)],
                    color=color,
                    label=label_name)
    if legend:
        ax.legend()

    return fig


def thresholds(data):
    user = data['user']
    unique_user = np.unique(data['user'])
    label = data['label']
    unique_label = np.unique(label)
    radius = data['intensity'] * data['filter_radius']

    fig = plt.figure("Thresholds")
    ax = plt.axes()
    for user_index, user_name in enumerate(unique_user):
        user_color = (user_index + 1) / len(unique_user)
        for label_index, label_name in enumerate(unique_label):
            r = radius[(user == user_name) & (label == label_name)]
            label_color = (label_index + 1) / len(unique_label)
            color = matplotlib.colors.hsv_to_rgb(
                (label_color, user_color, 0.8))
            ax.plot(label_index, r[-1], 'o', color=color)

    plt.xticks(range(len(unique_label)),
               unique_label,
               rotation=20,
               horizontalalignment='right')
    plt.subplots_adjust(bottom=0.2)
    return fig


def boxplot(data, show_points=True):
    user = data['user']
    unique_user = np.unique(data['user'])
    label = data['label']
    unique_label = np.unique(label)
    radius = data['intensity'] * data['filter_radius']

    fig = plt.figure("Boxplot")
    ax = plt.axes()

    radii = [[
        radius[(user == user_name) & (label == label_name)]
        for user_name in unique_user
    ] for label_name in unique_label]
    radii = [[r[-1] for r in radius if len(r) > 0] for radius in radii]

    if show_points:
        colors = [[
            matplotlib.colors.hsv_to_rgb(
                (l / len(unique_label), u / len(unique_user), 0.8))
            for u in range(1, len(unique_user) + 1)
        ] for l in range(1, len(unique_label) + 1)]

        for i, (radius, color) in enumerate(zip(radii, colors)):
            for r, c, in zip(radius, color):
                ax.plot(i + 1, r, 'o', color=c)

    unique_label = relabel(unique_label)

    ax.boxplot(radii, labels=unique_label)
    plt.xticks(range(1,
                     len(unique_label) + 1),
               unique_label,
               rotation=20,
               horizontalalignment='center')
    plt.subplots_adjust(top=0.97, bottom=0.15, left=0.06, right=0.94)
    return fig