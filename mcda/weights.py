"""
weights.py - the OBJECTIVE criterion weights: m-ITARA stages I and II, and EWCS.

"Objective" means derived from the decision matrix alone - no expert opinion
enters this file. Two complementary readings of the same matrix:

    stage I   how far apart a criterion spreads the alternatives, ignoring
              gaps too small to be meaningful (the indifference threshold IT)
    stage II  how much a criterion merely repeats what the others already say,
              measured by correlation

A criterion earns weight by separating the alternatives (stage I) and by
saying something the others do not (stage II). The two vectors are then fused
by ewcs_fusion into one objective weight vector.

ewcs_fusion is used a SECOND time, in integrated.py, to fuse this objective
vector with the subjective one that opa.py produces. It lives here because it
is a weighting operator, not because it belongs to m-ITARA.
"""

import numpy as np

from .utils import ensure_2d, safe_normalize_to_1


def mitara_stage1_independent_weights(D, AL, IT):
    """m-ITARA stage I - objective weights from each criterion's own spread.

        Appends the aspiration level AL as an extra alternative row, normalises
        every column by its own total, sorts each column, and measures the gaps
        between consecutive alternatives that exceed the normalised indifference
        threshold NIT. A criterion whose alternatives all sit close together earns
        little weight, because it separates nothing.

            A     = D_ext / column sum      normalised decision matrix [-]
            NIT   = IT / column sum         indifference threshold, normalised
            beta  = A sorted up each column
            gamma = consecutive differences of beta
            delta = max(gamma - NIT, 0)     only gaps that clear the threshold
            nu    = column-wise Euclidean norm of delta
            w1    = nu normalised to sum to 1

        Returns every intermediate as well as w1, so the notebook can display the
        working rather than just the answer.
        """
    D = ensure_2d(D)
    AL = np.asarray(AL, dtype=float).reshape(1, -1)
    IT = np.asarray(IT, dtype=float).ravel()

    m, n = D.shape
    if AL.shape[1] != n or IT.shape[0] != n:
        raise ValueError("Dimension mismatch in Stage I inputs.")

    D_ext = np.vstack([D, AL])
    col_sum = np.sum(D_ext, axis=0)
    if np.any(np.isclose(col_sum, 0.0)):
        raise ValueError("Some criterion column sums are 0, so normalization cannot be performed.")

    A = D_ext / col_sum
    NIT = IT / col_sum

    beta = np.sort(A, axis=0)
    gamma = beta[1:, :] - beta[:-1, :]
    delta = np.maximum(gamma - NIT.reshape(1, -1), 0.0)
    nu = np.sqrt(np.sum(delta ** 2, axis=0))
    w1 = safe_normalize_to_1(nu)

    return {
        "D_ext": D_ext,
        "A": A,
        "NIT": NIT,
        "beta": beta,
        "gamma": gamma,
        "delta": delta,
        "nu": nu,
        "w1": w1,
    }


def stage2_dependent_weights_corr(D, types_bc, AL, WL):
    """m-ITARA stage II - weights from how much each criterion repeats the others.

        Rescales every column against the two benchmarks, then correlates the
        columns. A criterion that correlates strongly with all the others carries
        little new information and earns little weight:

            u   = (y - WL) / (AL - WL)      the rescaling, methodological
                                            report Eq. 9, over the REAL
                                            alternatives only
            R   = Pearson correlation of the rescaled columns        Eq. 10-11
            phi = sum over j of (1 - R[i][j])                        Eq. 12
            w2  = phi normalised to sum to 1                         Eq. 13

        Pearson correlation is invariant under the affine rescaling, so R (and
        hence w2) equals what a plain min-max rescaling would give; the
        rescaling follows the published method.

        Note: AL and WL come from integrated.derive_thresholds, which assumes
        every criterion is a cost (see the note there).

        A criterion whose two benchmarks coincide (AL == WL) would divide by
        zero, so it is left at zero, which is what the min-max form did for a
        column with no spread. NaNs in R - which is what a constant column
        produces - are read as zero correlation. Returns X, R, phi and w2.
        """
    D = ensure_2d(D)
    types_bc = [str(t).strip().upper() for t in types_bc]

    m, n = D.shape
    if len(types_bc) != n:
        raise ValueError("types_bc length must match the number of criteria.")

    # The type is no longer what sets the direction - AL and WL do, and which of
    # the two is larger is what encodes benefit or cost. It is still validated,
    # because a typo here means the caller has misdescribed its own matrix.
    for j in range(n):
        if types_bc[j] not in ("B", "C"):
            raise ValueError(f"Invalid criterion type at column {j+1}: {types_bc[j]}. Use B or C.")

    AL = np.asarray(AL, dtype=float).ravel()
    WL = np.asarray(WL, dtype=float).ravel()
    if AL.shape[0] != n or WL.shape[0] != n:
        raise ValueError("Dimension mismatch in Stage II inputs: AL and WL must "
                         "carry one value per criterion.")

    span = AL - WL
    X = np.zeros_like(D, dtype=float)
    usable = ~(np.isclose(span, 0.0) | np.isnan(span))
    X[:, usable] = (D[:, usable].astype(float) - WL[usable]) / span[usable]

    R = np.corrcoef(X, rowvar=False)
    R = np.nan_to_num(R, nan=0.0)

    phi = np.sum(1.0 - R, axis=1)
    w2 = safe_normalize_to_1(phi)

    return {"X": X, "R": R, "phi": phi, "w2": w2}


def ewcs_fusion(w1, w2):
    """Fuse two weight vectors by the Extended Weighted Compromise Solution.

        Solves the 2x2 normal system for the pair of multipliers p that best
        reconciles w1 and w2, takes their absolute values, normalises them to sum
        to 1, and returns wagg = p1*w1 + p2*w2 renormalised.

        Called TWICE in one analysis: once to fuse m-ITARA stage I with stage II
        into the objective weights, and once to fuse those with the subjective
        (fuzzy OPA) weights into the final ones. A singular system - which means
        the two vectors carry the same information - falls back to equal shares.
        """
    w1 = np.asarray(w1, dtype=float).ravel()
    w2 = np.asarray(w2, dtype=float).ravel()

    if w1.shape != w2.shape:
        raise ValueError("w1 and w2 must have the same length.")

    a11 = float(np.dot(w1, w1))
    a12 = float(np.dot(w1, w2))
    a22 = float(np.dot(w2, w2))

    A = np.array([[a11, a12], [a12, a22]], dtype=float)
    b = np.array([a11, a22], dtype=float)

    det = np.linalg.det(A)
    if np.isclose(det, 0.0):
        p_raw = np.array([1.0, 1.0])
    else:
        p_raw = np.linalg.solve(A, b)

    p_star = np.abs(p_raw)
    p_star = p_star / np.sum(p_star)

    wagg = p_star[0] * w1 + p_star[1] * w2
    wagg = safe_normalize_to_1(wagg)

    return {"p_raw": p_raw, "p_star": p_star, "wagg": wagg}
