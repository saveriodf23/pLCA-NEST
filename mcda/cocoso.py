"""
cocoso.py - the ranking stage: fuzzy CoCoSo with Bonferroni aggregation.

This is where weights and alternatives finally meet. Given the fuzzy decision
matrix and the final criterion weights, it produces the ranking that is the
whole point of the tool. Five functions, run in this order:

    normalize_cocoso_bonferroni   scale every criterion to [0, 1] in its own
                                  benefit/cost direction, so that criteria in
                                  different units become comparable
    compute_bonferroni            aggregate across criteria, two ways: SCoB
                                  (a sum form) and PCoB (a product form)
    relative_significance         defuzzify both, then form the three CoCoSo
                                  appraisal scores Kia, Kib, Kic
    final_scores_bonferroni       combine those into K and rank
    cocoso_bonferroni_from_app    the four above, in order

WHY BONFERRONI. A plain weighted sum treats the criteria as independent. The
Bonferroni mean aggregates over every ORDERED PAIR of distinct criteria
instead, so an alternative that scores well on two criteria at once is
rewarded for the pairing, not only for the two scores. phi1 and phi2 set how
the two members of a pair are balanced; at the default 1.0/1.0 they are equal.

WHY THREE APPRAISAL SCORES. CoCoSo's Kia, Kib and Kic normalise the same pair
of aggregates three different ways - by their total, by the smallest, and by
the largest - and K combines all three. No single normalisation decides the
ranking on its own.

DEFUZZIFY FIRST ("revised, Excel-style"): SCoB and PCoB are defuzzified
before the three K scores are formed from the crisp values, rather than being
carried through fuzzily and defuzzified at the end. That ordering is a
modelling decision and it changes the numbers.
"""

import math

import numpy as np
import pandas as pd

from .config import EPS
from .fuzzy import fuzzy_df_to_nested_matrix
from .utils import defuzz_tfn, safe_normalize_to_1, safe_pos, to_bc_label


def normalize_cocoso_bonferroni(decision, types_bc):
    """Normalise the fuzzy decision matrix to [0, 1], by criterion direction.

        For a BENEFIT criterion each component is divided by the largest upper
        bound in that column. For a COST criterion the smallest lower bound is
        divided BY each component - which also swaps the triple's ends, so the
        result is still ordered l <= m <= u. Every divisor and every divisand goes
        through safe_pos first, because a zero in either place is an inf.
        """
    n_alt = len(decision)
    n_crit = len(types_bc)
    norm = [[(0.0, 0.0, 0.0) for _ in range(n_crit)] for _ in range(n_alt)]

    for j in range(n_crit):
        typ = to_bc_label(types_bc[j])

        if typ == "B":
            max_u = max(decision[i][j][2] for i in range(n_alt))
            max_u = safe_pos(max_u)
            for i in range(n_alt):
                l, m, u = decision[i][j]
                norm[i][j] = (l / max_u, m / max_u, u / max_u)
        else:
            # Note: safe_pos clamps a negative minimum to EPS, so one negative
            # value on a cost criterion (LCA credits can be negative) collapses
            # that criterion: the negative alternative normalises to 1 and all
            # others to about 0. Open question.
            min_l = min(decision[i][j][0] for i in range(n_alt))
            min_l = safe_pos(min_l)
            for i in range(n_alt):
                l, m, u = decision[i][j]
                l = safe_pos(l)
                m = safe_pos(m)
                u = safe_pos(u)
                norm[i][j] = (min_l / u, min_l / m, min_l / l)

    return norm


def compute_bonferroni(norm_matrix, weights, phi1=1.0, phi2=1.0):
    """The two Bonferroni aggregations of the normalised matrix, per alternative.

        Both run over every ORDERED PAIR of distinct criteria (i, j), weighted by
        term = wi*wj / (1 - wi):

            SCoB  the sum form:     sum(term * gi^phi1 * gj^phi2) ^ (1/(phi1+phi2))
            PCoB  the product form: accumulated in LOGS, then exponentiated and
                                    divided by (phi1 + phi2) - the logs are what
                                    keep a product of ~110 terms from underflowing

        phi1 and phi2 are the Bonferroni exponents; at the default 1.0/1.0 the two
        criteria in a pair count equally. Each weight is clamped into
        [EPS, 1 - EPS] so that the 1 - wi denominator cannot vanish. Returns the
        two lists of (l, m, u) triples, one entry per alternative.
        """
    weights = safe_normalize_to_1(pd.Series(weights).astype(float).values)

    n_alt = len(norm_matrix)
    n_crit = len(weights)

    if n_crit < 2:
        raise ValueError("At least two criteria are required for fuzzy Bonferroni CoCoSo.")

    scob = []
    pcob = []
    exp_term = 1.0 / safe_pos(phi1 + phi2)

    for a in range(n_alt):
        s_l = 0.0
        s_m = 0.0
        s_u = 0.0

        log_p_l = 0.0
        log_p_m = 0.0
        log_p_u = 0.0

        for i in range(n_crit):
            wi = min(max(weights[i], EPS), 1.0 - EPS)
            denom = 1.0 - wi

            for j in range(n_crit):
                if i == j:
                    continue

                wj = weights[j]
                term = (wi * wj) / denom

                gi_l, gi_m, gi_u = norm_matrix[a][i]
                gj_l, gj_m, gj_u = norm_matrix[a][j]

                # SCoB
                s_l += term * (safe_pos(gi_l) ** phi1) * (safe_pos(gj_l) ** phi2)
                s_m += term * (safe_pos(gi_m) ** phi1) * (safe_pos(gj_m) ** phi2)
                s_u += term * (safe_pos(gi_u) ** phi1) * (safe_pos(gj_u) ** phi2)

                # PCoB
                base_l = safe_pos(phi1 * gi_l + phi2 * gj_l)
                base_m = safe_pos(phi1 * gi_m + phi2 * gj_m)
                base_u = safe_pos(phi1 * gi_u + phi2 * gj_u)

                log_p_l += term * math.log(base_l)
                log_p_m += term * math.log(base_m)
                log_p_u += term * math.log(base_u)

        s_l = safe_pos(s_l) ** exp_term
        s_m = safe_pos(s_m) ** exp_term
        s_u = safe_pos(s_u) ** exp_term
        scob.append((s_l, s_m, s_u))

        p_l = math.exp(log_p_l) / safe_pos(phi1 + phi2)
        p_m = math.exp(log_p_m) / safe_pos(phi1 + phi2)
        p_u = math.exp(log_p_u) / safe_pos(phi1 + phi2)
        pcob.append((p_l, p_m, p_u))

    return scob, pcob


def relative_significance(scob, pcob, pi=0.5):
    """
    Revised version:
    - First defuzzify SCoB and PCoB using the SAME TFN formula
      Crisp = (l + 4m + u) / 6
    - Then compute Kia, Kib, Kic from the crisp values
      (Excel-style ranking logic).
    """
    scob_crisp = np.array([defuzz_tfn(s) for s in scob], dtype=float)
    pcob_crisp = np.array([defuzz_tfn(p) for p in pcob], dtype=float)

    sum_scob = safe_pos(np.sum(scob_crisp))
    sum_pcob = safe_pos(np.sum(pcob_crisp))

    min_scob = safe_pos(np.min(scob_crisp))
    min_pcob = safe_pos(np.min(pcob_crisp))

    max_scob = safe_pos(np.max(scob_crisp))
    max_pcob = safe_pos(np.max(pcob_crisp))

    # Kia
    kia = (scob_crisp + pcob_crisp) / safe_pos(sum_scob + sum_pcob)

    # Kib
    kib = (scob_crisp / min_scob) + (pcob_crisp / min_pcob)

    # Kic
    kic = (pi * scob_crisp + (1.0 - pi) * pcob_crisp) / safe_pos(
        pi * max_scob + (1.0 - pi) * max_pcob
    )

    meta = {
        "sum_Crisp_SCoB": sum_scob,
        "sum_Crisp_PCoB": sum_pcob,
        "min_Crisp_SCoB": min_scob,
        "min_Crisp_PCoB": min_pcob,
        "max_Crisp_SCoB": max_scob,
        "max_Crisp_PCoB": max_pcob,
    }

    return scob_crisp, pcob_crisp, kia, kib, kic, meta


def final_scores_bonferroni(
    scob,
    pcob,
    scob_crisp,
    pcob_crisp,
    kia,
    kib,
    kic,
    alternative_names=None,
):
    """Combine Kia, Kib and Kic into the final score K, and rank the alternatives.

        K is CoCoSo's usual combination - the geometric mean of the three appraisal
        scores plus their arithmetic mean:

            K = (Kia * Kib * Kic)^(1/3) + (Kia + Kib + Kic)/3

        Returns one row per alternative carrying the fuzzy SCoB/PCoB triples, their
        crisp values, the three K scores, K itself and the rank, sorted best first
        and ties broken by alternative name.

        The frame carries K twice, as 'K' and as 'Crisp' (same number; 'Crisp'
        is kept for compatibility with existing outputs).
        """
    n_alt = len(kia)
    if alternative_names is None:
        alternative_names = [f"A{i+1}" for i in range(n_alt)]

    rows = []
    for i in range(n_alt):
        K = (
            (safe_pos(kia[i]) * safe_pos(kib[i]) * safe_pos(kic[i])) ** (1.0 / 3.0)
            + (kia[i] + kib[i] + kic[i]) / 3.0
        )

        rows.append([
            alternative_names[i],

            scob[i][0], scob[i][1], scob[i][2],
            pcob[i][0], pcob[i][1], pcob[i][2],

            scob_crisp[i],
            pcob_crisp[i],

            kia[i],
            kib[i],
            kic[i],

            K,      # Excel-style final score
            K,      # keep "Crisp" for compatibility with your existing print statement
        ])

    df = pd.DataFrame(
        rows,
        columns=[
            "Alternative",
            "SCoB_l", "SCoB_m", "SCoB_u",
            "PCoB_l", "PCoB_m", "PCoB_u",
            "Crisp_SCoB", "Crisp_PCoB",
            "Kia", "Kib", "Kic",
            "K", "Crisp",
        ],
    )

    df["Rank"] = df["K"].rank(ascending=False, method="min").astype(int)
    return df.sort_values(["K", "Alternative"], ascending=[False, True]).reset_index(drop=True)


def cocoso_bonferroni_from_app(fuzzy_df, types_bc, final_weights, phi1=1.0, phi2=1.0, pi=0.5):
    """Fuzzy CoCoSo-Bonferroni end to end, from the fuzzy frame to the ranking.

        Nests the frame, normalises it by criterion direction, runs both Bonferroni
        aggregations under `final_weights`, defuzzifies and forms Kia/Kib/Kic, then
        scores and ranks. Returns the ranking frame, a metadata dict and six
        working frames (normalised matrix, SCoB, PCoB, and the three K vectors) so
        that every step is reportable.

        The criterion names are recovered from the fuzzy frame's own '_l' columns,
        which is why that naming convention is load-bearing rather than cosmetic.
        """
    criteria = [c[:-2] for c in fuzzy_df.columns if c.endswith("_l")]
    alternatives = fuzzy_df.index.astype(str).tolist()

    decision = fuzzy_df_to_nested_matrix(fuzzy_df, criteria, alternatives)
    norm_matrix = normalize_cocoso_bonferroni(decision, types_bc)
    weights = pd.Series(final_weights, index=criteria).astype(float)

    scob, pcob = compute_bonferroni(norm_matrix, weights, phi1=phi1, phi2=phi2)

    scob_crisp, pcob_crisp, kia, kib, kic, crisp_meta = relative_significance(
        scob, pcob, pi=pi
    )

    ranking_df = final_scores_bonferroni(
        scob=scob,
        pcob=pcob,
        scob_crisp=scob_crisp,
        pcob_crisp=pcob_crisp,
        kia=kia,
        kib=kib,
        kic=kic,
        alternative_names=alternatives,
    )

    norm_rows = []
    for i, alt in enumerate(alternatives):
        row = {"Alternative": alt}
        for j, c in enumerate(criteria):
            row[f"{c}_l"] = norm_matrix[i][j][0]
            row[f"{c}_m"] = norm_matrix[i][j][1]
            row[f"{c}_u"] = norm_matrix[i][j][2]
        norm_rows.append(row)
    norm_df = pd.DataFrame(norm_rows).set_index("Alternative")

    scob_df = pd.DataFrame(
        scob,
        columns=["SCoB_l", "SCoB_m", "SCoB_u"],
        index=alternatives,
    )
    scob_df["Crisp_SCoB"] = scob_crisp

    pcob_df = pd.DataFrame(
        pcob,
        columns=["PCoB_l", "PCoB_m", "PCoB_u"],
        index=alternatives,
    )
    pcob_df["Crisp_PCoB"] = pcob_crisp

    psi_a_df = pd.DataFrame({"Kia": kia}, index=alternatives)
    psi_b_df = pd.DataFrame({"Kib": kib}, index=alternatives)
    psi_c_df = pd.DataFrame({"Kic": kic}, index=alternatives)

    cocoso_meta = {
        "phi1": phi1,
        "phi2": phi2,
        "pi": pi,
        **crisp_meta,
    }

    return ranking_df, cocoso_meta, norm_df, scob_df, pcob_df, psi_a_df, psi_b_df, psi_c_df
