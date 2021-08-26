#!/usr/bin/env python
# 
# -- from http://stackoverflow.com/questions/16330831/most-efficient-way-to-find-mode-in-numpy-array
# 
# Usage: 
#   from almacosmos_get_fits_image_pixel_mode.py import mode

import numpy

def mode(ndarray,axis=0):
    # -- from http://stackoverflow.com/questions/16330831/most-efficient-way-to-find-mode-in-numpy-array
    if ndarray.size == 1:
        return (ndarray[0],1)
    elif ndarray.size == 0:
        raise Exception('Attempted to find mode on an empty array!')
    try:
        axis = [i for i in range(ndarray.ndim)][axis]
    except IndexError:
        raise Exception('Axis %i out of range for array with %i dimension(s)' % (axis,ndarray.ndim))
    ndarray2 = ndarray[~numpy.isnan(ndarray)]
    srt = numpy.sort(ndarray2,axis=axis)
    dif = numpy.diff(srt,axis=axis)
    shape = [i for i in dif.shape]
    shape[axis] += 2
    indices = numpy.indices(shape)[axis]
    index = tuple([slice(None) if i != axis else slice(1,-1) for i in range(dif.ndim)])
    indices[index][dif == 0] = 0
    indices.sort(axis=axis)
    bins = numpy.diff(indices,axis=axis)
    location = numpy.argmax(bins,axis=axis)
    mesh = numpy.indices(bins.shape)
    index = tuple([slice(None) if i != axis else 0 for i in range(dif.ndim)])
    index = [mesh[i][index].ravel() if i != axis else location.ravel() for i in range(bins.ndim)]
    counts = bins[tuple(index)].reshape(location.shape)
    index[axis] = indices[tuple(index)]
    modals = srt[tuple(index)].reshape(location.shape)
    return (modals, counts)

