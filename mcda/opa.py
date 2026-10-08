"""
opa.py - the SUBJECTIVE criterion weights: triangular fuzzy OPA.

Where weights.py reads the decision matrix, this file reads the expert panel.
Each of the seven experts rates each of the criteria on the nine-point
linguistic scale in config.py; those words become triangular fuzzy numbers,
the seven judgements per criterion are aggregated into one, the criteria are
RANKED by the defuzzified result, and a linear programme turns that ranking
into weights.

OPA is an ORDINAL method: only the order of the criteria reaches the LP. Two
panels that disagree about how much criterion 2 beats criterion 7, but agree
that it does, produce the same weights.

THE ONE EXTERNAL SOLVER IN THE WHOLE TOOL. solve_fuzzy_opa calls CBC through
PuLP. pulp is imported defensively, so the rest of the module works on a
machine without it; solve_fuzzy_opa raises with an install instruction if it
is needed and missing.
"""

import numpy as np
import pandas as pd

try:
    import pulp
except Exception:
    pulp = None

from .config import LINGUISTIC_SCALE
from .utils import defuzz_tfn, validate_expert_weights, validate_linguistic_df


def trig_geom_component(values, weights):
    """Aggregate one component (l, m or u) of several TFNs, trigonometrically.

        The trigonometric geometric operator: each value's share of the total is
        mapped through cos(pi*ratio/2), the shares are combined as a weighted
        product, and arccos maps the result back. Returns 0.0 when the values sum
        to zero, which is the only degenerate case reachable from a valid scale.
        """
    if len(values) != len(weights):
        raise ValueError(
            f"Length mismatch in trigonometric aggregation: {len(values)} values but {len(weights)} weights."
        )

    s = sum(values)
    if s == 0:
        return 0.0

    prod = 1.0
    for v, w in zip(values, weights):
        ratio = v / s
        term = np.cos(np.pi * ratio / 2.0) ** w
        prod *= term

    prod = np.clip(prod, -1.0, 1.0)
    return s * (2.0 / np.pi) * np.arccos(prod)


def aggregate_tfn(tfn_list, weights):
    """Aggregate a list of triangular fuzzy numbers into one, under `weights`.

        Component by component - the lows with the lows, the mids with the mids,
        the highs with the highs - so the result is still a valid TFN. This is how
        seven experts' judgements on one criterion become a single fuzzy priority.
        """
    ls = [t[0] for t in tfn_list]
    ms = [t[1] for t in tfn_list]
    us = [t[2] for t in tfn_list]
    l = trig_geom_component(ls, weights)
    m = trig_geom_component(ms, weights)
    u = trig_geom_component(us, weights)
    return (l, m, u)


def solve_fuzzy_opa(coeff_list, n):
    """Solve the fuzzy Ordinal Priority Approach linear programme, with PuLP/CBC.

        `coeff_list` holds the n criteria's (l, m, u) coefficients ALREADY SORTED
        from most to least important; `n` is the criterion count. The programme
        maximises (psi_l + 2*psi_m + psi_u) / 4 - the defuzzified priority margin -
        subject to:

            w_l[i] <= w_m[i] <= w_u[i]          each weight is a valid TFN
            sum(w_l) = 0.8, sum(w_m) = 1.0,     the fuzzy normalisation the method
            sum(w_u) = 1.2                      prescribes
            coeff[a] * (w[a] - w[a+1]) >= psi   each rank beats the next by at
                                                least the margin
            coeff[n-1] * w[n-1] >= psi          and the last beats zero

        Returns (weights, psi) with every component clamped at 0, or (None, None)
        if CBC does not report status 1 (optimal).

        NOTE on precision: CBC returns its solution through a text file at about
        nine significant digits, so these weights are quantised, not float64-exact
        - sum(w_l) comes back as 0.800000002, not 0.8. Repeated solves on one
        machine agree exactly (measured: eight solves, worst difference 0.0), and
        the optimum was measured to be unique rather than degenerate, so a diff of
        two runs is exact. A different CBC build could still move a weight by
        about 1e-7 absolute, which is that solver's own feasibility tolerance.
        """
    if pulp is None:
        raise RuntimeError("PuLP is not installed. Install it first: pip install pulp")

    prob = pulp.LpProblem("Triangular_Fuzzy_OPA", pulp.LpMaximize)

    w_l = [pulp.LpVariable(f"w_l_{i}", lowBound=0) for i in range(n)]
    w_m = [pulp.LpVariable(f"w_m_{i}", lowBound=0) for i in range(n)]
    w_u = [pulp.LpVariable(f"w_u_{i}", lowBound=0) for i in range(n)]

    psi_l = pulp.LpVariable("psi_l", lowBound=0)
    psi_m = pulp.LpVariable("psi_m", lowBound=0)
    psi_u = pulp.LpVariable("psi_u", lowBound=0)

    prob += (psi_l + 2 * psi_m + psi_u) / 4.0

    for i in range(n):
        prob += w_l[i] <= w_m[i]
        prob += w_m[i] <= w_u[i]

    prob += pulp.lpSum(w_l) == 0.8
    prob += pulp.lpSum(w_m) == 1.0
    prob += pulp.lpSum(w_u) == 1.2

    for a in range(n - 1):
        prob += coeff_list[a][0] * (w_l[a] - w_u[a + 1]) >= psi_l
        prob += coeff_list[a][1] * (w_m[a] - w_m[a + 1]) >= psi_m
        prob += coeff_list[a][2] * (w_u[a] - w_l[a + 1]) >= psi_u

    prob += coeff_list[n - 1][0] * w_l[n - 1] >= psi_l
    prob += coeff_list[n - 1][1] * w_m[n - 1] >= psi_m
    prob += coeff_list[n - 1][2] * w_u[n - 1] >= psi_u

    status = prob.solve(pulp.PULP_CBC_CMD(msg=False))
    if status != 1:
        return None, None

    weights = []
    for i in range(n):
        weights.append((
            max(0, pulp.value(w_l[i])),
            max(0, pulp.value(w_m[i])),
            max(0, pulp.value(w_u[i])),
        ))

    psi = (
        max(0, pulp.value(psi_l)),
        max(0, pulp.value(psi_m)),
        max(0, pulp.value(psi_u)),
    )
    return weights, psi


def run_fuzzy_opa(criteria_names, linguistic_df, expert_weights):
    """Fuzzy OPA end to end - experts' words in, subjective criterion weights out.

        Four steps:

          1. every expert's linguistic label for a criterion becomes a TFN through
             config.LINGUISTIC_SCALE, and the seven are aggregated under the expert
             weights into one fuzzy priority theta per criterion;
          2. theta is defuzzified and the criteria are RANKED by it, because OPA is
             an ordinal method - the LP only ever sees the order;
          3. each theta becomes a coefficient triple relative to the smallest
             positive lower bound, so the coefficients are scale-free. A criterion
             with a non-positive component is given (0, 0, 0), which drops it out
             of the margin constraints rather than making the LP infeasible;
          4. the LP is solved on the sorted coefficients and the weights are put
             back into the caller's criterion order.

        Returns a dict of every intermediate plus four display frames: theta_df,
        coeff_df, weights_df (in the caller's order) and ranked_df (in rank order).
        """
    n = len(criteria_names)
    linguistic_df = validate_linguistic_df(linguistic_df)
    expert_weights = validate_expert_weights(linguistic_df, expert_weights)

    theta = []
    defuzz_values = []
    for crit in criteria_names:
        tfn_list = [LINGUISTIC_SCALE[linguistic_df.loc[crit, e]] for e in linguistic_df.columns]
        aggregated = aggregate_tfn(tfn_list, expert_weights)
        theta.append(aggregated)
        defuzz_values.append(defuzz_tfn(aggregated))

    positive_lowers = [t[0] for t in theta if t[0] > 0]
    min_l = min(positive_lowers) if positive_lowers else 1.0

    coeff = []
    for t in theta:
        if min(t) <= 0:
            coeff.append((0.0, 0.0, 0.0))
        else:
            coeff.append((min_l / t[2], min_l / t[1], min_l / t[0]))

    sorted_indices = np.argsort(defuzz_values)[::-1]
    coeff_sorted = [coeff[idx] for idx in sorted_indices]
    criteria_sorted = [criteria_names[idx] for idx in sorted_indices]

    weights_sorted, psi = solve_fuzzy_opa(coeff_sorted, n)
    if weights_sorted is None:
        raise ValueError("Fuzzy OPA optimization failed. Check linguistic data and expert weights.")

    weights = [None] * n
    for rank, idx in enumerate(sorted_indices):
        weights[idx] = weights_sorted[rank]

    theta_df = pd.DataFrame({
        "Criterion": criteria_names,
        "Theta_l": [t[0] for t in theta],
        "Theta_m": [t[1] for t in theta],
        "Theta_u": [t[2] for t in theta],
        "Defuzzified": defuzz_values,
    })

    coeff_df = pd.DataFrame({
        "Criterion": criteria_names,
        "Coeff_l": [c[0] for c in coeff],
        "Coeff_m": [c[1] for c in coeff],
        "Coeff_u": [c[2] for c in coeff],
    })

    weights_df = pd.DataFrame({
        "Criterion": criteria_names,
        "Weight_l": [w[0] for w in weights],
        "Weight_m": [w[1] for w in weights],
        "Weight_u": [w[2] for w in weights],
        "Defuzzified": [defuzz_tfn(w) for w in weights],
    })

    ranked_df = pd.DataFrame({
        "Rank": list(range(1, n + 1)),
        "Criterion": [criteria_names[idx] for idx in sorted_indices],
        "Weight_l": [weights_sorted[r][0] for r in range(n)],
        "Weight_m": [weights_sorted[r][1] for r in range(n)],
        "Weight_u": [weights_sorted[r][2] for r in range(n)],
        "Defuzzified": [defuzz_tfn(weights_sorted[r]) for r in range(n)],
    })

    return {
        "theta": theta,
        "defuzz_values": defuzz_values,
        "coeff": coeff,
        "sorted_indices": sorted_indices,
        "criteria_sorted": criteria_sorted,
        "weights": weights,
        "weights_sorted": weights_sorted,
        "psi": psi,
        "theta_df": theta_df,
        "coeff_df": coeff_df,
        "weights_df": weights_df,
        "ranked_df": ranked_df,
    }
