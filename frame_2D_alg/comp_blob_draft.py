'''
Cross-compare blobs with incrementally intermediate adjacency, within a frame
'''

from class_cluster import ClusterStructure, NoneType
from frame_blobs import ave
import numpy as np
import cv2

class CderBlob(ClusterStructure):

    blob = object
    _blob = object
    mB = int
    dB = int
    # not in used for accumulation now
    dI = int
    mI = int
    dA = int
    mA = int
    dG = int
    mG = int
    dM = int
    mM = int

class CBblob(ClusterStructure):

    # derBlob params
    mB = int
    dB = int
    # not in used for accumulation now
    dI = int
    mI = int
    dA = int
    mA = int
    dG = int
    mG = int
    dM = int
    mM = int

    blob_ = list

ave_mB = 0  # ave can't be negative
ave_rM = .7  # average relative match at rL=1: rate of ave_mB decay with relative distance, due to correlation between proximity and similarity
ave_da = 0.7853  # da at 45 degree


def cross_comp_blobs(frame):
    '''
    root function of comp_blob: cross compare blobs with their adjacent blobs in frame.blob_, including sub_layers
    '''
    blob_ = frame.blob_

    for blob in blob_:  # each blob forms derBlob per compared adj_blob and accumulates adj_blobs'derBlobs:
        if len(blob.derBlob_) == 0:
            comp_blob_recursive(blob, blob.adj_blobs[0], derBlob_=[])
        # derBlob_ is local and but not frame-wide, it is per blob

    bblob_ = form_bblob_(blob_)  # form blobs of blobs, connected by mutual match

    visualize_cluster_(bblob_, blob_, frame)

    return bblob_


def comp_blob_recursive(blob, adj_blob_, derBlob_):
    '''
    called by cross_comp_blob to recursively compare blob to adj_blobs in incremental layers of adjacency
    '''
    derBlob_pair_ = [ [derBlob.blob, derBlob._blob]  for derBlob in derBlob_]  # blob, adj_blob pair

    for adj_blob in adj_blob_:
        if [adj_blob, blob] in derBlob_pair_:  # derBlob.blob=adj_blob, derBlob._blob=blob
            derBlob = derBlob_[derBlob_pair_.index([adj_blob,blob])]
            # also adj_blob.rdn += 1?
        elif [blob, adj_blob] not in derBlob_pair_:  # form new derBlob if blob pair wasn't compared in prior function call
            derBlob = comp_blob(blob, adj_blob)  # compare blob and adjacent blob
            derBlob_.append(derBlob)             # also frame-wide

        if "derBlob" in locals(): # derBlob exists
            accum_derBlob(blob, derBlob)         # from all compared blobs, regardless of mB sign

            if derBlob.mB > 0:  # replace blob with adj_blob for continued adjacency search:
                comp_blob_recursive(adj_blob, adj_blob.adj_blobs[0], derBlob_)  # search depth could be different, compare anyway
                break
            elif blob.M + blob.neg_mB + derBlob.mB > ave_mB:  # neg mB but positive comb M,
                # extend blob comparison to adjacents of adjacent, depth-first
                blob.neg_mB += derBlob.mB  # mB and distance are accumulated over comparison scope
                blob.distance += np.sqrt(adj_blob.A)
                comp_blob_recursive(blob, adj_blob.adj_blobs[0], derBlob_)


def comp_blob(blob, _blob):
    '''
    cross compare _blob and blob
    '''

    derBlob = blob.compare(_blob, blob.A)

    derBlob.mB = derBlob.I.m + derBlob.A.m + derBlob.G.m + derBlob.M.m +  derBlob.Vector.M  \
    - ave_mB * (ave_rM ** ((1+blob.distance) / np.sqrt(blob.A)))  # deviation from average blob match at current distance

    derBlob.dB = derBlob.I.d + derBlob.A.d + derBlob.G.d + derBlob.M.d +  derBlob.Vector.d
    '''
    difference = _blob.difference(blob)
    match = _blob.min_match(blob)
    
    Ave = ave * blob.A; _Ave = ave *_blob.A  # why ave is defined size? Is it due to relative to size of blob?
    # prevent zero division
    if blob.G + Ave == 0: G = 1
    else: G = blob.G + Ave
    if _blob.G + _Ave == 0: _G = 1
    else: _G = _blob.G + _Ave
    sin = blob.Dy / (G); _sin = _blob.Dy / (_G)   # sine component   = dy/g
    cos = blob.Dx / (G); _cos = _blob.Dx / (_G)   # cosine component = dx/g
    sin_da = (cos * _sin) - (sin * _cos)          # using formula : sin(α − β) = sin α cos β − cos α sin β
    cos_da = (cos * _cos) + (sin * _sin)          # using formula : cos(α − β) = cos α cos β + sin α sin β
    da = np.arctan2( sin_da, cos_da )
    ma = ave_da - abs(da)
    mB = match['I'] + match['A'] + match['G'] + match['M'] + ma \
    - ave_mB * (ave_rM ** ((1+blob.distance) / np.sqrt(blob.A)))  # deviation from average blob match at current distance
    dB = difference['I'] + difference['A'] + difference['G'] + difference['M'] + da
    derBlob  = CderBlob(blob=blob, _blob=_blob, mB=mB, dB=dB)  # blob is core node, _blob is adjacent blob
    if _blob.fsliced and blob.fsliced:
        pass
        
    '''
    return derBlob


def form_bblob_(blob_):
    '''
    bblob is a cluster (graph) of blobs with positive mB to any other member blob, formed by comparing adj_blobs
    two kinds of bblobs: merged_blob and blob_graph
    '''
    bblob_ = []
    for blob in blob_:
        if blob.mB > 0 and not isinstance(blob.bblob, CBblob):  # init bblob with current blob
            bblob = CBblob()
            merged_ids = [bblob.id]
            accum_bblob(bblob_, bblob, blob, merged_ids)  # accum blob into bblob
            form_bblob_recursive(bblob_, bblob, bblob.blob_, merged_ids)

    # test code to see duplicated blobs in bblob, not needed in actual code
    for bblob in bblob_:
        bblob_blob_id_ = [ blob.id for blob in bblob.blob_]
        if len(bblob_blob_id_) != len(np.unique(bblob_blob_id_)):
            raise ValueError("Duplicated blobs")

    return bblob_


def form_bblob_recursive(bblob_, bblob, blob_, merged_ids):

    blobs2check = []  # list of blobs to check for inclusion in bblob

    for blob in blob_:  # search new added blobs to get potential border clustering blob
        if (blob.mB > 0):  # positive summed mBs

            if isinstance(blob.bblob, CBblob) and blob.bblob.id not in merged_ids:  # merge existing bblobs
                if blob.bblob in bblob_:
                    bblob_.remove(blob.bblob)  # remove the merging bblob from bblob_
                merge_bblob(bblob_, bblob, blob.bblob, merged_ids)
            else:
                for derBlob in blob.derBlob_:
                    # blob is in bblob.blob_, but derBlob._blob is not in bblob_blob_ and (DerBlob.mB > 0 and blob.mB > 0):
                    if (derBlob._blob not in bblob.blob_) and (derBlob._blob.mB + blob.mB > 0):
                        accum_bblob(bblob_, bblob, derBlob._blob, merged_ids)  # pack derBlob._blob in bblob
                        blobs2check.append(derBlob._blob)
                    elif (derBlob.blob not in bblob.blob_) and (derBlob.blob.mB + blob.mB > 0):
                        accum_bblob(bblob_, bblob, derBlob.blob, merged_ids)
                        blobs2check.append(derBlob.blob)

    if blobs2check:
        form_bblob_recursive(bblob_, bblob, blobs2check, merged_ids)

    bblob_.append(bblob)  # pack bblob after scanning all accessible derBlobs


def merge_bblob(bblob_, _bblob, bblob, merged_ids):

    merged_ids.append(bblob.id)

    for blob in bblob.blob_: # check and merge blobs of bblob
        if blob not in _bblob.blob_:
            _bblob.blob_.append(blob) # add blob to bblob
            blob.bblob = _bblob       # update bblob reference of blob

            for derBlob in blob.derBlob_: # pack adjacent blobs of blob into _bblob
                if derBlob.blob not in _bblob.blob_:     # if blob not in _bblob.blob_, _blob in _bblob.blob_
                    merge_blob = derBlob.blob
                elif derBlob._blob not in _bblob.blob_:  # if _blob not in _bblob.blob_, blob in _bblob.blob_
                    merge_blob = derBlob._blob

                if "merge_blob" in locals():
                    if isinstance(merge_blob.bblob, CBblob):  # derBlob._blob is having bblob, merge them
                        if merge_blob.bblob.id not in merged_ids:
                            if merge_blob.bblob in bblob_:
                                bblob_.remove(merge_blob.bblob) # remove the merging bblob from bblob_
                            merge_bblob(bblob_, _bblob, merge_blob.bblob, merged_ids)
                    else:
                        # accumulate derBlob only if either one of _blob or blob (adjacent) not in _bblob
                        _bblob.accum_from(derBlob)
                        _bblob.blob_.append(merge_blob)
                        merge_blob.bblob = _bblob

def accum_derBlob(blob, derBlob):

    blob.accum_from(derBlob)
    blob.derBlob_.append(derBlob)

def accum_bblob(bblob_, bblob, blob, merged_ids):

    bblob.blob_.append(blob) # add blob to bblob
    blob.bblob = bblob       # update bblob reference of blob

    for derBlob in blob.derBlob_: # pack adjacent blobs of blob into bblob
        if derBlob.blob not in bblob.blob_:     # if blob not in bblob.blob_, _blob in bblob.blob_
            merge_blob = derBlob.blob
        elif derBlob._blob not in bblob.blob_:  # if _blob not in bblob.blob_, blob in bblob.blob_
            merge_blob = derBlob._blob

        if "merge_blob" in locals():
            if isinstance(merge_blob.bblob, CBblob): # derBlob._blob or derBlob.blob is having bblob, merge them
                if merge_blob.bblob.id not in merged_ids:
                    if merge_blob.bblob in bblob_:
                        bblob_.remove(merge_blob.bblob) # remove the merging bblob from bblob_
                    merge_bblob(bblob_, bblob, merge_blob.bblob, merged_ids)
            else:
                # accumulate derBlob only if either one of _blob or blob (adjacent) not in bblob
                bblob.accum_from(derBlob)
                bblob.blob_.append(merge_blob)
                merge_blob.bblob = bblob

'''
    cross-comp among sub_blobs in nested sub_layers:
    _sub_layer = bblob.sub_layer[0]
    for sub_layer in bblob.sub_layer[1:]:
        for _sub_blob in _sub_layer:
            for sub_blob in sub_layer:
                comp_blob(_sub_blob, sub_blob)
        merge(_sub_layer, sub_layer)  # only for sub-blobs not combined into new bblobs by cross-comp
'''


def visualize_cluster_(bblob_, blob_, frame):

    colour_list = []  # list of colours:
    colour_list.append([200, 130, 1])  # blue
    colour_list.append([75, 25, 230])  # red
    colour_list.append([25, 255, 255])  # yellow
    colour_list.append([75, 180, 60])  # green
    colour_list.append([212, 190, 250])  # pink
    colour_list.append([240, 250, 70])  # cyan
    colour_list.append([48, 130, 245])  # orange
    colour_list.append([180, 30, 145])  # purple
    colour_list.append([40, 110, 175])  # brown
    colour_list.append([192, 192, 192])  # silver
    colour_list.append([255, 255, 0])  # blue2
    colour_list.append([34, 34, 178])  # red2
    colour_list.append([0, 215, 255])  # yellow2
    colour_list.append([50, 205, 50])  # green2
    colour_list.append([114, 128, 250])  # pink2
    colour_list.append([255, 255, 224])  # cyan2
    colour_list.append([0, 140, 255])  # orange2
    colour_list.append([204, 50, 153])  # purple2
    colour_list.append([63, 133, 205])  # brown2
    colour_list.append([128, 128, 128])  # silver2

    # initialization
    ysize, xsize = frame.dert__[0].shape
    blob_img = np.zeros((ysize, xsize,3)).astype('uint8')
    cluster_img = np.zeros((ysize, xsize,3)).astype('uint8')
    img_separator = np.zeros((ysize,3,3)).astype('uint8')

    # create mask
    blob_mask = np.zeros_like(frame.dert__[0]).astype('uint8')
    cluster_mask = np.zeros_like(frame.dert__[0]).astype('uint8')

    blob_colour_index = 1
    cluster_colour_index = 1

    cv2.namedWindow('blobs & clusters', cv2.WINDOW_NORMAL)

    # draw blobs
    for blob in blob_:
        cy0, cyn, cx0, cxn = blob.box
        blob_mask[cy0:cyn,cx0:cxn] += (~blob.mask__ * blob_colour_index).astype('uint8')
        blob_colour_index += 1

    # draw blob cluster of bblob
    for bblob in bblob_:
        for blob in bblob.blob_:
            cy0, cyn, cx0, cxn = blob.box
            blob_colour_index += 1
            cluster_mask[cy0:cyn,cx0:cxn] += (~blob.mask__ *cluster_colour_index).astype('uint8')

        # increase colour index
        cluster_colour_index += 1

        # insert colour of blobs
        for i in range(1,blob_colour_index):
            blob_img[np.where(blob_mask == i)] = colour_list[i % 20]

        # insert colour of clusters
        for i in range(1,cluster_colour_index):
            cluster_img[np.where(cluster_mask == i)] = colour_list[i % 20]

        # combine images for visualization
        img_concat = np.concatenate((blob_img, img_separator,
                                    cluster_img, img_separator), axis=1)

        # plot cluster of blob
        cv2.imshow('blobs & clusters',img_concat)
        cv2.resizeWindow('blobs & clusters', 1920, 720)
        cv2.waitKey(10)

    cv2.waitKey(0)
    cv2.destroyAllWindows()


def generate_unique_id(id1, id2):
    '''
    generate unique id based on id1 and id2, different order of id1 and id2 yields unique id in different sign
    '''
    # generate unique id with sign
    '''
    get sign based on order of id1 and id2, output would be +1 or -1
    id_sign = ((0.5*(id1+id2)*(id1+id2+1) + id1) - (0.5*(id2+id1)*(id2+id1+1) + id2)) / abs(id1-id2)
    modified pairing function, so that different order of a and b will generate same value
    unique_id = (0.5*(id1+id2)*(id1+id2+1) + (id1*id2)) * id_sign
    '''
    # generate unique id without sign
    unique_id = (0.5 * (id1 + id2) * (id1 + id2 + 1) + (id1 * id2))

    return unique_id