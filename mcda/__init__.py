"""
mcda - multi-criteria decision making for pLCA-NEST.

WHAT IT DOES. Given a table of completed pLCA scenarios - one row per
alternative, one column per criterion - it decides which alternative is best,
and says how much each criterion counted towards that answer. Three weighting
stages feed one ranking stage:

    objective weights   m-ITARA stages I and II, fused by EWCS. Read off the
                        decision matrix alone: a criterion earns weight by
                        separating the alternatives and by not merely
                        repeating what the other criteria already say.
    subjective weights  triangular fuzzy OPA on a panel of seven experts'
                        linguistic judgements, solved as a linear programme.
    final weights       the objective and subjective vectors, fused by EWCS.
    ranking             fuzzy CoCoSo with Bonferroni aggregation, on the
                        decision matrix widened to +/- 10%.

THE FILES, in dependency order - each imports only from the ones above it:

    config.py      the fuzzy scale, the expert panel, the coefficients. Data
                   only, no formula.
    utils.py       parsing, guards and validation shared by everything below.
    weights.py     m-ITARA stages I and II, and the EWCS fusion operator.
    opa.py         fuzzy OPA. The only file that needs an external solver.
    fuzzy.py       crisp decision matrix -> fuzzy, and the reshaping.
    cocoso.py      the ranking. The largest file, and the one that finally
                   brings weights and alternatives together.
    integrated.py  the pipeline, and the entry point RUN_MCDA.ipynb calls.

WHY THIS IS SEPARATE FROM plca/. The MCDA consumes scenario_summary.xlsx,
which is assembled by hand from SEVERAL completed scenario runs - each row is
one whole pLCA run. It is therefore separate from the single-scenario
pipeline RUN_pLCA.ipynb drives and shares no code with it. It imports no
Brightway; its dependencies are math, re, typing, numpy, pandas and pulp.

ENTRY POINT:

    import mcda
    D_df       = mcda.integrated.load_decision_matrix("scenario_summary.xlsx")
    thresholds = mcda.integrated.derive_thresholds(D_df)
    results    = mcda.integrated.analyse(D_df, thresholds)
    mcda.integrated.export_results_to_excel(results, "integrated_mcda_results.xlsx")
"""

from . import cocoso
from . import config
from . import fuzzy
from . import integrated
from . import opa
from . import utils
from . import weights
