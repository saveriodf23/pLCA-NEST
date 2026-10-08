"""
utils.py - the small shared helpers every stage of the MCDA leans on.

Ten functions, in three groups:

    reading      parse_number, ensure_2d          get caller input into the
                                                  shape and dtype the maths
                                                  below expects
    arithmetic   safe_normalize_to_1, safe_pos,   the two guards and the one
                 defuzz_tfn                       defuzzifier used everywhere
    validating   to_bc_label, validate_linguistic_df, check_missing_df,
                 check_missing_array, validate_expert_weights

Nothing here is specific to m-ITARA, to OPA or to CoCoSo; each of those
modules imports from this one and not the other way round.

The guards matter more than they look. This tool divides by, raises to powers
of, and takes logarithms of numbers that are normalised ratios, so a zero
anywhere is an inf or a NaN that reaches the final ranking without ever
raising. safe_pos and safe_normalize_to_1 are where that is stopped.
"""

import re
from typing import List, Tuple

import numpy as np
import pandas as pd

from .config import EPS, LINGUISTIC_OPTIONS


def parse_number(x):
    """Convert strings like '7,400,000.00' to float; keep numerics as-is."""
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return np.nan
    if isinstance(x, (int, float, np.number)):
        return float(x)
    s = str(x).strip()
    if s == "":
        return np.nan
    s = s.replace(",", "")
    if re.match(r"^\(\s*[-+]?\d+(\.\d+)?\s*\)$", s):
        s = "-" + s.strip("()").strip()
    return float(s)


def safe_normalize_to_1(v: np.ndarray) -> np.ndarray:
    """Scale a vector so that it sums to 1.

        A vector that sums to zero, to a negative, or to NaN comes back uniform
        (1/n in every position) rather than raising. Every weight vector in the
        tool passes through here, and a degenerate one must not stop the run.
        """
    v = np.asarray(v, dtype=float)
    s = np.nansum(v)
    if len(v) == 0:
        raise ValueError("Vector length cannot be zero.")
    if s <= 0 or np.isclose(s, 0.0) or np.isnan(s):
        return np.ones_like(v) / len(v)
    return v / s


def ensure_2d(a):
    """Return `a` as a 2-D float array, promoting a single row.

        The decision matrix is allowed to hold one alternative, which numpy would
        otherwise hand back as 1-D and break the (m, n) unpacking downstream.
        """
    a = np.asarray(a, dtype=float)
    if a.ndim == 1:
        return a.reshape(1, -1)
    return a


def safe_pos(x: float, eps: float = EPS) -> float:
    """Clamp x to at least `eps` (1e-12 by default).

        Used wherever a value is about to be divided by, raised to a power, or
        passed to log - the CoCoSo normalisation and both Bonferroni means do all
        three, and a zero there becomes an inf or a NaN that poisons the ranking.
        """
    return max(float(x), eps)


def defuzz_tfn(tfn: Tuple[float, float, float]) -> float:
    """Defuzzify a triangular fuzzy number (l, m, u) to one crisp value.

        The weighted-mean formula (l + 4m + u) / 6. This is the ONLY defuzzifier
        the tool uses - the OPA weights and the CoCoSo SCoB/PCoB scores all come
        through here - so changing it changes every reported number.
        """
    return (tfn[0] + 4 * tfn[1] + tfn[2]) / 6.0


def to_bc_label(x: str) -> str:
    """Normalise a criterion type to 'B' (benefit) or 'C' (cost).

        Benefit means larger is better, cost means smaller is better. Anything not
        recognisable as a benefit becomes a cost, which is the safe default for
        this tool: every criterion in the current dataset is a cost.
        """
    s = str(x).strip().upper()
    if s in {"B", "BENEFIT", "MAX"}:
        return "B"
    return "C"


def validate_linguistic_df(df: pd.DataFrame) -> pd.DataFrame:
    """Clean the expert judgement matrix: trim, upper-case, and default.

        Any cell that is not one of the nine labels in config.LINGUISTIC_SCALE is
        replaced by 'E', the neutral middle of the scale, rather than raising - a
        blank from one expert must not discard the other six. Returns a copy.
        """
    out = df.copy()
    for c in out.columns:
        out[c] = out[c].astype(str).str.strip().str.upper()
        out[c] = out[c].where(out[c].isin(LINGUISTIC_OPTIONS), "E")
    return out


def check_missing_df(df: pd.DataFrame, name: str):
    """Raise ValueError if any cell of `df` is blank or unparseable.

        `name` is quoted in the message so the caller can tell which input failed.
        """
    if df.isna().any().any():
        raise ValueError(f"{name} contains blank or invalid cells.")


def check_missing_array(arr, name: str):
    """Raise ValueError if any element of `arr` is NaN; return it as float.

        The AL and IT threshold vectors are checked with this before m-ITARA sees
        them, because a NaN there propagates silently into every weight.
        """
    arr = np.asarray(arr, dtype=float)
    if np.isnan(arr).any():
        raise ValueError(f"{name} contains blank or invalid values.")
    return arr


def validate_expert_weights(linguistic_df: pd.DataFrame, expert_weights: List[float]) -> np.ndarray:
    """Check the expert weight vector against the judgement matrix.

        One weight per expert column, none negative, and summing to 1 within 1e-8.
        Returns them as a flat float array. Raises with the offending figure in the
        message, since a panel reweighting is the easiest thing to get wrong here.
        """
    expert_weights = np.asarray(expert_weights, dtype=float).ravel()
    n_experts = linguistic_df.shape[1]

    if expert_weights.size != n_experts:
        raise ValueError(
            f"Number of expert weights ({expert_weights.size}) must equal the number of expert columns "
            f"in linguistic_df ({n_experts})."
        )

    if np.any(expert_weights < 0):
        raise ValueError("Expert weights must be non-negative.")

    if not np.isclose(expert_weights.sum(), 1.0, atol=1e-8):
        raise ValueError(
            f"Expert weights must sum to 1.0. Current sum = {expert_weights.sum():.10f}"
        )

    return expert_weights
