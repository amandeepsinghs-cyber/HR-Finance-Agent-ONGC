# Answer Key: P2__drill_down

**Question:** Do Delhi and Dehradun form separate clusters, and how are Mumbai, Uran, and Panvel treated?
**Type:** `policy` | **Result Count:** `18` rows | **Execution:** `0.71s`

## Executive Synthesis
Yes - Delhi and Dehradun are separate clusters: New Delhi is CL-DEL and all 6 Dehradun work centres form CL-DDN, so a Delhi-Dehradun move is a genuine outstation transfer. Mumbai, Uran and Panvel are one cluster (CL-MUM, 11 work centres including Uran Plant and the Panvel units IEOT, IOGPT and Well Services), so moving among them does not reset station or cumulative tenure. The cluster mixes Category C offshore assets (Bassein & Satellite, Mumbai High and Neelam & Heera) with Category A urban offices, so an offshore-to-office move in Mumbai still counts as the same station.

### Summary Result Table
| city | wc_id | short_name | cluster_id | cluster_name | hard_station_cat |
| --- | --- | --- | --- | --- | --- |
| Dehradun | WC-ACA | ONGC Academy | CL-DDN | Dehradun Complex | A |
| Dehradun | WC-DDN | Dehradun Tel Bhavan | CL-DDN | Dehradun Complex | A |
| Dehradun | WC-FRB | Frontier Basin | CL-DDN | Dehradun Complex | A |
| Dehradun | WC-GEO | GEOPIC | CL-DDN | Dehradun Complex | A |
| Dehradun | WC-IDW | IDWE | CL-DDN | Dehradun Complex | A |
| Dehradun | WC-KDM | KDMIPE | CL-DDN | Dehradun Complex | A |
| New Delhi | WC-DEL | Delhi HQ | CL-DEL | Delhi National Capital Region | A |
| Mumbai | WC-BAS | Bassein & Satellite | CL-MUM | Mumbai–Panvel–Uran | C |
| Mumbai | WC-DRL | Drilling Services | CL-MUM | Mumbai–Panvel–Uran | B |
| Mumbai | WC-LOG | Offshore Logistics | CL-MUM | Mumbai–Panvel–Uran | B |