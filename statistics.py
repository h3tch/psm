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

    labels = np.array(labels)
    radii = np.array(radii)
    outlier = np.zeros(radii.shape, np.bool)

    quantiles = [np.quantile(radii[labels == label], [0.25, 0.75])
                 for label in unique_label]
    iqr = [a[1] - a[0] for a in quantiles]
    bounds = np.array([(a[0] - 1.5 * i, a[1] + 1.5 * i) for a, i in zip(quantiles, iqr)])

    for label, th in zip(unique_label, bounds):
        r = radii[labels == label]
        outlier[labels == label] = (r < th[0]) | (th[1] < r)

    return labels, radii, outlier
