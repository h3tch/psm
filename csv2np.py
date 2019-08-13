import numpy as np


def merge_structured_arrays(*arrays):
    columns = [t[0] for t in arrays[0].dtype.descr]
    types = [t[1] for t in arrays[0].dtype.descr]

    for t in [a.dtype.descr for a in arrays[1:]]:
        for i, v in enumerate(t):
            types[i] = max(types[i], v[1])

    dtype = np.dtype([(name, desc) for name, desc in zip(columns, types)])

    array_out = np.empty((sum(len(a) for a in arrays), ), dtype=dtype)
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