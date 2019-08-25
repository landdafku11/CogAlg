import operator as op
'''
    intra_blob() evaluates for recursive frame_blobs() and comp_P() within each blob.
    combined frame_blobs and intra_blob form a 2D version of 1st-level algorithm.
    to be added:

    inter_sub_blob() will compare sub_blobs of same range and derivation within higher-level blob, bottom-up ) top-down:
    inter_level() will compare between blob levels, where lower composition level is integrated by inter_sub_blob
    match between levels' edges may form composite blob, axis comp if sub_blobs within blob margin?
    inter_blob() will be 2nd level 2D alg: a prototype for recursive meta-level alg

    Each intra_comp() call from intra_blob() adds a layer of sub_blobs, new dert to derts and Layer to Layers, in each blob.
    intra_comp also sends feedback to root_fork | root_blob, then to root_blob.root_blob, etc.
    Blob structure:
    
    root_fork, # = root_blob['fork_'][iG]: reference for feedback of blob' Dert params and sub_blob_, up to frame
    
    Dert = G, Gg, M, Dx, Dy, Ga, Dax, Day, L, Ly,  
    # extended per fork: iG + gDert in g_fork, + aDert in a_fork, L, Ly are defined by Gg | Ga sign
    
    iG,   # fork type: index of compared ig in dert and criterion iG in Dert: 0 if G | 1 if Gg | 5 if Ga 
    sign, # of iG
    rng,  # comp range, in each Dert
    map,  # boolean map of blob to compute overlap
    box,  # boundary box: y0, yn, x0, xn; selective map, box in lower Layers
    dert__, # comp_i inputs
       
    segment_[ seg_params, Py_ [(P_params, dert_)]],  
    # dert: g, gg, m, dy, dx, ga, day, dax; no m_angle: mag!=val, ~brightness
    # references down blob formation tree, accumulating Dert, in vertical (horizontal) order
    
    fork_ # multiple derivation trees per blob: 0-1 in g_blobs, 0-3 in a_blobs, next sub_blob_ is in layer_[0]:
        [
         layer_ [(Dert, sub_blob_)]  # alternating g(even) | a(odd) layers across derivation tree, seq access
        ]
        # deeper layers are mixed-fork with nested sub_blob_, Dert params are for layer-parallel comp_blob        
    '''

from collections import deque, defaultdict
from functools import reduce
from itertools import groupby, starmap

import numpy as np
import numpy.ma as ma

from comp_i import comp_i
from utils import pairwise, flatten

# -----------------------------------------------------------------------------
# Filters

ave = 20   # average g, reflects blob definition cost, higher for smaller positive blobs, no intra_cluster for neg blobs
kwidth = 3   # kernel width
if kwidth != 2:  # ave is an opportunity cost per comp:
    ave *= (kwidth ** 2 - 1) / 2  # ave *= ncomp_per_kernel / 2 (base ave is for ncomp = 2 in 2x2)
    # not needed?

ave_blob = 10000       # fixed cost of intra_cluster per blob, accumulated in deeper layers
rave = 20              # fixed root_blob / blob cost ratio: add sub_blobs, Levels+=Level, derts+=dert
ave_n_sub_blobs = 10   # determines rave, adjusted per intra_cluster
ave_intra_blob = 1000  # cost of default eval_sub_blob_ per intra_blob

''' These filters are accumulated for evaluated intra_cluster:
    Ave += ave: cost per next-layer dert, fixed comp grain: pixel
    ave_blob *= rave: cost per next root blob, variable len sub_blob_
    represented per fork if tree reorder, else redefined at each access?
'''

# -----------------------------------------------------------------------------
# Functions, under revision:

def form_P__(x0, y0, dert__, Ave, fa):
    """Form Ps across the whole dert array."""

    g__ = dert__[0, :, :]  # g sign determines clustering:

    # Clustering:
    s_x_L__ = [*map(
        lambda g_: # Each line.
            [(sign, next(group)[0], len(list(group)) + 1) # (s, x, L)
             for sign, group in groupby(enumerate(g_ > Ave),
                                        op.itemgetter(1)) # (x, s): return s.
             if sign is not ma.masked], # Ignore gaps.
        g__,  # line, blob slice
    )]

    # Accumulation:
    P__ = [[dict(sign=s,
                 x0=x+x0,
                 G=dert_[0, x : x+L].sum() - Ave * L,
                 M=0 if fa else dert_[1, x : x+L].sum(),
                 Dy=np.array(dert_[1:3, x : x+L].sum(axis=-1)) if fa
                 else dert_[2, x : x+L].sum(),
                 Dx=np.array(dert_[3:, x : x+L].sum(axis=-1)) if fa
                 else dert_[3, x : x+L].sum(),
                 L=L,
                 dert_=dert_[:, x : x+L].T,
                 root_=[],
                 fork_=[],
                 y=y)
            for s, x, L in s_x_L_]
           for dert_, (y, s_x_L_) in zip(dert__.swapaxes(0, 1),
                                         enumerate(s_x_L__, start=y0))]
    return P__


def scan_P__(P__):
    """ detect forks and roots per P"""

    for _P_, P_ in pairwise(P__): # Iterate through pairs of lines.
        _P_, P_ = iter(_P_), iter(P_) # Convert to iterators.
        try:
            _P, P = next(_P_), next(P_) # First pair to check.
        except StopIteration: # No more fork-root pair.
            continue # To next pair of _P_, P_.
        while True:
            left, olp = comp_edge(_P, P) # Check for 4 different cases.
            if olp and _P['sign'] == P['sign']:
                _P['root_'].append(P)
                P['fork_'].append(_P)
            try:
                _P, P = (next(_P_), P_) if left else (_P, next(P_))
            except StopIteration: # No more fork-root pair.
                break # To next pair of _P_, P_.

    return [*flatten(P__)] # Flatten P__ before return.


def comp_edge(_P, P): # Used in scan_P_().
    """
    Check for end-point relative position and overlap.
    Used in scan_P__().
    """
    _x0 = _P['x0']
    _xn = _x0 + _P['L']
    x0 = P['x0']
    xn = x0 + P['L']

    if _xn < xn: # End-point relative position
        return True, x0 < _xn
    else:
        return False, _x0 < xn


def form_segment_(P_):
    """Form segments of vertically contiguous Ps."""

    seg_pars = 'y0', 'G', 'M', 'Dy', 'Dx', 'L', 'Ly', 'Py_', 'root_', 'fork_'

    # Get a list of all segment's first P:
    P0_ = [*filter(lambda P: (len(P['fork_']) != 1
                            or len(P['fork_'][0]['root_']) != 1),
                   P_)]

    # Form segments:
    seg_ = [dict(zip(seg_pars, # segment's params as keys
                     [Py_[0].pop('y'),] # y0
                     # Accumulate params:
                     + [*map(sum,
                             zip(*map(op.itemgetter('G',
                                                    'M',
                                                    'Dy',
                                                    'Dx',
                                                    'L'),
                                      Py_)))]
                     + [len(Py_)]  # Ly
                     + [Py_]
                     + [Py_[-1]['root_']]  # root_
                     + [Py_[0]['fork_']])) # fork_
            # cluster_vertical(P): traverse segment from first P:
            for Py_ in map(cluster_vertical, P0_)]

    for seg in seg_:
        seg['Py_'][0]['seg'] = seg['Py_'][-1]['seg'] = seg

    for seg in seg_:
        seg.update(root_=[*map(lambda P: P['seg'], seg['root_'])],
                   fork_=[*map(lambda P: P['seg'], seg['fork_'])])

    for seg in seg_:
        for i, ref in ((0, 'fork_'), (-1, 'root_')):
            seg['Py_'][i].pop('seg')
            seg['Py_'][i].pop(ref)

    return seg_


def cluster_vertical(P): # Used in form_segment_().
    """
    Cluster P vertically, stop at the end of segment.
    Used in form_segment_().
    """

    if len(P['root_']) == 1 and len(P['root_'][0]['fork_']) == 1:
        P['root_'][0].pop('y')
        root = P.pop('root_')[0] # Only 1 root.
        root.pop('fork_') # Only 1 fork.
        return [P] + cluster_vertical(root)
    else:
        return [P]


def form_blob_(seg_, root_blob, dert___, rng, fork_type):
    encountered = []
    blob_ = []
    for seg in seg_:
        if seg in encountered:
            continue

        q = deque([seg])
        encountered.append(seg)

        s = seg['Py_'][0]['sign']
        G, M, Dy, Dx, L, Ly, blob_seg_ = 0, 0, 0, 0, 0, 0, []
        x0, xn = 9999999, 0
        while q:
            blob_seg = q.popleft()
            for ext_seg in blob_seg['fork_'] + blob_seg['root_']:
                if ext_seg not in encountered:
                    encountered.append(ext_seg)
            G += blob_seg['G']
            M += blob_seg['M']
            Dy += blob_seg['Dy']
            Dx += blob_seg['Dx']
            L += blob_seg['L']
            Ly += blob_seg['Ly']
            blob_seg_.append(blob_seg)

            x0 = min(x0, min(map(op.itemgetter('x0'), blob_seg['Py_'])))
            xn = max(xn, max(map(lambda P: P['x0']+P['L'], blob_seg['Py_'])))

        y0 = min(map(op.itemgetter('y0'), blob_seg_))
        yn = max(map(lambda segment: segment['y0']+segment['Ly'], blob_seg_))

        mask = np.ones((yn - y0, xn - x0), dtype=bool)
        for blob_seg in blob_seg_:
            for y, P in enumerate(blob_seg['Py_'], start=blob_seg['y0']):
                x_start = P['x0'] - x0
                x_stop = x_start + P['L']
                mask[y - y0, x_start:x_stop] = False

        # Form blob:
        blob = dict(
            Dert=dict(G=G, M=M, Dy=Dy, Dx=Dx, L=L, Ly=Ly),
            sign=s,
            box=(y0, yn, x0, xn),  # boundary box
            slices=(Ellipsis, slice(y0, yn), slice(x0, xn)),
            seg_=blob_seg_,
            rng = rng,
            dert___ = dert___,
            mask=mask,
            root_blob = root_blob,
            hDerts = np.concatenate(
                (
                    [[*root_blob['Dert'].values()]],
                    root_blob['hDerts'],
                ),
                axis=0
            ),
            forks=defaultdict(list),
            fork_type=fork_type,
        )

        feedback(blob)

        blob_.append(blob)

    return blob_


def feedback(blob, sub_fork_type=None): # Add each Dert param to corresponding param of recursively higher root_blob.

    root_blob = blob['root_blob']
    if root_blob is None: # Stop recursion.
        return
    fork_type = blob['fork_type']

    # blob Layers is deeper than root_blob Layers:
    len_sub_layers = max(0, 0, *map(len, blob['forks'].values()))
    while len(root_blob['forks'][fork_type]) <= len_sub_layers:
        root_blob['forks'][fork_type].append((0, 0, 0, 0, 0, 0, []))

    # First layer accumulation:
    G, M, Dy, Dx, L, Ly = blob['Dert'].values()
    Gr, Mr, Dyr, Dxr, Lr, Lyr, sub_blob_ = root_blob['forks'][fork_type][0]
    root_blob['forks'][fork_type][0] = (
        Gr + G, Mr + M, Dyr + Dy, Dxr + Dx, Lr + L, Lyr + Ly,
        sub_blob_ + [blob],
    )

    # Accumulate deeper layers:
    root_blob['forks'][fork_type][1:] = \
        [*starmap( # Like map() except for taking multiple arguments.
            # Function (with multiple arguments):
            lambda Dert, sDert:
                (*starmap(op.add, zip(Dert, sDert)),), # Dert and sub_blob_ accum
            # Mapped iterables:
            zip(
                root_blob['forks'][fork_type][1:],
                blob['forks'][sub_fork_type][:],
            ),
        )]
    # Dert-only numpy.ndarray equivalent: (no sub_blob_ accumulation)
    # root_blob['forks'][fork_type][1:] += blob['forks'][fork_type]

    feedback(root_blob, fork_type)


def intra_fork(dert__, root_fork, Ave_blob, Ave, rng, iG, fa):  # root_fork reference is for blob_ and feedback

    # comparison: comp_g -> dert__(g, gg, m, dy, dx) or comp_a -> dert__(g, gg, m, dy, dx, ga, day, dax):
    dert__ = comp_i(dert__, rng, iG, not fa)  # not fa: alternate between g and a comp layers

    # clustering: dert__-> sub_blob_, with added g|a_Dert per sub_blob.Dert:

    P__ = form_P__(dert__, Ave, not fa)  # horizontal clustering
    P_ = scan_P__(P__)
    seg_ = form_segment_(P_)  # vertical clustering
    blob_ = form_blob_(seg_, root_fork, not fa)  # with feedback to root_fork

    Ave_blob *= len(blob_) / ave_n_sub_blobs
    Ave_blob *= rave  # cost per blob, same crit G for g_fork and a_fork
    Ave += ave  # cost per dert, both Ave and Ave_blob are for next intra_comp

    if not fa:
        Ave *= 2; Ave_blob *= 2  # a_fork_coef = 2: > cost, Aves += redundant g_sub_blob_: ga_val < gg_val

    for blob in root_fork[0]['blob_']:  # blob_ in layer_[0] of root_fork

        if fa: # blob is g_blob, evaluated for single a_fork (ig_sub_blobs formed by intra_comp(fa=0) are ignored):

            if blob['Dert']['G'].values() > ave_intra_blob:
                # initialize root_fork with flat Day=(Dyay, Dxay), Dax=(Dyax, Dxax):
                blob['fork_'][0] =\
                    dict(G=0, Gg=0, M=0, Dy=0, Dx=0, Ga=0, Dyay=0, Dxay=0, Dyax=0, Dxax=0, L=0, Ly=0, blob_=[])

                intra_fork(blob, blob['fork_'][0], Ave_blob, Ave, blob['Dert']['G'], rng, fa=1)  # fork_ = [a_fork]

        else: # blob is a_blob, a_sub_blobs formed by intra_comp(fa=1) are evaluated for three g_forks:

            for sub_blob in blob['fork_']['iG'][0]['sub_blob_']:  # sub_blob_ in layer_[0] of fork_['iG']

                G, Gg, M, Dy, Dx, Ga, Dyay, Dxay, Dyax, Dxax, L, Ly = sub_blob['Dert'].values()
                rdn = 1
                eval_fork_ = [      # sub_forks:
                    (G + M, 1, 0),  # rng+ / est match of input gradient iG=Dert[0] at rng+1, 0 if i is p
                    (Gg, rng+1, 1), # der+ / est match of gg: iG=Dert[1] at rng+rng+1, initial fork same as rng+
                    (Ga, rng+1, 5), # gad+ / est match of ga: iG=Dert[5] at rng+rng+1; a_rng+/ g_rng+: no indep value
                ]
                for val, irng, iG in sorted(eval_fork_, key=lambda val: val[0], reverse=True):

                    if  val > rdn * ave_intra_blob:  # cost of sub_blob_ eval in intra_fork
                        rdn += 1  # fork rdn = fork index + 1
                        rng += irng  # comp rng per fork
                        Ave_blob += ave_blob * rave * rdn
                        Ave += ave * rdn
                        # initialize root_fork at ['fork_'][rdn-2 |'iG']:
                        sub_blob['fork_']['iG'] = dict(G=0, Gg=0, M=0, Dy=0, Dx=0, Ly=0, L=0, blob_=[])

                        intra_fork(sub_blob, sub_blob['fork_'][iG], Ave_blob, Ave, blob['Dert'][iG], rng, fa=0)
                    else:
                        break
    return dert__