"""
config.py - the MCDA registry: the fuzzy scale, the expert panel, the coefficients.

Pure data, in the same spirit as plca/config.py. Everything a study would
change between one run and the next is here, named, with the reason it has
the value it has:

    LINGUISTIC_SCALE    the nine-point word-to-number scale the experts use
    CRITERION_TYPES     which criteria are costs and which are benefits
    EXPERT_JUDGEMENTS   the panel's answers - 7 experts x 11 criteria
    EXPERT_WEIGHTS      how much each expert counts
    EPSILON             the fuzzification half-width
    PHI1, PHI2, PI_COEF the CoCoSo-Bonferroni coefficients

CHANGING THE PANEL OR THE CRITERIA. EXPERT_JUDGEMENTS is keyed by expert and
each list runs DOWN the criteria, in the order the decision matrix's columns
come in - so the eleven entries of "E1" are that expert's rating of criteria 1
to 11. A study with a different number of criteria has to change
CRITERION_TYPES and all seven lists together; run_integrated_analysis raises if
they disagree with the workbook, so a half-edit fails loudly rather than
ranking the wrong thing.
"""

import pandas as pd


# --- numerical floor -------------------------------------------------------
# The smallest number the tool will divide by, raise to a power, or take the
# log of. Everything downstream works in normalised ratios, so a true zero is
# reachable and would become an inf or a NaN that survives all the way to the
# ranking without raising. utils.safe_pos and cocoso.compute_bonferroni are
# where it is applied.
EPS = 1e-12


# --- the triangular fuzzy scale -------------------------------------------
# The nine linguistic labels an expert may use, each as a triangular fuzzy
# number (lower, modal, upper) on a 1-10 scale. The steps overlap by one unit
# on each side, which is what makes the scale fuzzy rather than ordinal: "High"
# and "Very High" are not disjoint judgements.
#
#   AL Absolutely Low   VL Very Low    L  Low         ML Medium Low
#   E  Equal            MH Medium High H  High        VH Very High
#   AH Absolutely High
#
# 'E' is the neutral middle and is what utils.validate_linguistic_df
# substitutes for any cell it does not recognise.
LINGUISTIC_SCALE = {
    "AL": (1.00, 1.50, 2.50),
    "VL": (1.50, 2.50, 3.50),
    "L":  (2.50, 3.50, 4.50),
    "ML": (3.50, 4.50, 5.50),
    "E":  (4.50, 5.50, 6.50),
    "MH": (5.50, 6.50, 7.50),
    "H":  (6.50, 7.50, 8.50),
    "VH": (7.50, 8.50, 9.50),
    "AH": (8.50, 9.00, 10.00),
}

# The nine labels as a list, which is what validate_linguistic_df tests against.
LINGUISTIC_OPTIONS = list(LINGUISTIC_SCALE.keys())


# --- the criteria ----------------------------------------------------------
# One 'B' (benefit, larger is better) or 'C' (cost, smaller is better) per
# column of scenario_summary.xlsx, in column order.
#
# Every criterion is a COST in the current dataset: the eleven columns are LCA
# impact figures, and less impact is better in all of them. If a benefit
# criterion is ever added - a comfort score, a self-sufficiency fraction - this
# is the list that has to say so, and the direction reaches the model in two
# places, weights.stage2_dependent_weights_corr and
# cocoso.normalize_cocoso_bonferroni.
#
# The list must match the workbook's column count; run_integrated_analysis
# raises if it does not.
# Note: integrated.derive_thresholds takes the aspiration level from each
# column's minimum and the worst level from its maximum, which is only right
# for cost criteria, and it does not consult this list. Changing a 'C' to a
# 'B' is therefore not enough to add a benefit criterion.
CRITERION_TYPES = ["C"] * 11


# --- the expert panel ------------------------------------------------------
# Seven experts, each rating all eleven criteria on LINGUISTIC_SCALE. Each
# list runs DOWN the criteria in the decision matrix's own column order, so
# EXPERT_JUDGEMENTS["E1"][0] is expert 1's rating of the first criterion.
#
# These are the panel's actual answers and are the only subjective input to the
# whole tool - opa.py turns them into the subjective half of the weights, and
# nothing else reads them.
EXPERT_JUDGEMENTS = {
    "E1":  ["ML", "AH", "AH", "AH", "ML", "VH", "VH", "AH", "VH", "AH", "AH"],
    "E2":  ["MH", "VH", "MH", "MH", "MH", "H",  "VH", "H",  "H",  "H",  "MH"],
    "E3":  ["VH", "VH", "L",  "L",  "L",  "E",  "AH", "AH", "E",  "E",  "E" ],
    "E4":  ["L",  "VH", "H",  "ML", "E",  "H",  "VH", "VH", "AH", "VH", "H" ],
    "E5":  ["AL", "AH", "L",  "L",  "L",  "VL", "H",  "ML", "L",  "H",  "H" ],
    "E6":  ["H",  "AH", "VH", "H",  "H",  "E",  "H",  "VH", "H",  "H",  "H" ],
    "E7":  ["H",  "VH", "ML", "E",  "ML", "H",  "VH", "H",  "H",  "ML", "H" ],
}

# How much each expert's judgement counts. Equal shares, one seventh each -
# there is no separate weighting scheme for this panel. The list must be as
# long as EXPERT_JUDGEMENTS has keys and must sum to 1;
# utils.validate_expert_weights checks both.
EXPERT_WEIGHTS = [1/7] * 7


# --- analysis coefficients -------------------------------------------------
# EPSILON - the fuzzification half-width. The decision matrix is crisp, so each
# value x is widened to the triangular fuzzy number (0.9x, x, 1.1x). This is a
# STATED uncertainty, not a measured one: it asserts that every LCA figure is
# good to about +/- 10%. It is the only place uncertainty enters the MCDA, and
# every ranking depends on it.
EPSILON = 0.10

# PHI1, PHI2 - the Bonferroni exponents. They set how the two members of each
# criterion pair are balanced in cocoso.compute_bonferroni; at 1.0 and 1.0 the
# pair counts its two criteria equally, which is the usual choice.
PHI1 = 1.0
PHI2 = 1.0

# PI_COEF - the balance between the sum form (SCoB) and the product form (PCoB)
# in CoCoSo's third appraisal score Kic. At 0.5 the two count equally.
PI_COEF = 0.5


def linguistic_frame(criteria):
    """The expert judgement matrix as a DataFrame indexed by criterion name.

    Parameters
    ----------
    criteria : sequence of str
        Criterion names, normally D_df.columns, in column order.

    Returns
    -------
    pandas.DataFrame
        Criteria x experts, linguistic labels.

    Raises
    ------
    ValueError
        If an expert does not have one judgement per criterion.
    """
    criteria = list(criteria)
    for expert, answers in EXPERT_JUDGEMENTS.items():
        if len(answers) != len(criteria):
            raise ValueError(
                "Expert %s has %d judgements but there are %d criteria (%s). "
                "EXPERT_JUDGEMENTS and the decision matrix's columns must agree."
                % (expert, len(answers), len(criteria), ", ".join(map(str, criteria))))
    return pd.DataFrame(EXPERT_JUDGEMENTS, index=criteria)
