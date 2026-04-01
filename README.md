# pLCA-NEST  
*prospective Life Cycle Assessment-Neighbourhood Energy system Selection Tool*
A tool designed to integrate the environmental evaluation of building-wise prospective scenarios of urban energy systems (heating, cooling, appliances) and their ranking with the m-ITARA-trigonometric t-conorm and t-norm fuzzy OPA–COPRAS method

---

## Project Goals

pLCA-NEST can be used to:

- Evaluate the environmental impacts of final energy use for heating, cooling and appliances of each building of an urban stack at a certain point in the future with a *life cycle perspective* 
- Define a ranking of different scenarios in terms of minimization of the potential environmental impacts

Moreover, since pLCA-NEST has been built on top of the LCA4DHC computational structure (https://zenodo.org/records/18302949), it can:
- Ensure compliance with EPBD (Energy Performance of Buildings Directive, version 4) requirements 
- Support standardized and automated LCA calculations according to EN 15804 + A2 and EN 50693
- Provide a modular, transparent, and reproducible computational framework 

---

## Project Status

- **Stable** – Core computational workflow is fully implemented and functional  
- **Experimental** – Scientific and methodological validation is ongoing  
- **Under active development** – Continuous updates and improvements  

**Compilers / Interfaces**
- Excel-based input files (`.xlsx`, `.xlsm`)
- Python (via Jupyter Notebook)

---

## Requirements

For the requirements of the Python environment see *requirements_pLCANEST_env.txt* file.

➕ **Third party software dependencies (see below)**

---

## Third Party Software

pLCA-NEST relies on the following third-party software and databases:

- **Brightway 2.5** – Core Life Cycle Assessment computational framework  
- **premise** - Core library for background database modification
- **ecoinvent database v3.11 cutoff** – Emission factors and background processes.
- Other versions of the ecoinvent database can be used; be sure to change process names used in the database if required.

⚠️ A **valid ecoinvent license** is required to run the tool.
⚠️ The **premise encryption key** is required to run the tool (please contact premise developers).

---

## License

                                 Apache License
                           Version 2.0, January 2004
                        http://www.apache.org/licenses/

   Copyright 2026 Saverio De Franceschi and Alessandro Manzardo

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

             http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.

---

## Disclaimer

The **pLCA-NEST** tool is provided for *research, academic, and technical support purposes only*.

- The authors do **not guarantee** the absence of errors, inaccuracies, or omissions.
- The authors accept **no liability** for any direct or indirect damages resulting from the use of the tool.
- Users are **fully responsible** for validating the correctness, robustness, and suitability of the results for their specific application.
- Results should be **independently reviewed**, especially when used for regulatory, policy, or decision-making purposes.
- The Excel input file **`DataInput` must be fully completed in all its sections**, with all required data fields properly filled in. Incomplete or partially compiled input files may lead to invalid or misleading results.

---

## References

This tool is based on the following peer-reviewed publications:

- **De Franceschi, S., Jabara, M., Wu, J., & Manzardo, A.** (2024).
*NEST Task 8.5.2: Framework of the LCA Model of an Urban Energy System* 
**2024 IEEE International Conference on Environment and Electrical Engineering and 2024 IEEE Industrial and Commercial Power Systems Europe (EEEIC / I&CPS Europe)**, pp. 1–6.
https://doi.org/10.1109/EEEIC/ICPSEurope61470.2024.10751034.

- ...
  
---

## Citation (Academic Use)

If you use this tool in academic work, please cite it as:

> De Franceschi, S., & Manzardo, A. (2026). *pLCA-NEST - A prospective Life Cycle Assessment Neighbourhood Energy system Selection Tool*. Zenodo. https://doi.org/10.5281/zenodo.19365133

---

## Contributing

Contributions are welcome.  
If you encounter bugs, issues, or have suggestions for improvements, please contact the authors or open an issue in the project repository.

---

## Author / Contact

**Saverio De Franceschi**  
*Centro Studi Qualità e Ambiente (CESQA), Università degli Studi di Padova*  
📧 saverio.defranceschi@phd.unipd.it  

**Alessandro Manzardo**  
*Centro Studi Qualità e Ambiente (CESQA), Università degli Studi di Padova*  
📧 alessandro.manzardo@unipd.it  

## Acknowledgments

This tool was funded by the National Recovery and Resilience Plan (NRRP), Mission 4 Component 2 Investment 1.3—Call for tender No. 1561 of 11.10.2022 of Ministero dell’Università e della Ricerca (MUR)—and funded by the European Union, NextGenerationEU, project code PE0000021, Concession Decree No. 1561 of 11.10.2022 adopted by Ministero dell’Università e della Ricerca (MUR), CUP–D43C2200309001, according to attachment E of Decree No. 1561/2022, project title “Network 4 Energy Sustainable Transition–NEST.”

