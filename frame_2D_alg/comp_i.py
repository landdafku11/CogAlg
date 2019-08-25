"""
Perform comparison of g or a over predetermined range.
"""

import operator as op

import numpy as np
import numpy.ma as ma

# -----------------------------------------------------------------------------
# Constants

# Define scalers:
SCALER_g = {
    1:0.354801226089485,
    2:0.168952964804517,
    3:0.110256954721035,
}
SCALER_ga = 57.597736326150859

# Define slicing for vectorized rng comparisons:
TRANSLATING_SLICES = {
    1:[
        (Ellipsis, slice(None, -2, None), slice(None, -2, None)),
        (Ellipsis, slice(None, -2, None), slice(1, -1, None)),
        (Ellipsis, slice(None, -2, None), slice(2, None, None)),
        (Ellipsis, slice(1, -1, None), slice(2, None, None)),
        (Ellipsis, slice(2, None, None), slice(2, None, None)),
        (Ellipsis, slice(2, None, None), slice(1, -1, None)),
        (Ellipsis, slice(2, None, None), slice(None, -2, None)),
        (Ellipsis, slice(1, -1, None), slice(None, -2, None)),
    ],
    2:[
        (Ellipsis, slice(None, -4, None), slice(None, -4, None)),
        (Ellipsis, slice(None, -4, None), slice(1, -3, None)),
        (Ellipsis, slice(None, -4, None), slice(2, -2, None)),
        (Ellipsis, slice(None, -4, None), slice(3, -1, None)),
        (Ellipsis, slice(None, -4, None), slice(4, None, None)),
        (Ellipsis, slice(1, -3, None), slice(4, None, None)),
        (Ellipsis, slice(2, -2, None), slice(4, None, None)),
        (Ellipsis, slice(3, -1, None), slice(4, None, None)),
        (Ellipsis, slice(4, None, None), slice(4, None, None)),
        (Ellipsis, slice(4, None, None), slice(3, -1, None)),
        (Ellipsis, slice(4, None, None), slice(2, -2, None)),
        (Ellipsis, slice(4, None, None), slice(1, -3, None)),
        (Ellipsis, slice(4, None, None), slice(None, -4, None)),
        (Ellipsis, slice(3, -1, None), slice(None, -4, None)),
        (Ellipsis, slice(2, -2, None), slice(None, -4, None)),
        (Ellipsis, slice(1, -3, None), slice(None, -4, None)),
    ],
    3:[
        (Ellipsis, slice(None, -6, None), slice(None, -6, None)),
        (Ellipsis, slice(None, -6, None), slice(1, -5, None)),
        (Ellipsis, slice(None, -6, None), slice(2, -4, None)),
        (Ellipsis, slice(None, -6, None), slice(3, -3, None)),
        (Ellipsis, slice(None, -6, None), slice(4, -2, None)),
        (Ellipsis, slice(None, -6, None), slice(5, -1, None)),
        (Ellipsis, slice(None, -6, None), slice(6, None, None)),
        (Ellipsis, slice(1, -5, None), slice(6, None, None)),
        (Ellipsis, slice(2, -4, None), slice(6, None, None)),
        (Ellipsis, slice(3, -3, None), slice(6, None, None)),
        (Ellipsis, slice(4, -2, None), slice(6, None, None)),
        (Ellipsis, slice(5, -1, None), slice(6, None, None)),
        (Ellipsis, slice(6, None, None), slice(6, None, None)),
        (Ellipsis, slice(6, None, None), slice(5, -1, None)),
        (Ellipsis, slice(6, None, None), slice(4, -2, None)),
        (Ellipsis, slice(6, None, None), slice(3, -3, None)),
        (Ellipsis, slice(6, None, None), slice(2, -4, None)),
        (Ellipsis, slice(6, None, None), slice(1, -5, None)),
        (Ellipsis, slice(6, None, None), slice(None, -6, None)),
        (Ellipsis, slice(5, -1, None), slice(None, -6, None)),
        (Ellipsis, slice(4, -2, None), slice(None, -6, None)),
        (Ellipsis, slice(3, -3, None), slice(None, -6, None)),
        (Ellipsis, slice(2, -4, None), slice(None, -6, None)),
        (Ellipsis, slice(1, -5, None), slice(None, -6, None)),
    ],
}

# Define coefficients for decomposing d into dy and dx:
Y_COEFFS = {
    1:np.array([-0.5, -1. , -0.5,  0. ,  0.5,  1. ,  0.5,  0. ]),
    2:np.array([-0.25, -0.4 , -0.5 , -0.4 , -0.25, -0.2 ,  0.  ,  0.2 ,  0.25,
                0.4 ,  0.5 ,  0.4 ,  0.25,  0.2 ,  0.  , -0.2 ]),
    3:np.array([-0.16666667, -0.23076923, -0.3       , -0.33333333, -0.3       ,
                -0.23076923, -0.16666667, -0.15384615, -0.1       ,  0.        ,
                0.1       ,  0.15384615,  0.16666667,  0.23076923,  0.3       ,
                0.33333333,  0.3       ,  0.23076923,  0.16666667,  0.15384615,
                0.1       ,  0.        , -0.1       , -0.15384615]),
}
X_COEFFS = {
    1:np.array([-0.5,  0. ,  0.5,  1. ,  0.5,  0. , -0.5, -1. ]),
    2:np.array([-0.25, -0.2 ,  0.  ,  0.2 ,  0.25,  0.4 ,  0.5 ,  0.4 ,  0.25,
                0.2 ,  0.  , -0.2 , -0.25, -0.4 , -0.5 , -0.4 ]),
    3:np.array([-0.16666667, -0.15384615, -0.1       ,  0.        ,  0.1       ,
                 0.15384615,  0.16666667,  0.23076923,  0.3       ,  0.33333333,
                0.3       ,  0.23076923,  0.16666667,  0.15384615,  0.1       ,
                0.        , -0.1       , -0.15384615, -0.16666667, -0.23076923,
                -0.3       , -0.33333333, -0.3       , -0.23076923]),
}

# -----------------------------------------------------------------------------
# Functions

def comp_i(blob_derts, rng, iG, fa):
    """
    Compare g or a over predetermined range.
    Parameters
    ----------
    blob_derts : MaskedArray
        Contain the arrays: g, m, dy, dx.
    rng : int
        Determine translation between comparands.
    Return
    ------
    out : MaskedArray
        The array that contain result from comparison.
    """

    assert isinstance(derts, ma.MaskedArray)

    if fa:
        return comp_a(blob_derts, rng)
    else:
        return comp_g(select_derts(blob_derts, iG), rng)

def select_derts(blob_derts, iG):
    """
    Select_g to compare
    """
    g = blob_derts[iG]
    if iG == 0: # Accumulated m, dy, dx:
        m, dy, dx = blob_derts[2:5]
    else: # Initialized m, dy, dx:
        m, dy, dx = ma.zeros(g.shape)

    return g, m, dy, dx

def comp_g(derts, rng):
    """
    Compare g over predetermined range.
    """
    # Unpack derts:
    g, m, dy, dx = derts

    # Compare gs:
    d = translated_operation(g, rng, op.sub)
    comp_field = central_slice(rng)

    # Decompose and add to corresponding dy and dx:
    dy[comp_field] += (d * Y_COEFFS[rng]).sum(axis=-1)
    dx[comp_field] += (d * X_COEFFS[rng]).sum(axis=-1)

    # Compute ms:
    m[comp_field] += translated_operation(g, rng, ma.minimum).sum(axis=-1)

    # Compute gg:
    gg = ma.hypot(dy, dx) * SCALER_g[rng]

    return ma.stack((g, gg, m, dy, dx), axis=0) # ma.stack() for extra array dimension.


def comp_a(gblob_derts, rng):
    """
    Compute and compare a over predetermined range.
    """
    # Unpack derts:
    g, gg, m, dy, dx = gblob_derts

    # Compute angles:
    a = ma.stack((dy, dx), axis=0) / g

    # Compute angle differences:
    da = translated_operation(a, rng, angle_diff)
    comp_field = central_slice(rng)

    # Decompose and add to corresponding day and dax:
    day[comp_field] += (da * Y_COEFFS[rng]).mean(axis=-1)
    dax[comp_field] += (da * X_COEFFS[rng]).mean(axis=-1)

    # Compute ga:
    ga = ma.hypot(
        ma.arctan2(*day),
        ma.arctan2(*dax)
    )[np.newaxis, ...] * SCALER_ga

    return ma.concatenate( # Concatenate on the first dimension.
        (
            ma.stack((g, gg, m, dy, dx), axis=0),
            ga, day, dax,
        ),
        axis=0,
    )

# -----------------------------------------------------------------------------
# Utility functions

def central_slice(i):
    """Return central slice objects (last 2 dimensions)."""
    if i < 1:
        return ..., slice(None), slice(None)
    return ..., slice(i, -i), slice(i, -i)


def rim_mask(shape, i):
    """
    Return 2D array mask where outer pad (pad width=i) is True,
    the rest is False.
    """
    out = np.ones(shape, dtype=bool)
    out[central_slice(i)] = False
    return out


def translated_operation(a, rng, operator):
    """
    Return an array of corresponding results from operations between
    translated slices and central slice of an array.
    Parameters
    ----------
    a : ndarray
        Input array.
    rng : int
        Range of translations.
    operator : function
        Binary operator of which the result between central
        and translated slices are returned.
    Return
    ------
    out : ndarray
        Array of results where additional dimension correspondent
        to each translated slice.
    """
    out = ma.masked_array([*map(lambda slices:
                                    operator(a[slices],
                                             a[central_slice(rng)]),
                                TRANSLATING_SLICES[rng])])

    # Rearrange axes:
    for dim in range(out.ndim - 1):
        out = out.swapaxes(dim, dim+1)

    return out


def angle_diff(a2, a1):
    """
    Return the vector, of which angle is the angle between a2 and a1.
    Can be applied to arrays.
    Note: This only works for 2D vectors.
    """
    # Extend a1 vector(s) into basis/bases:
    y, x = a1
    bases = [(x, -y), (y, x)]
    transform_mat = ma.array(bases)

    # Apply transformation:
    da = (transform_mat * a2).sum(axis=1)

    return da

# ----------------------------------------------------------------------
# -----------------------------------------------------------------------------