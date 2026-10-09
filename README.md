# pLCA-NEST
*prospective Life Cycle Assessment - Neighbourhood Energy system Selection Tool*

pLCA-NEST integrates the environmental evaluation of building-wise prospective
scenarios of urban energy systems (heating, cooling, appliances) and their ranking
with the m-ITARA-trigonometric t-conorm and t-norm fuzzy OPA-CoCoSo-Bonferroni
method.

**Version 2.0.** See [CHANGELOG.md](CHANGELOG.md) for what changed since v1.0;
results of the two versions are not comparable.

---

## What it does

pLCA-NEST can be used to:

- evaluate the environmental impacts of the final energy use for heating, cooling
  and appliances of each building of an urban stack, at a point in the future,
  with a life cycle perspective;
- rank different scenarios by the minimisation of their potential environmental
  impacts.

Since its LCA part is built on the computational structure of LCA4DHC
(Autelitano and Famiglietti, 2026, https://doi.org/10.5281/zenodo.18302949), it can also:

- ensure compliance with EPBD (Energy Performance of Buildings Directive,
  version 4) requirements;
- support standardised and automated LCA calculations according to
  EN 15804+A2 and EN 50693, per technology and per life cycle module (A to D,
  from cradle to cradle);
- provide a modular, transparent and reproducible computational framework.

The prospective background (a future ecoinvent) is generated with *premise* from
an Integrated Assessment Model scenario, e.g. REMIND SSP2-PkBudg1000 in 2030.

---

## Repository contents

| Path | Contents |
|---|---|
| `RUN_pLCA.ipynb` | Runs the LCA of one scenario. |
| `RUN_MCDA.ipynb` | Ranks several completed scenarios. |
| `batch_run.py` | Runs `RUN_pLCA.ipynb` unattended for several scenarios. |
| `plca/` | The LCA: background databases, scenario input, model, results. |
| `energy_systems/` | One module per technology (22 technologies). |
| `mcda/` | The multi-criteria ranking. Settings and the expert panel are in `mcda/config.py`. |
| `EndOfLifeInputParameters.xlsx` | End-of-life shares and heating values. Needed by every run. |
| `blank_inputs/` | Empty templates: `DataInput_blank.xlsm` (one scenario) and `scenario_summary_blank.xlsx` (the MCDA input). |
| `Examples/` | Worked examples: one scenario (`S14_2030/`) and a ranking of five (`MCDA_2030_SSP2-1000/`). |
| `pLCA-NEST User Manual.pdf` | The user manual. |

---

## Requirements

- **Python 3.12** (tested on Windows). Python 3.13 and later are not supported
  yet: the pinned numpy 1.26 is not available for them.
- **A valid ecoinvent licence** (username and password). The tool was built on
  ecoinvent **v3.11 cut-off**. Other versions can be used if every dataset named
  in `plca/ecoinvent_datasets.py` exists in them under the same name.
- **The premise decryption key**, available from the premise developers. It is
  needed only to generate a new prospective database.
- The Python packages in `requirements.txt`, mainly Brightway 2.5 and premise.

### Installation

```
python -m venv plcanest_env
plcanest_env\Scripts\activate          # on macOS/Linux: source plcanest_env/bin/activate
pip install -r requirements.txt
python -m ipykernel install --user --name plcanest_env
```

Then open the notebooks (in Jupyter or VS Code) with the `plcanest_env` kernel,
**from the repository folder**: the notebooks import `plca` and `mcda` from
there.

---

## Running one scenario: `RUN_pLCA.ipynb`

1. **Fill in a DataInput workbook** from `blank_inputs/DataInput_blank.xlsm`:
   the reference study period, the buildings (floor area, loads, heating,
   cooling and appliance demands, PV) and one sheet per energy system used.
   Every required field must be filled in.
2. **Put it in the repository folder**, next to `RUN_pLCA.ipynb`. The tool
   looks for `EndOfLifeInputParameters.xlsx` in the same folder as the
   DataInput file.
3. **Run the notebook** from top to bottom and answer its questions (Brightway
   project, ecoinvent version, premise scenario, DataInput file name, scenario
   name). The answers can also be written in advance in the notebook's
   *Answers prepared in advance* cell.
   - The first run in a new Brightway project imports ecoinvent, and the first
     run for a new premise scenario and year generates the prospective
     database. Each of these can take several minutes and is done only once; later runs
     find the existing databases and skip these steps.
   - The scenario name is used for the scenario database and for every output
     file. If a database with that name already exists, you are asked before it
     is deleted.

**Outputs**, written next to the notebook (`<name>` is the scenario name):

| File | Contents |
|---|---|
| `<name>_LCA_results_heating.xlsx` | Heating systems: one row per building, one sheet per life cycle module, plus whole life cycle with and without module D. |
| `<name>_LCA_results_cooling.xlsx` | The same for cooling (no module B1). |
| `<name>_LCA_results_appliances.xlsx` | Appliances (module B6 only). |
| `<name>_LCA_results.xlsx` | Heating + cooling + appliances, per building. |
| `<name>_LCA_results_wholeneighbourhood.xlsx` | The neighbourhood: one row per sheet, per life cycle module and for the whole life cycle, plus the totals split by function. |
| `<name>_per_system.pkl` | Every result frame, per technology and module, for further analysis. |

Results are given for the 15 EN 15804+A2 impact categories, **per m² of useful
floor area**. The neighbourhood figures are area-weighted over the buildings:
the impact of the whole neighbourhood divided by its total floor area.

### Several scenarios: `batch_run.py`

Write one text file per scenario with the twelve answers of the notebook's
*Answers prepared in advance* cell (see `Examples/S14_2030/inputs_S14.txt`),
put them in a folder, and run from the repository folder:

```
python batch_run.py RUN_pLCA.ipynb --inputs-dir batch_runs_inputs
```

Each scenario runs in a fresh kernel; a failing scenario is logged and the next
one starts. The ecoinvent login and the premise key are not in the files: the
databases they unlock must already exist in the Brightway project, so run one
scenario interactively first. See the top of `batch_run.py` for all options.

---

## Ranking scenarios: `RUN_MCDA.ipynb`

1. Run `RUN_pLCA.ipynb` for every scenario (alternative) to compare.
2. Fill in `scenario_summary.xlsx` from `blank_inputs/scenario_summary_blank.xlsx`:
   one row per scenario, one column per criterion (C1-C11, the impact
   categories listed in the *Legend* sheet), taken from each scenario's
   neighbourhood workbook: sheet *Whole Lifecycle (hood)* (with module D, as in
   the example) or *Whole Lifecycle (no D, hood)*, the same for all scenarios.
3. Put it next to `RUN_MCDA.ipynb` and run the notebook. It needs no database
   and no Brightway.

The method combines objective criterion weights from the decision matrix
(m-ITARA), subjective weights from an expert panel (fuzzy OPA) and ranks the
scenarios with fuzzy CoCoSo-Bonferroni. The expert judgements, the criterion
types and the method parameters are set in `mcda/config.py`.

**Outputs:** `integrated_mcda_results.xlsx` (every step of the method) and
`integrated_mcda_results_short.xlsx` (final weights and ranking only). Both are
overwritten by the next run.

---

## Examples

### One scenario: S14 (2030)

`Examples/S14_2030/` holds a complete run of a 475-building neighbourhood in
Padova (Italy) in 2030, background REMIND SSP2-PkBudg1000:

- `DataInput_S14.xlsm` - the input (gas boilers, electric heat pumps and
  compression chillers);
- `inputs_S14.txt` - the same run as a `batch_run.py` input. Replace
  `EI_BACKGROUND` with the name of the premise database in your project;
- `results/` - the five result workbooks.

To reproduce it, copy `DataInput_S14.xlsm` next to `RUN_pLCA.ipynb` and run the
notebook with the answers in `inputs_S14.txt`. Small differences can come from a
different premise or ecoinvent build.

### Ranking: five scenarios in 2030

`Examples/MCDA_2030_SSP2-1000/` ranks five alternative scenarios of the same
neighbourhood (S10-S14, all in 2030 with REMIND SSP2-PkBudg1000):

- `scenario_summary.xlsx` - the decision matrix, taken from each scenario's
  *Whole Lifecycle (hood)* sheet (whole life cycle including module D);
- `results/` - the two MCDA workbooks.

To reproduce it, copy `scenario_summary.xlsx` next to `RUN_MCDA.ipynb` and run
the notebook.

---

## Third-party software

- **Brightway 2.5** - LCA calculation framework (Mutel, 2017).
- **premise** - prospective background databases (Sacchi et al., 2022).
- **ecoinvent v3.11 cut-off** - background processes. ⚠️ A valid ecoinvent
  licence is required.
- **PuLP** with the CBC solver - the fuzzy OPA linear programme.

---

## Disclaimer

pLCA-NEST is provided for *research, academic and technical support purposes only*.

- The authors do **not guarantee** the absence of errors, inaccuracies or omissions.
- The authors accept **no liability** for any direct or indirect damages resulting from the use of the tool.
- Users are **fully responsible** for validating the correctness, robustness and suitability of the results for their application.
- Results should be **independently reviewed**, especially when used for regulatory, policy or decision-making purposes.
- The DataInput workbook **must be fully completed in all its sections**. Incomplete input files may lead to invalid or misleading results.

---

## References

- De Franceschi, S., Jabara, M., Wu, J. and Manzardo, A. (2024). *NEST Task 8.5.2:
  Framework of the LCA Model of an Urban Energy System.* 2024 IEEE International
  Conference on Environment and Electrical Engineering and 2024 IEEE Industrial
  and Commercial Power Systems Europe (EEEIC / I&CPS Europe), pp. 1-6.
  https://doi.org/10.1109/EEEIC/ICPSEurope61470.2024.10751034
- Autelitano, K. and Famiglietti, J. (2026). *LCA4DHC - A Life Cycle Assessment
  data-driven tool for the evaluation of District Heating and Cooling networks.*
  Zenodo. https://doi.org/10.5281/zenodo.18302949
- Mutel, C. (2017). Brightway: An open source framework for Life Cycle Assessment.
  *Journal of Open Source Software*, 2(12), 236. https://doi.org/10.21105/joss.00236
- Sacchi, R. et al. (2022). PRospective EnvironMental Impact asSEment (premise).
  *Renewable and Sustainable Energy Reviews*, 160, 112311.
  https://doi.org/10.1016/j.rser.2022.112311

---

## Citation

If you use this tool in academic work, please cite it. GitHub's **"Cite this
repository"** button (from `CITATION.cff`) gives the reference in APA and BibTeX:

> De Franceschi, S. and Manzardo, A. (2026). *pLCA-NEST - prospective Life Cycle
> Assessment Neighbourhood Energy system Selection Tool* (Version 2.0). Zenodo.
> https://doi.org/10.5281/zenodo.23264647

To cite all versions, or always the latest one, use
https://doi.org/10.5281/zenodo.23264646.

---

## License

Copyright 2026 Saverio De Franceschi and Alessandro Manzardo.
Licensed under the Apache License, Version 2.0 - see [LICENSE](LICENSE).

---

## Contributing

Contributions are welcome. If you find a bug or have a suggestion, please open
an issue in this repository or contact the authors.

## Authors / Contact

**Saverio De Franceschi**
*Centro Studi Qualità e Ambiente (CESQA), Università degli Studi di Padova*
📧 saverio.defranceschi@phd.unipd.it

**Alessandro Manzardo**
*Centro Studi Qualità e Ambiente (CESQA), Università degli Studi di Padova*
📧 alessandro.manzardo@unipd.it

## Acknowledgments

This tool was funded by the National Recovery and Resilience Plan (NRRP), Mission 4 Component 2 Investment 1.3—Call for tender No. 1561 of 11.10.2022 of Ministero dell’Università e della Ricerca (MUR)—and funded by the European Union, NextGenerationEU, project code PE0000021, Concession Decree No. 1561 of 11.10.2022 adopted by Ministero dell’Università e della Ricerca (MUR), CUP–D43C2200309001, according to attachment E of Decree No. 1561/2022, project title “Network 4 Energy Sustainable Transition–NEST.”
