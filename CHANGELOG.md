# Changelog

## v2.0 - 2026-10

v2.0 is a rewrite of the v1.0 notebooks into a Python package, followed by a
systematic review of the inventories and the calculation chain. Input files from
v1.0 work unchanged. **Results differ from v1.0**, by an amount that depends on
the technology mix of each scenario (see *Bug fixes* below). Results from the two
versions should not be compared or combined.

### Structure

- The calculation moved from 25+ notebooks run with `%run` into three packages:
  - `plca/` - project setup, background databases, scenario input, LCA model,
    results aggregation and export;
  - `energy_systems/` - one module per technology (22 technologies), computing
    the inventory of each life cycle module;
  - `mcda/` - the multi-criteria ranking.
- `RUN_pLCA.ipynb` and `RUN_MCDA.ipynb` are now short drivers: they call the
  packages in order and hold no formulas. `RUN_MCDM.ipynb` is renamed
  `RUN_MCDA.ipynb`; `Libraries_pd.ipynb`, `ImportEcoinventDatasets_pd.ipynb` and
  the `Energy_systems_pd/` folder are replaced by the packages.
- The run-time questions can be answered in advance in the notebook's first
  cell, so a scenario can run unattended. **`batch_run.py`** (new) runs
  `RUN_pLCA.ipynb` once per prepared scenario.
- Credentials (ecoinvent login, premise key) are asked for at run time and are
  never stored in the notebook.
- Lower memory use and faster runs: on a 19-building test scenario, peak memory
  fell from 8.5 GB to 0.7 GB and run time from 560 s to 256 s; a 300-building
  scenario that v1.0 could not complete on a 16 GB machine now runs in 3 GB.

### New results

- **The neighbourhood total is now area-weighted:** sum(x_i * a_i) / sum(a_i),
  i.e. the impact of the whole neighbourhood per square metre of its total
  useful floor area. v1.0 summed the per-square-metre results of the buildings,
  which is not a per-square-metre figure.
- The neighbourhood workbook (`<scenario>_LCA_results_wholeneighbourhood.xlsx`)
  now also reports every life cycle module (A1-3 to D3), not only the whole life
  cycle, and two new sheets with the whole-life-cycle totals kept separate for
  heating, cooling and appliances (`WLC by Function (hood)`,
  `WLC no D by Function (hood)`).

### Input validation

- The DataInput workbook is checked when it is loaded. A missing sheet, column
  or value raises an error naming the sheet, the building and the column,
  instead of failing later inside Brightway.

### Bug fixes

More than 70 issues in the v1.0 inventories and calculation chain were fixed. They
fall into four groups:

- **Scaling and totals applied to the wrong quantity.** For example: each
  building was scaled by another building's lifetime factor in some systems;
  the heating B1 total was summed from the B2 results; the "no D" whole life
  cycle total left out the appliances.
- **Quantities in the wrong unit or charged to the wrong dataset.** For example:
  wastewater charged in cubic metres from kilogram amounts (x1000); module D3
  electricity credits in MJ charged to a dataset in kWh (x3.6); the boiler's
  combustion nitrogen wired to the NOx flow; reinforcing steel charged as
  generic steel in four systems.
- **Arithmetic that had drifted from the source inventories.** For example: the
  gas blend charged each machine's whole fuel demand three times (as natural
  gas, biomethane and hydrogen); the gas boiler fuel rows divided by the
  efficiency twice; the gas engine heat pump fuel rows used kWh where MJ were
  needed (x3.6); the biomass boiler above 500 kW used the natural gas boiler's
  mass curve; the number of replacements is now pro-rated over the study period
  instead of rounded up.
- **Dead, duplicated or silently failing code**, including in the MCDA: the
  thresholds are now derived from the parsed decision matrix, and a mismatch
  between the criterion names and the expert panel raises an error instead of
  silently giving neutral weights.

The size of each fix depends on the scenario. On two 300-building test
scenarios, the neighbourhood climate change result moved by +23% (all electric
heat pumps) and -95% (all gas boilers).

### Known issues

- `energy_systems/auxiliaries.py` (district network pipes and substations) is
  disabled, as in v1.0: its inputs have no worksheet yet. Its docstring lists
  what to fix before enabling it.
- Hydrogen in the gas blend: the blend's hydrogen share is 0 by default
  (`plca/config.py`, `GAS_BLEND`). Before using a non-zero share, check the
  hydrogen row of the boiler and of the gas engine heat pump, which use the
  natural gas conversion factor.

## v1.0 - 2026-04-01

First public release.
