from math import hypot
from comp_angle import comp_angle
from comp_gradient import comp_gradient
from comp_range import comp_range
from intra_comp import intra_comp

'''
    intra_blob() evaluates for recursive frame_blobs() and comp_P() within each blob.
    combined frame_blobs and intra_blob form a 2D version of 1st-level algorithm.
    to be added:
    
    inter_sub_blob() will compare sub_blobs of same range and derivation within higher-level blob, bottom-up ) top-down:
    inter_level() will compare between blob levels, where lower composition level is integrated by inter_sub_blob
    match between levels' edges may form composite blob, axis comp if sub_blobs within blob margin?
    inter_blob() will be 2nd level 2D alg: a prototype for recursive meta-level alg

    Recursive intra_blob comp_branch() calls add a layer of sub_blobs, new dert to derts and Dert to Derts, in each blob.
    Dert params are summed params of sub_blobs per layer of derivation tree.
    Blob structure:
        
        I,  # top Dert
        Derts[ alt_Derts[ A, Ga, typ_Derts[ Dert: (alt, rng), (G, Dx, Dy, N, L, Ly, sub_blob_)]],     
        
        # Dert per current & lower layers of derivation tree for Dert-parallel comp_blob, 
        # len layer_Derts = comp_branch rdn, same-syntax cross-branch summation in deeper Derts,  
        # sub_blob_ per Dert is nested to depth = Derts[index] for Dert-sequential blob -> sub_blob access
        
        sign, # lower Derts are sign-mixed at depth > 0, alt-mixed at depth > 1, rng-mixed at depth > 2:
        alt,  # alternating layer index: -1 for ga, -2 for a, -3 for g
        #  or blob.input = (cyc, alt, typ), typ is nested input?
        rng,  # for comp_range only  
        
        map,  # boolean map of blob, to compute overlap; map and box of lower Derts are similar to top Dert
        box,  # boundary box: y0, yn, x0, xn
        
        root_blob,  # reference, to return summed blob params
        range_input_ = [cyc][alt][typ],  # input derts of prior intra_blob comp_branches, ini at intra_blob 

        seg_ =  # seg_s of lower Derts are packed in their sub_blobs
            [ seg_params,  
              Py_ = # vertical buffer of Ps per segment
                  [ P_params,       
                  
                    derts_ [ derts [ alt_derts [ typ_derts [ dert = (g, dx, dy) | a | p:   
                    # dert / current and higher derivation layers,
                    # typ: p, g_dert, intra_blob_-> cyc_dert_: [(a, ga_dert, (gg_dert, gga_dert, gr_dert_))]
                    
    input for:
        comp_angle: dx, dy = derts[-1][-1][-1][1,2]  # full index necessary?  
        comp_grad: ga = derts[-1][-1][-1][0] or g = derts[-2][-1][0][0]  # g of higher cycle, last typ dert 
        
        comp_range: p| a | g | ga = derts [cyc][alt][typ], buffered in range_input_
        # index: += cyc / intra_blob [ += alt / sequential comp_branch [ += typ / parallel comp_branch                            
'''
ave = 20
ave_eval = 100  # fixed cost of evaluating sub_blobs and adding root_blob flag
ave_blob = 200  # fixed cost per blob, not evaluated directly

ave_root_blob = 1000  # fixed cost of intra_comp, converting blob to root_blob
rave = ave_root_blob / ave_blob  # relative cost of root blob, to form rdn
ave_n_sub_blobs = 10

# These filters are accumulated for evaluated intra_comp:
# Ave += ave: cost per next-layer dert, fixed comp grain: pixel
# Ave_blob *= rave: cost per next root blob, variable len sub_blob_


def intra_blob_hypot(frame):  # evaluates for hypot_g and recursion, ave is per hypot_g & comp_angle, or all branches?

    for blob in frame.blob_:
        if blob.Derts[-1][0] > ave_root_blob:  # G > root blob cost
            intra_comp(blob, hypot_g, ave_root_blob, ave)  # g = hypot(dy, dx), adds Dert & sub_blob_, calls intra_blob

    return frame

def intra_blob(root_blob, comp_range_input_, Ave_blob, Ave):  # intra_comp(comp_branch) selection per branch per sub_blob

    Ave_blob *= rave  # estimated cost of redundant representations per blob
    Ave + ave         # estimated cost of redundant representations per dert
    new_comp_range_input_ = []  # for next intra_blob

    for blob in root_blob.sub_blob_:
        if blob.Derts[-1][0] > Ave_blob + ave_eval:  # noisy or directional G: > root blob conversion cost

            blob.alt = None  # no i comp, angle calc & comp (no a eval), no intra_blob call from comp_angle
            blob.rng = root_blob.rng
            Ave_blob = intra_comp(blob, comp_angle, Ave_blob, Ave)  # adjusted Ave_blob return, comp_angle only

            Ave_blob *= rave   # estimated cost per next sub_blob
            Ave + ave   # estimated cost per next comp

            for ga_blob in blob.sub_blob_:  # ga_blobs are defined by the sign of ga: gradient of angle
                rdn = 1
                G = ga_blob.Derts[-2][0]   # Derts: current + higher-layers params, no lower layers yet
                Ga = ga_blob.Derts[-1][0]  # different I per layer, not redundant to higher I

                val_ga = G       # value of forming gradient_of_gradient_of_angle deviation sub_blobs
                val_gg = G - Ga  # value of forming gradient_of_gradient deviation sub_blobs
                val_ = []  # + val_gr = Gr + Ga: value of forming extended-range gradient deviation sub_blobs:

                for typ, alt, rng in comp_range_input_:  # composite index of a root Dert:
                    Gr = blob.Derts[rng][alt][typ][0]
                    val_ += \
                        [((Gr + Ga), Ave_blob*2, comp_range, blob.alt, blob.rng+1)]  # alt of initial comp_grad

                val_ += [(val_ga, Ave_blob,   comp_gradient, (-1,-1), 1),  # current cyc and alt, no rng accumulation
                         (val_gg, Ave_blob*2, comp_gradient, (-2,-1), 1)]  # current cyc and alt, from typ

                sorted(val_, key=lambda val: val[0], reverse=True)
                for val, threshold, comp_branch, alt, rng in val_:

                    if val > threshold * rdn:
                        ga_blob.alt = alt
                        ga_blob.rng = rng
                        rdn += 1
                        intra_comp(ga_blob, comp_branch, Ave_blob + ave_root_blob * rdn, Ave + ave * rdn)
                        # root_blob.Derts[-1] += Derts, derts += dert, intra_blob call eval
                    else:
                        break
    ''' 
    if Ga > Ave_blob: 
       intra_comp( ablob, comp_gradient, Ave_blob, Ave)  # forms g_angle deviation sub_blobs

    if G - Ga > Ave_blob * 2:  # 2 crit, -> i_dev - a_dev: stable estimated-orientation G (not if -Ga) 
       intra_comp( ablob, comp_gradient, Ave_blob, Ave)  # likely edge blob -> gg deviation sub_blobs

    if G + Ga > Ave_blob * 2:  # 2 crit, -> i_dev + a_dev: noise, likely sign reversal & distant match
       intra_comp( ablob, comp_range, Ave_blob, Ave)  # forms extended-range-g- deviation sub_blobs
    
    end of intra_comp:
    Ave_blob *= len(blob.sub_blob_) / ave_n_sub_blobs  # adjust by actual / average n sub_blobs
    
    if not comp_angle:
       if blob.Derts[-1][0] > Ave_blob + ave_eval:  # root_blob G > cost of evaluating sub_blobs
          intra_blob( ablob, Ave_blob, Ave, rng)     

    ave and ave_blob are averaged between branches, else multiple blobs, adjusted for ave comp_range x comp_gradient rdn
    g and ga are dderived, blob of min_g? val -= branch switch cost?
    no Ave = ave * ablob.L, (G + Ave) / Ave: always positive?

    comp_P_() if estimated val_PP_ > ave_comp_P, for blob in root_blob.sub_blob_: defined by dx_g:
     
    L + I + |Dx| + |Dy|: P params sum is a superset of their match Pm, 
    * L/ Ly/ Ly: elongation: >ave Pm? ~ box (xn - x0) / (yn - y0), 
    * Dy / Dx:   variation-per-dimension bias 
    * Ave / Ga:  angle match rate?
    '''

    return root_blob


def hypot_g(P_, dert___):
    dert__ = []  # dert_ per P, dert__ per line, dert___ per blob

    for P in P_:
        x0 = P[1]
        dert_ = P[-1]
        for i, (p, ncomp, dy, dx, g) in enumerate(dert_):
            g = hypot(dx, dy)

            dert_[i] = [(p, ncomp, dy, dx, g)]  # p is replaced by a in odd layers and absent in deep even layers
        dert__.append((x0, dert_))
    dert___.append(dert__)

    # ---------- hypot_g() end ----------------------------------------------------------------------------------------------


