from scipy import misc

'''
Level 1:

Cross-comparison between consecutive pixels within horizontal scan line (row).
Resulting difference patterns dPs (spans of pixels forming same-sign differences)
and relative match patterns vPs (spans of pixels forming same-sign predictive value)
are redundant representations of each line of pixels.

I don't pack arguments because this code is optimized for visibility rather than speed 
'''

def range_increment(a, aV, aD, min_r, A, AV, AD, r, t_):

    if r > min_r:  # A, AV, AD inc.to adjust for redundancy to patterns formed by prior comp:
        A += a     # a: min m for inclusion into positive vP
        AV += aV   # aV: min V for initial comp() recursion, AV: min V for higher recursions

    if r > min_r-1:  # default range is shorter for d_: redundant ds are smaller than ps
        AD += aD     # aV: min |D| for comp() recursion over d_[w], AD: min |D| for recursion

    # or by default: initial r = min_r?

    X = len(t_)
    it_ = t_  # to differentiate from initialized t_:

    vP_, dP_ = [],[]  # r was incremented in higher-scope p_
    pri_s, I, D, V, rv, olp, t_, olp_ = 0, 0, 0, 0, 0, 0, [], []  # tuple vP = 0
    pri_sd, Id, Dd, Vd, rd, dolp, d_, dolp_ = 0, 0, 0, 0, 0, 0, [], []  # tuple dP = 0

    for x in range(r+1, X):

        p, fd, fv = it_[x]       # compared to a pixel at x-r-1:
        pp, pfd, pfv = it_[x-r]  # previously compared p(ignored), its fd, fv to next p
        fv += pfv  # fuzzy v is summed over extended-comp range
        fd += pfd  # fuzzy d is summed over extended-comp range

        pri_p, pri_fd, pri_fv = it_[x-r-1]  # for comp(p, pri_p), pri_fd and pri_fv are ignored

        pri_s, I, D, V, rv, t_, olp, olp_, pri_sd, Id, Dd, Vd, rd, d_, dolp, dolp_, vP, dP_ = \
        comp(p, pri_p, fd, fv, x, X,
             pri_s, I, D, V, rv, t_, olp, olp_,
             pri_sd, Id, Dd, Vd, rd, d_, dolp, dolp_,
             a, aV, aD, min_r, A, AV, AD, r, vP_, dP_)

    return vP_, dP_  # local vPs and dPs to replace p_, A, AV, AD accumulated per comp recursion


def derivation_increment(a, aV, aD, min_r, A, AV, AD, r, d_):

    if r > min_r:
        A += a; AV += aV
    if r > min_r-1:
        AD += aD

    # or by default: initial r = min_r?

    X = len(d_)
    id_ = d_  # to differentiate from initialized d_:

    # or input tuples if derivation_increment() is called from range_increment()?

    fd, fv, r, vP_, dP_ = 0, 0, 0, [], []  # r is initialized for each d_; or passed from comp()?
    pri_s, I, D, V, rv, olp, t_, olp_ = 0, 0, 0, 0, 0, 0, [], []  # tuple vP = 0,
    pri_sd, Id, Dd, Vd, rd, dolp, d_, dolp_ = 0, 0, 0, 0, 0, 0, [], []  # tuple dP = 0

    pri_p = id_[0]

    for x in range(1, X):

        p = id_[x]  # or pop()

        pri_s, I, D, V, rv, t_, olp, olp_, pri_sd, Id, Dd, Vd, rd, d_, dolp, dolp_, vP, dP_ = \
        comp(p, pri_p, fd, fv, x, X,
             pri_s, I, D, V, rv, t_, olp, olp_,
             pri_sd, Id, Dd, Vd, rd, d_, dolp, dolp_,
             a, aV, aD, min_r, A, AV, AD, r, vP_, dP_)

        pri_p = p

    return vP_, dP_  # local vPs and dPs to replace d_


def comp(p, pri_p, fd, fv, x, X,  # input variables
         pri_s, I, D, V, rv, t_, olp, olp_,  # variables of vP
         pri_sd, Id, Dd, Vd, rd, d_, dolp, dolp_,  # variables of dP
         a, aV, aD, min_r, A, AV, AD, r, vP_, dP_):  # filter variables and output patterns

    d = p - pri_p      # difference between consecutive pixels
    m = min(p, pri_p)  # match between consecutive pixels
    v = m - A          # relative match (predictive value) between consecutive pixels

    fd += d  # fuzzy d accumulates ds between p and all prior ps within min_r, via range_increment()
    fv += v  # fuzzy v accumulates vs between p and all prior ps within min_r, via range_increment()

    # or it_= min_r comp before form, then separate 1-incr recursive comp? or min_r incr?

    # formation of value pattern vP: span of pixels forming same-sign v s:

    s = 1 if v > 0 else 0  # s: positive sign of v
    if x > r+2 and (s != pri_s or x == X-1):  # if derived pri_s miss, vP is terminated

        if len(t_) > r+3 and pri_s == 1 and V > AV:  # min 3 comp over extended distance within p_:

            r += 1  # r: incremental range-of-comp counter
            rv = 1  # rv: incremental range flag
            t_.append(range_increment(a, aV, aD, min_r, A, AV, AD, r, t_))

        p = I / len(t_); d = D / len(t_); v = V / len(t_)  # default to eval overlap, poss. div.comp
        vP = pri_s, p, I, d, D, v, V, rv, t_, olp_
        vP_.append(vP)  # output of vP, related to dP_ by overlap only, no distant comp till level 3

        o = len(vP_), olp  # len(P_) is index of current vP
        dolp_.append(o)  # indexes of overlapping vPs and olp are buffered at current dP

        I, D, V, rv, olp, dolp, t_, olp_ = 0, 0, 0, 0, 0, 0, [], []  # initialized vP and olp_

    pri_s = s   # vP (span of pixels forming same-sign v) is incremented:
    olp += 1    # overlap to concurrent dP
    I += pri_p  # ps summed within vP
    D += fd     # fuzzy ds summed within vP
    V += fv     # fuzzy vs summed within vP
    t = pri_p, fd, fv  # inputs for inc_rng comp are tuples, vs. pixels for initial comp
    t_.append(t)  # tuples (pri_p, fd, fv) are buffered within each vP

    # formation of difference pattern dP: span of pixels forming same-sign d s:
    # but these ds are not fuzzy, summation and sign check should start when r = min_r?

    sd = 1 if d > 0 else 0  # sd: positive sign of d;  it should be fd?
    if x > r+2 and (sd != pri_sd or x == X-1):  # if derived pri_sd miss, dP is terminated

        if len(d_) > 3 and abs(Dd) > AD:  # min 3 comp within d_:

            rd = 1  # rd: incremental derivation flag:
            d_.append(derivation_increment(a, aV, aD, min_r, A, AV, AD, r, d_))

        pd = Id / len(d_); dd = Dd / len(d_); vd = Vd / len(d_)  # to evaluate olp Ps directly
        dP = pri_sd, pd, Id, dd, Dd, vd, Vd, rd, d_, dolp_
        dP_.append(dP)  # output of dP

        o = len(dP_), dolp  # len(P_) is index of current dP
        olp_.append(o)  # indexes of overlapping dPs and dolps are buffered at current vP

        Id, Dd, Vd, rd, olp, dolp, d_, dolp_ = 0, 0, 0, 0, 0, 0, [], []  # initialized dP and dolp_

    pri_sd = sd  # dP (span of pixels forming same-sign d) is incremented:
    dolp += 1    # overlap to concurrent vP
    Id += pri_p  # ps summed within dP
    Dd += fd     # fuzzy ds summed within dP
    Vd += fv     # fuzzy vs summed within dP
    d_.append(fd)  # prior fds of the same sign are buffered within dP

    return pri_s, I, D, V, rv, t_, olp, olp_, pri_sd, Id, Dd, Vd, rd, d_, dolp, dolp_, vP_, dP_
    # for next p comparison, vP and dP increment, and output


def level_1(Fp_):  # last '_' distinguishes array name from element name

    FP_ = []  # output frame of vPs: relative match patterns, and dPs: difference patterns
    Y, X = Fp_.shape  # Y: frame height, X: frame width

    a = 127  # minimal filter for vP inclusion
    aV = 63  # minimal filter for incremental-range comp
    aD = 63  # minimal filter for incremental-derivation comp
    min_r=0  # default range of fuzzy comparison, initially 0

    for y in range(Y):

        p_ = Fp_[y, :]  # y is index of new line ip_

        if min_r == 0: A = a; AV = aV  # actual filters, incremented per comp recursion
        else: A = 0; AV = 0  # if r > min_r

        if min_r <= 1: AD = aD
        else: AD = 0

        # or separate fuzzy comp while r < min_r: level_1_2D (for it in it_),
        # before eval, vPs and dPs form;  min_r not used elsewhere

        fd, fv, r, x, vP_, dP_ = 0, 0, 0, 0, [], []  # i/o tuple
        pri_s, I, D, V, rv, olp, t_, olp_ = 0, 0, 0, 0, 0, 0, [], []  # vP tuple
        pri_sd, Id, Dd, Vd, rd, dolp, d_, dolp_ = 0, 0, 0, 0, 0, 0, [], []  # dP tuple

        pri_p = p_[0]

        for x in range(1, X):  # cross-compares consecutive pixels

            p = p_[x]  # new pixel for comp to prior pixel, could use pop()?

            pri_s, I, D, V, rv, t_, olp, olp_, pri_sd, Id, Dd, Vd, rd, d_, dolp, dolp_, vP_, dP_ = \
            comp(p, pri_p, fd, fv, x, X,
                 pri_s, I, D, V, rv, t_, olp, olp_,
                 pri_sd, Id, Dd, Vd, rd, d_, dolp, dolp_,
                 a, aV, aD, min_r, A, AV, AD, r, vP_, dP_)

            pri_p = p  # prior pixel, pri_ values are always derived before use

        LP_ = vP_, dP_
        FP_.append(LP_)  # line of patterns is added to frame of patterns, y = len(FP_)

    return FP_  # output to level 2

f = misc.face(gray=True)  # input frame of pixels
f = f.astype(int)
level_1(f)

# at vP term: print ('type', 0, 'pri_s', pri_s, 'I', I, 'D', D, 'V', V, 'rv', rv, 'p_', p_)
# at dP term: print ('type', 1, 'pri_sd', pri_sd, 'Id', Id, 'Dd', Dd, 'Vd', Vd, 'rd', rd, 'd_', d_)

