"""
fuzzy.py - turning the crisp decision matrix into a fuzzy one, and reshaping it.

The ranking stage (cocoso.py) works on triangular fuzzy numbers, but the
decision matrix that comes out of the LCA runs is crisp: one number per
(alternative, criterion). These three functions bridge that gap.

    build_fuzzy_df_from_crisp_percent   crisp x -> (x*(1-e), x, x*(1+e))
    sanitize_fuzzy_df                   an already-fuzzy frame, made valid
    fuzzy_df_to_nested_matrix           wide frame -> [alt][crit] = (l, m, u)

The epsilon widening is a STATED UNCERTAINTY, not a measured one: it says
"treat every LCA figure as good to +/- 10%" and nothing more. It is the only
place uncertainty enters the MCDA, and changing epsilon changes every ranking,
so it is a modelling choice and lives in config.py as EPSILON.

The wide layout - three columns '<criterion>_l', '_m', '_u' per criterion - is
a convention two other files depend on: cocoso_bonferroni_from_app recovers
the criterion names from the '_l' columns, and sanitize_fuzzy_df addresses the
triples by those suffixes.
"""

from typing import List

import numpy as np
import pandas as pd


def build_fuzzy_df_from_crisp_percent(raw_df: pd.DataFrame, epsilon: float = 0.10) -> pd.DataFrame:
    """Widen each crisp value into a triangular fuzzy number of +/- epsilon.

        l = x*(1-epsilon), m = x, u = x*(1+epsilon), then the triple is sorted so
        that a NEGATIVE x - for which the multiplication reverses l and u - still
        yields a valid TFN. This is what stands in for a fuzzy decision matrix when
        the caller supplies only crisp figures, which is the current dataset's case.

        Returns a frame with three columns '<criterion>_l/_m/_u' per input column,
        keeping the input's index.
        """
    cols = []
    rows = []

    for c in raw_df.columns:
        cols.extend([f"{c}_l", f"{c}_m", f"{c}_u"])

    for _, r in raw_df.iterrows():
        row_vals = []
        for c in raw_df.columns:
            x = float(r[c])
            l = x * (1.0 - epsilon)
            m = x
            u = x * (1.0 + epsilon)
            trip = sorted([l, m, u])
            row_vals.extend(trip)
        rows.append(row_vals)

    return pd.DataFrame(rows, index=raw_df.index, columns=cols)


def sanitize_fuzzy_df(fuzzy_df: pd.DataFrame, criteria: List[str], alternatives: List[str]) -> pd.DataFrame:
    """Sort each criterion's (l, m, u) triple and reindex onto `alternatives`.

        Used when the caller supplies a fuzzy matrix directly rather than having it
        built from crisp values: it guarantees l <= m <= u, which everything
        downstream assumes, and puts the rows into the decision matrix's order.
        """
    out = fuzzy_df.copy().astype(float)
    for c in criteria:
        trip = out[[f"{c}_l", f"{c}_m", f"{c}_u"]].values
        trip = np.sort(trip, axis=1)
        out[[f"{c}_l", f"{c}_m", f"{c}_u"]] = trip
    return out.reindex(index=alternatives)


def fuzzy_df_to_nested_matrix(fuzzy_df: pd.DataFrame, criteria: List[str], alternatives: List[str]):
    """Turn the wide fuzzy frame into [alternative][criterion] = (l, m, u).

        The CoCoSo-Bonferroni code indexes by position, not by label, so this is
        where the column names stop mattering and the row/column order is fixed.
        """
    matrix = []
    for alt in alternatives:
        row = []
        for c in criteria:
            trip = (
                float(fuzzy_df.loc[alt, f"{c}_l"]),
                float(fuzzy_df.loc[alt, f"{c}_m"]),
                float(fuzzy_df.loc[alt, f"{c}_u"]),
            )
            row.append(tuple(sorted(trip)))
        matrix.append(row)
    return matrix
