"""
integrated.py - the pipeline: one decision matrix in, one ranked answer out.

    load_decision_matrix     read scenario_summary.xlsx
    derive_thresholds        AL / WL / IT, derived from that matrix
    run_integrated_analysis  weights -> ranking
    analyse                  the two above wired to config.py's settings
    short_results            the three-sheet summary
    export_results_to_excel  write a dict of frames to one workbook

The MCDA does not touch Brightway: scenario_summary.xlsx is assembled from
several completed scenario runs, one row per alternative.

The stages run in this order:

    1. parse and validate the decision matrix
    2. objective weights   (weights.py) - needs the matrix and AL / WL / IT
    3. subjective weights  (opa.py)     - needs only the expert panel
    4. final weights       - the two fused by EWCS
    5. fuzzify the matrix  (fuzzy.py)   - needs epsilon
    6. rank                (cocoso.py)  - needs the fuzzy matrix and step 4

Steps 2 and 3 are independent of each other; everything else is a chain.
"""

from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from . import config
from .cocoso import cocoso_bonferroni_from_app
from .fuzzy import build_fuzzy_df_from_crisp_percent, sanitize_fuzzy_df
from .opa import run_fuzzy_opa
from .utils import (check_missing_array, check_missing_df, parse_number,
                    to_bc_label, validate_expert_weights,
                    validate_linguistic_df)
from .weights import (ewcs_fusion, mitara_stage1_independent_weights,
                      stage2_dependent_weights_corr)


def run_integrated_analysis(
    D_df: pd.DataFrame,
    types: List[str],
    AL,
    IT,
    linguistic_df: pd.DataFrame,
    expert_weights: List[float],
    fuzzy_df: Optional[pd.DataFrame] = None,
    epsilon: float = 0.10,
    phi1: float = 1.0,
    phi2: float = 1.0,
    pi_coef: float = 0.5,
    # WL is the worst level used by stage II; it must be given (None raises).
    WL=None,
) -> Dict[str, pd.DataFrame]:
    """The whole MCDA, from the decision matrix to the ranked alternatives.

        Three weighting stages feed one ranking stage:

            objective   m-ITARA stage I (spread) + stage II (redundancy), fused by
                        EWCS -> how much each criterion separates the alternatives
            subjective  fuzzy OPA on the expert panel's linguistic judgements
                        -> how much each criterion matters to the experts
            final       the two fused by EWCS again -> the weights actually used
            ranking     fuzzy CoCoSo-Bonferroni on the fuzzified decision matrix

        Parameters
        ----------
        D_df : pandas.DataFrame
            Decision matrix, alternatives x criteria; formatted strings such as
            '7,400,000.00' are parsed.
        types : list of str
            'B' (benefit) or 'C' (cost) per criterion.
        AL, IT, WL : array-like
            m-ITARA aspiration level, indifference threshold and worst level,
            one value per criterion (see derive_thresholds).
        linguistic_df : pandas.DataFrame
            Expert judgements, criteria x experts.
        expert_weights : list of float
            One weight per expert, summing to 1.
        fuzzy_df : pandas.DataFrame, optional
            Fuzzy decision matrix; built from D_df at +/- `epsilon` if None.
        epsilon, phi1, phi2, pi_coef : float
            Fuzzification half-width and CoCoSo-Bonferroni coefficients.

        Returns
        -------
        dict
            27 DataFrames - every intermediate as well as the answer - keyed by
            the sheet name each is exported under.

        Raises
        ------
        ValueError
            If inputs are missing or inconsistent, or the expert panel does not
            name every criterion of the decision matrix.
        """
    D_df = D_df.copy().apply(lambda col: col.map(parse_number))
    check_missing_df(D_df, "Decision matrix")

    criteria = D_df.columns.astype(str).tolist()
    alternatives = D_df.index.astype(str).tolist()

    types = [to_bc_label(t) for t in types]
    if len(types) != len(criteria):
        raise ValueError("Length of types must match the number of criteria.")

    AL = check_missing_array(AL, "AL")
    IT = check_missing_array(IT, "IT")
    WL = check_missing_array(WL, "WL")

    linguistic_df = validate_linguistic_df(linguistic_df.copy())
    if list(linguistic_df.index.astype(str)) != criteria:
        # Put the panel into the matrix's criterion order.
        panel_criteria = list(linguistic_df.index.astype(str))
        linguistic_df = linguistic_df.reindex(criteria)

        # A row that is all NaN after the reindex is a criterion the panel
        # does not name; fail rather than let it default to 'E'.
        unnamed = linguistic_df.index[linguistic_df.isna().all(axis=1)]
        if len(unnamed):
            raise ValueError(
                f"The expert panel does not name {len(unnamed)} of the "
                f"{len(criteria)} criteria in the decision matrix: "
                f"{list(unnamed.astype(str))}. The panel's own criteria are "
                f"{panel_criteria}. Judgements for the missing ones would "
                f"otherwise default to 'E' (Equal) and the run would look "
                f"normal.")

    expert_weights = validate_expert_weights(linguistic_df, expert_weights)

    D_num = D_df.to_numpy(dtype=float)
    sigma = D_num.std(axis=0, ddof=0)
    # Reported in ObjectiveSummary as a sanity check. With the derived
    # thresholds (IT = 0.5 * sigma) it only fails for a constant column.
    it_ok = IT < sigma

    stage1 = mitara_stage1_independent_weights(D_num, AL, IT)
    stage2 = stage2_dependent_weights_corr(D_num, types, AL, WL)
    stage3_obj = ewcs_fusion(stage1["w1"], stage2["w2"])

    objective_summary = pd.DataFrame({
        "Criterion": criteria,
        "Type": types,
        "sigma": sigma,
        "IT": IT,
        "IT<sigma": it_ok,
        "w1_independent": stage1["w1"],
        "w2_dependent": stage2["w2"],
        "objective_weight": stage3_obj["wagg"],
    })
    objective_summary["Objective_Rank"] = objective_summary["objective_weight"].rank(ascending=False, method="dense").astype(int)

    opa_result = run_fuzzy_opa(criteria, linguistic_df, expert_weights.tolist())
    subjective_crisp = opa_result["weights_df"]["Defuzzified"].to_numpy(dtype=float)

    final_stage = ewcs_fusion(stage3_obj["wagg"], subjective_crisp)
    final_weights = pd.Series(final_stage["wagg"], index=criteria, name="final_weight")

    final_weight_df = pd.DataFrame({
        "Criterion": criteria,
        "Objective_weight": stage3_obj["wagg"],
        "Subjective_weight": subjective_crisp,
        "Final_weight": final_weights.values,
    })
    final_weight_df["Rank"] = final_weight_df["Final_weight"].rank(ascending=False, method="min").astype(int)
    final_weight_df = final_weight_df.sort_values("Final_weight", ascending=False).reset_index(drop=True)

    if fuzzy_df is None:
        fuzzy_df = build_fuzzy_df_from_crisp_percent(D_df.astype(float), epsilon=epsilon)
    else:
        fuzzy_df = sanitize_fuzzy_df(fuzzy_df, criteria=criteria, alternatives=alternatives)

    ranking_df, cocoso_meta, norm_df, scob_df, pcob_df, psi_a_df, psi_b_df, psi_c_df = cocoso_bonferroni_from_app(
        fuzzy_df=fuzzy_df,
        types_bc=types,
        final_weights=final_weights.values,
        phi1=float(phi1),
        phi2=float(phi2),
        pi=float(pi_coef),
    )

    return {
        "DecisionMatrix": D_df,
        "ObjectiveSummary": objective_summary,
        "StageI_A": pd.DataFrame(stage1["A"], index=alternatives + ["AL"], columns=criteria),
        "StageI_beta": pd.DataFrame(stage1["beta"], columns=criteria),
        "StageI_gamma": pd.DataFrame(stage1["gamma"], columns=criteria),
        "StageI_delta": pd.DataFrame(stage1["delta"], columns=criteria),
        "StageI_NIT": pd.DataFrame({"NIT": stage1["NIT"]}, index=criteria),
        "StageI_nu": pd.DataFrame({"nu": stage1["nu"]}, index=criteria),
        "StageII_X": pd.DataFrame(stage2["X"], index=alternatives, columns=criteria),
        "StageII_R": pd.DataFrame(stage2["R"], index=criteria, columns=criteria),
        "StageII_phi_w2": pd.DataFrame({"phi": stage2["phi"], "w2": stage2["w2"]}, index=criteria),
        "Objective_EWCS": pd.DataFrame({"p_raw": stage3_obj["p_raw"], "p_star": stage3_obj["p_star"]}, index=["w1", "w2"]),
        "OPA_Theta": opa_result["theta_df"],
        "OPA_Coefficients": opa_result["coeff_df"],
        "OPA_Weights": opa_result["weights_df"],
        "OPA_Ranked": opa_result["ranked_df"],
        "Final_Weights": final_weight_df,
        "Final_EWCS": pd.DataFrame({"p_raw": final_stage["p_raw"], "p_star": final_stage["p_star"]}, index=["objective", "subjective"]),
        "Fuzzy_Input": fuzzy_df,
        "Bonferroni_Normalized": norm_df,
        "SCoB": scob_df,
        "PCoB": pcob_df,
        "psi_a": psi_a_df,
        "psi_b": psi_b_df,
        "psi_c": psi_c_df,
        "Ranking": ranking_df,
        "CoCoSo_Meta": pd.DataFrame([cocoso_meta]),
    }


def export_results_to_excel(results: Dict[str, pd.DataFrame], filepath: str):
    """Write every DataFrame in `results` to one sheet of one .xlsx file.

        The dict key becomes the sheet name (truncated to 31 characters) and the
        index is written; non-DataFrame entries are skipped. No styling.
        """
    with pd.ExcelWriter(filepath, engine="openpyxl") as writer:
        for name, df in results.items():
            if isinstance(df, pd.DataFrame):
                df.to_excel(writer, sheet_name=name[:31], index=True)


def load_decision_matrix(path="scenario_summary.xlsx"):
    """Read the decision matrix: one row per alternative, one column per criterion.

    The first column holds the alternative names. The column order is what
    config.CRITERION_TYPES and config.EXPERT_JUDGEMENTS are aligned to. The
    workbook is assembled by hand from several completed pLCA runs;
    scenario_summary_blank.xlsx is the empty template.

    Parameters
    ----------
    path : str, default 'scenario_summary.xlsx'

    Returns
    -------
    pandas.DataFrame
    """
    return pd.read_excel(path, index_col=0)


def derive_thresholds(D_df):
    """The m-ITARA threshold vectors AL, WL and IT, derived from the matrix itself.

    Each is a fixed multiple of a column statistic:

        AL  aspiration level        0.50 x the column MINIMUM
        WL  worst level             1.25 x the column MAXIMUM
        IT  indifference threshold  0.50 x the column population std (ddof=0)

    AL is appended to the matrix as a notional ideal alternative in stage I;
    IT is the gap below which two alternatives count as indistinguishable on
    a criterion; AL and WL set stage II's rescaling.

    Note: every criterion is assumed to be a COST (lower is better), and
    nothing checks it. For a benefit criterion AL and WL would be inverted,
    which would silently weight the wrong things (the Excel implementation
    warns: "For cost criteria, set AL lower than WL").

    Parameters
    ----------
    D_df : pandas.DataFrame
        Decision matrix; formatted strings are parsed as in
        run_integrated_analysis.

    Returns
    -------
    pandas.DataFrame
        Indexed by criterion: columns min, max, std_pop, AL, WL, IT.
    """
    # Parse exactly as run_integrated_analysis does.
    D_df = D_df.copy().apply(lambda col: col.map(parse_number))

    # Calculate AL as 0.5 times the minimum value of each column in D_df
    AL = np.array([0.5 * D_df[col].min() for col in D_df.columns], dtype=float)

    # Calculate WL as 1.25 times the maximum value of each column in D_df
    WL = np.array([1.25 * D_df[col].max() for col in D_df.columns], dtype=float)

    # Calculate IT as 0.5 times the population standard deviation of each column in D_df
    IT = np.array([0.5 * D_df[col].std(ddof=0) for col in D_df.columns], dtype=float)
    # The statistics are included for reading the derivation.
    return pd.DataFrame({
        "min": D_df.min(),
        "max": D_df.max(),
        "std_pop": D_df.std(ddof=0),
        "AL": AL,
        "WL": WL,
        "IT": IT,
    }, index=D_df.columns)


def analyse(D_df, thresholds=None):
    """Run the whole MCDA on one decision matrix, using config.py's settings.

    Criterion types, expert panel, expert weights and coefficients come from
    config.py; the thresholds from derive_thresholds unless given.

    Parameters
    ----------
    D_df : pandas.DataFrame
        Decision matrix.
    thresholds : pandas.DataFrame, optional
        Output of derive_thresholds.

    Returns
    -------
    dict
        As run_integrated_analysis.
    """
    if thresholds is None:
        thresholds = derive_thresholds(D_df)

    return run_integrated_analysis(
        D_df=D_df,
        types=config.CRITERION_TYPES,
        AL=thresholds["AL"].to_numpy(dtype=float),
        IT=thresholds["IT"].to_numpy(dtype=float),
        linguistic_df=config.linguistic_frame(D_df.columns),
        expert_weights=config.EXPERT_WEIGHTS,
        fuzzy_df=None,
        epsilon=config.EPSILON,
        phi1=config.PHI1,
        phi2=config.PHI2,
        pi_coef=config.PI_COEF,
        WL=thresholds["WL"].to_numpy(dtype=float),
    )


def short_results(results):
    """The three sheets worth reporting: decision matrix, final weights, ranking.

    This is what integrated_mcda_results_short.xlsx holds; the full workbook
    keeps every intermediate. Note the sheet name 'Decision Matrix' (with a
    space) against 'DecisionMatrix' in the full workbook.

    Parameters
    ----------
    results : dict
        Output of analyse().

    Returns
    -------
    dict
    """
    return {
        "Decision Matrix": results["DecisionMatrix"],
        "Final_Weights": results["Final_Weights"],
        "Ranking": results["Ranking"],
    }
