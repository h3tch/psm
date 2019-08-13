import numpy as np


def merge_structured_arrays(*arrays):
    array_out = np.empty((sum(len(a) for a in arrays), ),
                         dtype=arrays[0].dtype)
    i = 0
    for a in arrays:
        array_out[i:(i + a.shape[0])] = a
        i += a.shape[0]
    return array_out


def load(files):
    tables = [
        np.genfromtxt(f,
                      delimiter=',',
                      names=True,
                      dtype=None,
                      encoding='utf-8') for f in files
    ]

    return merge_structured_arrays(*tables)