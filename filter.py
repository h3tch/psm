import numpy as np


def thresholds(data):
    user = data['user']
    unique_user = np.unique(data['user'])
    label = data['label']
    unique_label = np.unique(label)
    radius = data['intensity'] * data['filter_radius']

    labels = []
    radii = []

    for user_name in unique_user:
        for label_name in unique_label:
            r = radius[(user == user_name) & (label == label_name)]
            labels.append(label_name)
            radii.append(r[-1])

    return np.array(labels), np.array(radii)
