"""
SPEC-05 Field Economics-360 Biproportional (RAS) Allocation Engine.
Reads frozen real AR targets (field_econ_targets_fy.csv), physical drivers
(production_monthly.csv), P2H.5 employee production cost (PY_CLUSTER_EXP.csv),
and structured driver priors (alloc_drivers.yaml, cost_objects.yaml).

Performs:
1. Pre-flight P&L identity, Note 35 sum, and Note 44 segment identity assertions.
2. Production & sales volume calibration by basis (ONGC vs JV_SHARE, plants for VAP).
3. Two-way RAS fitting on Segment x Product for Revenue (SPEC-05 §6.2).
4. Two-way RAS fitting on Segment x Nature for Costs (SPEC-05 §6.3) with pinned
   cells (SEG.DDA.*, SEG.IMP.*, SEG.WO.*, N35.STAFF_EXPENDITURE).
5. Object down-allocation and monthly phasing via largest_remainder_round so every
   month-sum == FY object total and every object-sum == segment/company AR target.
"""

from pathlib import Path
import numpy as np
import pandas as pd
import yaml

try:
    from generators.finance.ras import ras_fit, largest_remainder_round
except ImportError:
    from ras import ras_fit, largest_remainder_round

DATA_BANK_DIR = Path(__file__).resolve().parent.parent.parent
WORLD_BIBLE = DATA_BANK_DIR / "world_bible"
LANDING_SAP = DATA_BANK_DIR / "landing" / "sap"
DB_EXPORTS = DATA_BANK_DIR / "landing" / "db_exports"

NOTE35_LEVIES = [
    "N35.ROYALTY",
    "N35.OIDB_CESS",
    "N35.NCCD",
    "N35.EXCISE_SAED",
    "N35.PORT_TRUST",
    "N35.OTHER_LEVIES",
]

NOTE35_OPEX = [
    "N35.STAFF_EXPENDITURE",
    "N35.WORKOVER_OPS",
    "N35.WATER_INJECTION_DESALTING",
    "N35.CONSUMPTION_STORES_SPARES",
    "N35.POLLUTION_CONTROL",
    "N35.TRANSPORT_EXPENDITURE",
    "N35.INSURANCE",
    "N35.POWER_FUEL",
    "N35.REPAIRS_MAINTENANCE",
    "N35.CONTRACTUAL_HIRE",
    "N35.OTHER_PRODUCTION_EXP",
    "N35.TRANSPORT_FREIGHT_PRODUCTS",
    "N35.R_AND_D",
    "N35.GAE",
    "N35.CSR",
    "N35.EXCHANGE_LOSS",
    "N35.MISC_EXP",
    "N35.FV_LOSS",
]

CORPORATE_NATURES = {
    "N35.R_AND_D",
    "N35.GAE",
    "N35.CSR",
    "N35.EXCHANGE_LOSS",
    "N35.MISC_EXP",
    "N35.FV_LOSS",
}

ALL_NOTE35 = NOTE35_LEVIES + NOTE35_OPEX


def load_data():
    with open(WORLD_BIBLE / "reference" / "cost_objects.yaml") as f:
        cost_objects = yaml.safe_load(f)["cost_objects"]
    with open(WORLD_BIBLE / "reference" / "alloc_drivers.yaml") as f:
        alloc_drivers = yaml.safe_load(f)
    targets = pd.read_csv(
        WORLD_BIBLE / "reference" / "real_targets" / "field_econ_targets_fy.csv"
    )
    prod = pd.read_csv(DB_EXPORTS / "production_monthly.csv")
    py_exp = pd.read_csv(
        LANDING_SAP / "PY_CLUSTER_EXP.csv",
        usecols=[
            "FPPER",
            "fiscal_year",
            "wc_id",
            "cost_expensed_production_inr",
            "cost_expensed_inr",
            "cost_capitalised_inr",
        ],
    )
    with open(WORLD_BIBLE / "reference" / "work_centres.yaml") as f:
        work_centres = {
            w["wc_id"]: w for w in yaml.safe_load(f)["work_centres"]
        }
    return cost_objects, alloc_drivers, targets, prod, py_exp, work_centres


def verify_target_identities(targets: pd.DataFrame) -> None:
    """Assert P&L, Note 35, and Segment identities per FY before allocating."""
    for fy, grp in targets.groupby("fiscal_year"):
        m = dict(zip(grp["line_code"].str.upper(), grp["value"]))
        tol = 0.01 if int(fy[2:]) >= 21 else 1.0

        # 1. Note 35 sum == PL.PROD_EXP
        n35_sum = sum(m[c] for c in ALL_NOTE35)
        assert abs(n35_sum - m["PL.PROD_EXP"]) <= tol, (
            f"{fy} Note 35 sum {n35_sum:.2f} != PL.PROD_EXP {m['PL.PROD_EXP']:.2f}"
        )

        # 2. P&L identity: Total Income - Total Expenses + Exceptional == PBT
        tot_inc = m["PL.REV_OPS"] + m["PL.OTHER_INCOME"]
        tot_exp = (
            m["PL.PROD_EXP"]
            + m["PL.EXPL_SURVEY"]
            + m["PL.EXPL_WELLS"]
            + m["PL.DDA"]
            + m["PL.PROVISIONS"]
            + m["PL.FIN_COST"]
            + m["PL.INVENTORY_CHANGE"]
            + m["PL.PURCHASES_TRADED"]
        )
        pbt_calc = tot_inc - tot_exp + m.get("PL.EXCEPTIONAL", 0.0)
        assert abs(pbt_calc - m["PL.PBT"]) <= tol, (
            f"{fy} P&L identity failed: {pbt_calc:.2f} != PL.PBT {m['PL.PBT']:.2f}"
        )

        # 3. Segment identity: SEG.RES.OFF + SEG.RES.ON + SEG.UNALLOC - PL.FIN_COST + SEG.INT_DIV - PL.EXCEP == PL.PBT
        seg_pbt = (
            m["SEG.RES.OFF"]
            + m["SEG.RES.ON"]
            + m["SEG.UNALLOC"]
            - m["PL.FIN_COST"]
            + m["SEG.INT_DIV"]
            - m.get("PL.EXCEP", -m.get("PL.EXCEPTIONAL", 0.0))
        )
        assert abs(seg_pbt - m["PL.PBT"]) <= tol, (
            f"{fy} Segment identity failed: {seg_pbt:.2f} != PL.PBT {m['PL.PBT']:.2f}"
        )

        # 4. Revenue product sum and segment sum == PL.REV_OPS to 2 dp
        rev_prod_sum = sum(
            m[p] for p in ("REV.CRUDE", "REV.GAS", "REV.VAP", "REV.OTHER_OP")
        )
        assert abs(rev_prod_sum - m["PL.REV_OPS"]) <= 0.01, (
            f"{fy} Revenue product sum {rev_prod_sum:.2f} != PL.REV_OPS {m['PL.REV_OPS']:.2f}"
        )
        rev_seg_sum = m["SEG.REV.OFF"] + m["SEG.REV.ON"]
        assert abs(rev_seg_sum - m["PL.REV_OPS"]) <= 0.01, (
            f"{fy} Segment revenue sum {rev_seg_sum:.2f} != PL.REV_OPS {m['PL.REV_OPS']:.2f}"
        )


def build_staff_seeds(
    py_exp: pd.DataFrame,
    prod: pd.DataFrame,
    cost_objects: list[dict],
    work_centres: dict,
):
    """
    Map P2H.5 PY_CLUSTER_EXP.csv cost_expensed_production_inr (and total employee cost)
    to producing field and plant cost objects by fiscal_year and month (FPPER).
    """
    py_grp = (
        py_exp.groupby(["fiscal_year", "FPPER", "wc_id"], as_index=False)[
            [
                "cost_expensed_production_inr",
                "cost_expensed_inr",
                "cost_capitalised_inr",
            ]
        ]
        .sum()
    )
    py_grp["prod_staff_mn"] = py_grp["cost_expensed_production_inr"] / 1e6
    py_grp["emp_total_mn"] = (
        py_grp["cost_expensed_inr"] + py_grp["cost_capitalised_inr"]
    ) / 1e6

    # Map asset/plant wc_id -> list of producing objects (field, jv_share, plant)
    wc_to_objs = {}
    obj_meta = {o["object_id"]: o for o in cost_objects}
    prod_objs = [
        o["object_id"]
        for o in cost_objects
        if o["object_type"] in ("field", "jv_share", "plant")
    ]
    offshore_prod_objs = [
        oid for oid in prod_objs if obj_meta[oid]["segment"] == "Offshore"
    ]
    onshore_prod_objs = [
        oid for oid in prod_objs if obj_meta[oid]["segment"] == "Onshore"
    ]

    for oid in prod_objs:
        wcid = obj_meta[oid].get("asset_wc_id") or obj_meta[oid].get("wc_id")
        wc_to_objs.setdefault(wcid, []).append(oid)

    # Monthly BOE by (fiscal_year, month, object_id)
    prod_m = (
        prod.groupby(["fiscal_year", "month", "field_id"])[
            "total_production_boe"
        ]
        .sum()
        .unstack(fill_value=0.0)
    )
    # Give plants a constant BOE proxy for internal staff weighting
    for p_oid, cap_boe in [
        ("WC-URN", 450000.0),
        ("WC-HAZ", 400000.0),
        ("WC-DAH", 150000.0),
    ]:
        if p_oid not in prod_m.columns:
            prod_m[p_oid] = cap_boe

    staff_month_map = {}  # (fy, month, oid) -> ₹ mn
    emp_tot_month_map = {}  # (fy, month, oid) -> ₹ mn

    for (fy, fpper), sub in py_grp.groupby(["fiscal_year", "FPPER"]):
        boe_row = (
            prod_m.loc[(fy, fpper)]
            if (fy, fpper) in prod_m.index
            else pd.Series(1.0, index=prod_objs)
        )
        obj_staff = {oid: 0.0 for oid in prod_objs}
        obj_emp_tot = {oid: 0.0 for oid in prod_objs}

        unmapped_off_staff = 0.0
        unmapped_on_staff = 0.0
        unmapped_off_tot = 0.0
        unmapped_on_tot = 0.0

        for _, row in sub.iterrows():
            wcid = row["wc_id"]
            s_val = float(row["prod_staff_mn"])
            t_val = float(row["emp_total_mn"])
            if wcid in wc_to_objs:
                mapped = wc_to_objs[wcid]
                weights = np.array(
                    [max(float(boe_row.get(oid, 0.0)), 1.0) for oid in mapped]
                )
                weights = weights / weights.sum()
                for oid, w in zip(mapped, weights):
                    obj_staff[oid] += s_val * w
                    obj_emp_tot[oid] += t_val * w
            else:
                wc_info = work_centres.get(wcid, {})
                loc_type = wc_info.get("onshore_offshore", "corporate")
                if loc_type == "offshore":
                    unmapped_off_staff += s_val
                    unmapped_off_tot += t_val
                elif loc_type == "onshore":
                    unmapped_on_staff += s_val
                    unmapped_on_tot += t_val
                else:
                    # Corporate/service WCs split across Offshore/Onshore by BOE
                    unmapped_off_staff += s_val * 0.55
                    unmapped_on_staff += s_val * 0.45
                    unmapped_off_tot += t_val * 0.55
                    unmapped_on_tot += t_val * 0.45

        # Distribute service/regional pools across Offshore and Onshore objects by BOE
        off_w = np.array(
            [max(float(boe_row.get(oid, 0.0)), 1.0) for oid in offshore_prod_objs]
        )
        off_w = off_w / off_w.sum()
        for oid, w in zip(offshore_prod_objs, off_w):
            obj_staff[oid] += unmapped_off_staff * w
            obj_emp_tot[oid] += unmapped_off_tot * w

        on_w = np.array(
            [max(float(boe_row.get(oid, 0.0)), 1.0) for oid in onshore_prod_objs]
        )
        on_w = on_w / on_w.sum()
        for oid, w in zip(onshore_prod_objs, on_w):
            obj_staff[oid] += unmapped_on_staff * w
            obj_emp_tot[oid] += unmapped_on_tot * w

        for oid in prod_objs:
            staff_month_map[(fy, fpper, oid)] = obj_staff[oid]
            emp_tot_month_map[(fy, fpper, oid)] = obj_emp_tot[oid]

    return staff_month_map, emp_tot_month_map


def run_allocation():
    cost_objects, alloc_drivers, targets, prod, py_exp, work_centres = load_data()
    verify_target_identities(targets)

    staff_month_map, emp_tot_month_map = build_staff_seeds(
        py_exp, prod, cost_objects, work_centres
    )

    obj_meta = {o["object_id"]: o for o in cost_objects}
    objs = [o["object_id"] for o in cost_objects]
    segments = ["Offshore", "Onshore", "Unallocated"]
    seg_idx = {s: i for i, s in enumerate(segments)}

    fys = sorted(targets["fiscal_year"].unique())
    copa_rows = []
    audit_rows = []

    maturity_map = alloc_drivers.get(
        "maturity_factors",
        {"mature": 1.15, "plateau": 1.0, "growth": 0.85, "developing": 1.0},
    )
    driver_cfg = alloc_drivers.get("drivers", {})
    price_factors = alloc_drivers.get("price_factors", {})

    plant_vap_weights = {"WC-URN": 0.45, "WC-HAZ": 0.40, "WC-DAH": 0.15}
    exp_basin_weights = {
        "EXP-WOB": 0.42,
        "EXP-KGB": 0.33,
        "EXP-MBA": 0.15,
        "EXP-ANDAMAN": 0.10,
        "EXP-CAB": 0.30,
        "EXP-AAB": 0.30,
        "EXP-RAJ": 0.15,
        "EXP-CAU": 0.15,
        "EXP-OTHER": 0.10,
    }

    for fy in fys:
        fy_targets = targets[targets["fiscal_year"] == fy]
        tmap = dict(zip(fy_targets["line_code"].str.upper(), fy_targets["value"]))

        start_year = 2000 + int(fy[2:]) - 1
        months = [
            f"{start_year + (1 if m > 12 else 0)}-{((m - 1) % 12) + 1:02d}"
            for m in range(4, 16)
        ]

        fy_prod = prod[prod["fiscal_year"] == fy]
        # Monthly driver series per object (shape: 12)
        m_oil_mt = {}
        m_cond_mt = {}
        m_gas_mmscm = {}
        m_boe = {}
        m_oil_sales = {}
        m_gas_sales = {}
        m_water = {}
        m_flare = {}
        m_wells = {}
        m_staff = {}
        m_emp_tot = {}

        for oid in objs:
            sub = fy_prod[fy_prod["field_id"] == oid].set_index("month")
            if len(sub) > 0:
                m_oil_mt[oid] = np.array(
                    [float(sub.loc[m, "oil_production_mt"]) if m in sub.index else 0.0 for m in months]
                )
                m_cond_mt[oid] = np.array(
                    [float(sub.loc[m, "condensate_production_mt"]) if m in sub.index else 0.0 for m in months]
                )
                m_gas_mmscm[oid] = np.array(
                    [float(sub.loc[m, "gas_production_mmscm"]) if m in sub.index else 0.0 for m in months]
                )
                m_boe[oid] = np.array(
                    [float(sub.loc[m, "total_production_boe"]) if m in sub.index else 0.0 for m in months]
                )
                m_oil_sales[oid] = np.array(
                    [float(sub.loc[m, "oil_sales_mt"]) if m in sub.index else 0.0 for m in months]
                )
                m_gas_sales[oid] = np.array(
                    [float(sub.loc[m, "gas_sales_mmscm"]) if m in sub.index else 0.0 for m in months]
                )
                m_water[oid] = np.array(
                    [float(sub.loc[m, "water_produced_m3"]) if m in sub.index else 0.0 for m in months]
                )
                m_flare[oid] = np.array(
                    [float(sub.loc[m, "gas_flared_mmscm"]) if m in sub.index else 0.0 for m in months]
                )
                m_wells[oid] = np.array(
                    [float(sub.loc[m, "active_producing_wells"]) if m in sub.index else 0.0 for m in months]
                )
            else:
                z = np.zeros(12)
                m_oil_mt[oid] = z.copy()
                m_cond_mt[oid] = z.copy()
                m_gas_mmscm[oid] = z.copy()
                m_boe[oid] = np.ones(12) if obj_meta[oid]["object_type"] == "plant" else z.copy()
                m_oil_sales[oid] = z.copy()
                m_gas_sales[oid] = z.copy()
                m_water[oid] = z.copy()
                m_flare[oid] = z.copy()
                m_wells[oid] = z.copy()

            m_staff[oid] = np.array(
                [float(staff_month_map.get((fy, m, oid), 0.0)) for m in months]
            )
            m_emp_tot[oid] = np.array(
                [float(emp_tot_month_map.get((fy, m, oid), 0.0)) for m in months]
            )

        # Store monthly allocated series: (oid, line_code) -> np.ndarray(12), basis
        alloc_m = {}
        basis_map = {}

        def allocate_line_to_objects(
            line_code: str,
            obj_weights: dict[str, float],
            total_target: float,
            month_profiles: dict[str, np.ndarray],
            basis: str = "RT",
            precision: int = 2,
        ):
            if abs(total_target) < 1e-12:
                for oid in obj_weights:
                    alloc_m[(oid, line_code)] = np.zeros(12)
                    basis_map[(oid, line_code)] = basis
                return
            oids = [oid for oid, w in obj_weights.items() if w > 0]
            w_arr = np.array([obj_weights[oid] for oid in oids], dtype=float)
            w_arr = w_arr / w_arr.sum()
            obj_totals = largest_remainder_round(
                w_arr * total_target, total_target, precision=precision
            )
            for oid, o_tot in zip(oids, obj_totals):
                if abs(o_tot) < 1e-12:
                    alloc_m[(oid, line_code)] = np.zeros(12)
                    basis_map[(oid, line_code)] = basis
                    continue
                prof = month_profiles.get(oid, np.ones(12))
                if np.sum(prof) <= 0:
                    prof = np.ones(12)
                prof_norm = prof / np.sum(prof)
                m_vals = largest_remainder_round(
                    prof_norm * o_tot, o_tot, precision=precision
                )
                alloc_m[(oid, line_code)] = m_vals
                basis_map[(oid, line_code)] = basis

        # ------------------------------------------------------------------
        # 1. Production & Sales Volumes (SPEC-05 §6.1, FLD-R11, FLD-R12)
        # ------------------------------------------------------------------
        ongc_field_objs = [
            oid for oid in objs if obj_meta[oid]["object_type"] == "field"
        ]
        jv_objs = [
            oid for oid in objs if obj_meta[oid]["object_type"] == "jv_share"
        ]
        plant_objs = [
            oid for oid in objs if obj_meta[oid]["object_type"] == "plant"
        ]
        prod_field_jv = ongc_field_objs + jv_objs

        allocate_line_to_objects(
            "PROD.CRUDE_ONGC",
            {oid: float(np.sum(m_oil_mt[oid] + m_cond_mt[oid])) for oid in ongc_field_objs},
            tmap["PROD.CRUDE_ONGC"],
            {oid: m_oil_mt[oid] + m_cond_mt[oid] for oid in ongc_field_objs},
            basis="RT",
            precision=4,
        )
        allocate_line_to_objects(
            "PROD.CRUDE_JV",
            {oid: float(np.sum(m_oil_mt[oid] + m_cond_mt[oid])) for oid in jv_objs},
            tmap["PROD.CRUDE_JV"],
            {oid: m_oil_mt[oid] + m_cond_mt[oid] for oid in jv_objs},
            basis="RT",
            precision=4,
        )
        allocate_line_to_objects(
            "PROD.GAS_ONGC",
            {oid: float(np.sum(m_gas_mmscm[oid])) for oid in ongc_field_objs},
            tmap["PROD.GAS_ONGC"],
            {oid: m_gas_mmscm[oid] for oid in ongc_field_objs},
            basis="RT",
            precision=4,
        )
        allocate_line_to_objects(
            "PROD.GAS_JV",
            {oid: float(np.sum(m_gas_mmscm[oid])) for oid in jv_objs},
            tmap["PROD.GAS_JV"],
            {oid: m_gas_mmscm[oid] for oid in jv_objs},
            basis="RT",
            precision=4,
        )
        allocate_line_to_objects(
            "QTY.CRUDE_SOLD",
            {oid: float(np.sum(m_oil_sales[oid])) for oid in prod_field_jv},
            tmap["QTY.CRUDE_SOLD"],
            {oid: m_oil_sales[oid] for oid in prod_field_jv},
            basis="RT",
            precision=4,
        )
        allocate_line_to_objects(
            "QTY.GAS_SOLD",
            {oid: float(np.sum(m_gas_sales[oid])) for oid in prod_field_jv},
            tmap["QTY.GAS_SOLD"],
            {oid: m_gas_sales[oid] for oid in prod_field_jv},
            basis="RT",
            precision=4,
        )
        allocate_line_to_objects(
            "QTY.VAP_SOLD",
            plant_vap_weights,
            tmap["QTY.VAP_SOLD"],
            {oid: np.ones(12) for oid in plant_objs},
            basis="RT",
            precision=2,
        )

        # ------------------------------------------------------------------
        # 2. Revenue Two-Way RAS: Segment (Offshore, Onshore) x Product (SPEC-05 §6.2)
        # ------------------------------------------------------------------
        rev_products = ["REV.CRUDE", "REV.GAS", "REV.VAP", "REV.OTHER_OP"]
        rev_objs_all = prod_field_jv + plant_objs

        # Build object-level prior weights for each revenue product
        rev_obj_seed = {p: {} for p in rev_products}
        for oid in prod_field_jv:
            seg = obj_meta[oid]["segment"]
            crude_pf = float(price_factors.get("crude", {}).get(seg, 1.0))
            gas_pf = float(price_factors.get("gas", {}).get(seg, 1.0))
            if oid in ("FLD-KG982", "FLD-DAM", "FLD-B17", "FLD-CS1", "FLD-BAS", "JV-RAVVA"):
                gas_pf *= 1.35  # HPHT / New Well gas premium per SPEC-05 §4.C
            rev_obj_seed["REV.CRUDE"][oid] = (
                float(np.sum(alloc_m.get((oid, "QTY.CRUDE_SOLD"), np.zeros(12)))) * crude_pf
            )
            rev_obj_seed["REV.GAS"][oid] = (
                float(np.sum(alloc_m.get((oid, "QTY.GAS_SOLD"), np.zeros(12)))) * gas_pf
            )
            rev_obj_seed["REV.VAP"][oid] = 0.0
            rev_obj_seed["REV.OTHER_OP"][oid] = float(np.sum(m_boe[oid]))

        for oid in plant_objs:
            rev_obj_seed["REV.CRUDE"][oid] = 0.0
            rev_obj_seed["REV.GAS"][oid] = 0.0
            rev_obj_seed["REV.VAP"][oid] = plant_vap_weights[oid]
            rev_obj_seed["REV.OTHER_OP"][oid] = plant_vap_weights[oid] * 500000.0

        # Build 2 x 4 seed matrix (rows: Offshore, Onshore; cols: REV.CRUDE, REV.GAS, REV.VAP, REV.OTHER_OP)
        rev_seed_mat = np.zeros((2, 4), dtype=float)
        for j, p in enumerate(rev_products):
            col_tot = tmap[p]
            raw_s = np.array(
                [
                    sum(
                        rev_obj_seed[p][oid]
                        for oid in rev_objs_all
                        if obj_meta[oid]["segment"] == s
                    )
                    for s in ("Offshore", "Onshore")
                ]
            )
            rev_seed_mat[:, j] = col_tot * (raw_s / np.sum(raw_s))

        rev_row_targets = np.array(
            [tmap["SEG.REV.OFF"], tmap["SEG.REV.ON"]], dtype=float
        )
        rev_col_targets = np.array([tmap[p] for p in rev_products], dtype=float)
        # Scale col_targets for RAS matrix consistency so sum(rows) == sum(cols)
        rev_col_targets_ras = rev_col_targets * (
            np.sum(rev_row_targets) / np.sum(rev_col_targets)
        )
        rev_fitted_mat = ras_fit(
            rev_seed_mat, rev_row_targets, rev_col_targets_ras, tol=1e-9, max_iter=500
        )

        # Record audit rows for revenue products
        for s_i, seg in enumerate(["Offshore", "Onshore"]):
            for j, p in enumerate(rev_products):
                s_val = float(rev_seed_mat[s_i, j])
                f_val = float(rev_fitted_mat[s_i, j])
                audit_rows.append(
                    {
                        "fy": fy,
                        "segment": seg,
                        "nature": p,
                        "seed": round(s_val, 4),
                        "ras_factor": round(f_val / s_val if s_val > 0 else 1.0, 6),
                        "final": round(f_val, 4),
                    }
                )

        # Round 2 x 4 RAS-fitted revenue matrix via largest_remainder_round so every
        # product column sum equals tmap[p] AND every segment row sum equals SEG.REV.OFF / SEG.REV.ON
        # AND grand total equals PL.REV_OPS to exact 2 decimal places (0.00 diff).
        rounded_rev_mat = np.zeros_like(rev_fitted_mat)
        for j, p in enumerate(rev_products):
            c_tot = round(float(rev_col_targets[j]), 2)
            rounded_rev_mat[:, j] = largest_remainder_round(
                rev_fitted_mat[:, j], c_tot, precision=2
            )
        rev_row_targets_2d = np.array([round(rt, 2) for rt in rev_row_targets])
        rev_row_diffs = np.round(
            rev_row_targets_2d - np.sum(rounded_rev_mat, axis=1), 2
        )
        if abs(rev_row_diffs[0]) > 0:
            rounded_rev_mat[0, 0] = round(
                rounded_rev_mat[0, 0] + rev_row_diffs[0], 2
            )
            rounded_rev_mat[1, 0] = round(
                rounded_rev_mat[1, 0] - rev_row_diffs[0], 2
            )

        # Allocate each (segment, product) cell to objects and months via largest_remainder_round
        for j, p in enumerate(rev_products):
            for s_i, seg in enumerate(["Offshore", "Onshore"]):
                cell_target = round(float(rounded_rev_mat[s_i, j]), 2)
                seg_oids = [
                    oid
                    for oid in rev_objs_all
                    if obj_meta[oid]["segment"] == seg
                    and rev_obj_seed[p].get(oid, 0.0) > 0
                ]
                w_dict = {oid: rev_obj_seed[p][oid] for oid in seg_oids}
                m_prof = {
                    oid: (
                        m_oil_sales[oid]
                        if p == "REV.CRUDE"
                        else m_gas_sales[oid]
                        if p == "REV.GAS"
                        else m_boe[oid]
                    )
                    for oid in seg_oids
                }
                allocate_line_to_objects(
                    p, w_dict, cell_target, m_prof, basis="RT", precision=2
                )

        # Set PL.REV_OPS on every object & month as the exact sum of the 4 allocated revenue products
        # so that REV.CRUDE + REV.GAS + REV.VAP + REV.OTHER_OP == PL.REV_OPS at object, segment, and FY levels.
        for oid in rev_objs_all:
            alloc_m[(oid, "PL.REV_OPS")] = np.round(
                sum(alloc_m.get((oid, p), np.zeros(12)) for p in rev_products), 2
            )
            basis_map[(oid, "PL.REV_OPS")] = "RT"

        # ------------------------------------------------------------------
        # 3. Non-interest Other Income (SPEC-05 §4.C, §6.3)
        # ------------------------------------------------------------------
        oi_non_int = round(tmap["PL.OTHER_INCOME"] - tmap["SEG.INT_DIV"], 2)
        rev_off = tmap["SEG.REV.OFF"]
        rev_on = tmap["SEG.REV.ON"]
        rev_tot = rev_off + rev_on
        oi_unalloc = round(oi_non_int * 0.10, 2)
        oi_off = round((oi_non_int - oi_unalloc) * (rev_off / rev_tot), 2)
        oi_on = round(oi_non_int - oi_unalloc - oi_off, 2)
        oi_seg_map = {
            "Offshore": oi_off,
            "Onshore": oi_on,
            "Unallocated": oi_unalloc,
        }

        for seg in ["Offshore", "Onshore"]:
            seg_oids = [
                oid for oid in rev_objs_all if obj_meta[oid]["segment"] == seg
            ]
            w_dict = {
                oid: float(np.sum(alloc_m.get((oid, "PL.REV_OPS"), np.zeros(12))))
                for oid in seg_oids
            }
            m_prof = {oid: alloc_m.get((oid, "PL.REV_OPS"), np.ones(12)) for oid in seg_oids}
            allocate_line_to_objects(
                "OTHER_INCOME_SEGMENT",
                w_dict,
                oi_seg_map[seg],
                m_prof,
                basis="RT",
                precision=2,
            )
            allocate_line_to_objects(
                "PL.OTHER_INCOME",
                w_dict,
                oi_seg_map[seg],
                m_prof,
                basis="RT",
                precision=2,
            )

        allocate_line_to_objects(
            "OTHER_INCOME_SEGMENT",
            {"CO-HQ": 1.0},
            oi_unalloc,
            {"CO-HQ": np.ones(12)},
            basis="RT",
            precision=2,
        )
        allocate_line_to_objects(
            "PL.OTHER_INCOME",
            {"CO-HQ": 1.0},
            oi_unalloc,
            {"CO-HQ": np.ones(12)},
            basis="RT",
            precision=2,
        )
        allocate_line_to_objects(
            "PL.OTHER_INCOME",
            {"CO-TREASURY": 1.0},
            tmap["SEG.INT_DIV"],
            {"CO-TREASURY": np.ones(12)},
            basis="R",
            precision=2,
        )

        # ------------------------------------------------------------------
        # 4. Costs Two-Way RAS: Segment (3) x Nature (SPEC-05 §6.3)
        # ------------------------------------------------------------------
        # Pinned natures (handled directly from Note 44.4 / Note 44.5 / P2H.5 staff):
        #   - PL.DDA (SEG.DDA.OFF, SEG.DDA.ON, SEG.DDA.UNALLOC)
        #   - N37.IMPAIRMENT_NET (SEG.IMP.OFF, SEG.IMP.ON, SEG.IMP.UNALLOC)
        #   - PL.PROVISIONS (SEG.WO.OFF, SEG.WO.ON, SEG.WO.UNALLOC)
        #   - N35.STAFF_EXPENDITURE (from PY_CLUSTER_EXP.csv)
        #   - PL.INVENTORY_CHANGE (assigned to Unallocated CO-HQ so field opex is non-negative)
        #   - PL.PURCHASES_TRADED (assigned to plants by VAP share)
        # Unpinned natures in 3 x K RAS:
        #   - 23 Note 35 lines (all except N35.STAFF_EXPENDITURE)
        #   - PL.EXPL_SURVEY, PL.EXPL_WELLS
        ras_natures = (
            NOTE35_LEVIES
            + [c for c in NOTE35_OPEX if c != "N35.STAFF_EXPENDITURE"]
            + ["PL.EXPL_SURVEY", "PL.EXPL_WELLS"]
        )
        # Include N35.STAFF_EXPENDITURE as column 0 (pinned) in the RAS matrix!
        all_ras_cols = ["N35.STAFF_EXPENDITURE"] + ras_natures
        n_cols = len(all_ras_cols)

        # Build object-level driver weights for each column
        obj_cost_weights = {col: {} for col in all_ras_cols}

        # Column 0: N35.STAFF_EXPENDITURE from PY_CLUSTER_EXP
        raw_staff_obj = {
            oid: float(np.sum(m_staff[oid])) for oid in rev_objs_all
        }
        raw_staff_sum = sum(raw_staff_obj.values())
        staff_scale = (
            tmap["N35.STAFF_EXPENDITURE"] / raw_staff_sum
            if raw_staff_sum > 0
            else 1.0
        )
        for oid in objs:
            obj_cost_weights["N35.STAFF_EXPENDITURE"][oid] = (
                raw_staff_obj.get(oid, 0.0) * staff_scale
            )

        # Remaining columns: physical driver * segment prior * maturity factor
        for col in ras_natures:
            cfg = driver_cfg.get(col, {})
            d_type = cfg.get("driver", "production_boe")
            p_off = float(cfg.get("offshore_prior", 1.0))
            p_on = float(cfg.get("onshore_prior", 1.0))
            p_un = float(cfg.get("unallocated_prior", 0.0))

            for oid in objs:
                otype = obj_meta[oid]["object_type"]
                seg = obj_meta[oid]["segment"]
                mat = maturity_map.get(obj_meta[oid].get("maturity", "mature"), 1.0)
                seg_prior = (
                    p_off
                    if seg == "Offshore"
                    else p_on
                    if seg == "Onshore"
                    else p_un
                )

                if col in ("PL.EXPL_SURVEY", "PL.EXPL_WELLS"):
                    if otype == "exploration":
                        obj_cost_weights[col][oid] = (
                            exp_basin_weights.get(oid, 0.1) * seg_prior
                        )
                    else:
                        obj_cost_weights[col][oid] = 0.0
                elif col in CORPORATE_NATURES:
                    if oid == "CO-HQ":
                        # Put unallocated share on CO-HQ
                        obj_cost_weights[col][oid] = p_un
                    elif otype in ("field", "jv_share", "plant"):
                        rev_share = float(
                            np.sum(alloc_m.get((oid, "PL.REV_OPS"), np.zeros(12)))
                        ) / max(tmap["PL.REV_OPS"], 1.0)
                        obj_cost_weights[col][oid] = rev_share * (1.0 - p_un)
                    else:
                        obj_cost_weights[col][oid] = 0.0
                else:
                    # Production / Field / Levy natures: only on field, jv_share, plant
                    if otype not in ("field", "jv_share", "plant"):
                        obj_cost_weights[col][oid] = 0.0
                        continue
                    if d_type == "wellhead_value":
                        base_d = float(
                            np.sum(alloc_m.get((oid, "REV.CRUDE"), 0.0))
                            + np.sum(alloc_m.get((oid, "REV.GAS"), 0.0))
                        )
                    elif d_type == "oil_sales_mt":
                        base_d = float(np.sum(m_oil_sales[oid]))
                    elif d_type == "oil_production_mt":
                        base_d = float(np.sum(m_oil_mt[oid] + m_cond_mt[oid]))
                    elif d_type == "active_producing_wells":
                        base_d = float(np.sum(m_wells[oid])) * mat
                    elif d_type == "water_produced_m3":
                        base_d = float(np.sum(m_water[oid])) * mat
                    elif d_type == "water_and_flare":
                        base_d = (
                            float(np.sum(m_water[oid])) / 1e5
                            + float(np.sum(m_flare[oid])) * 10.0
                        ) * mat
                    elif d_type == "liquids_handled":
                        base_d = (
                            float(np.sum(m_oil_mt[oid]))
                            + float(np.sum(m_water[oid])) * 0.2
                        ) * mat
                    elif d_type == "sales_boe":
                        base_d = float(
                            np.sum(m_oil_sales[oid]) * 7.33
                            + np.sum(m_gas_sales[oid]) * 7330.0
                        )
                    else:
                        base_d = float(np.sum(m_boe[oid])) * mat
                    obj_cost_weights[col][oid] = max(base_d * seg_prior, 0.0)

        # Build 3 x n_cols seed matrix (rows: Offshore, Onshore, Unallocated)
        cost_seed_mat = np.zeros((3, n_cols), dtype=float)
        pinned_mask = np.zeros((3, n_cols), dtype=bool)
        col_targets = np.array([tmap[c] for c in all_ras_cols], dtype=float)

        # Column 0 is N35.STAFF_EXPENDITURE (pinned)
        for s_i, seg in enumerate(segments):
            cost_seed_mat[s_i, 0] = sum(
                obj_cost_weights["N35.STAFF_EXPENDITURE"][oid]
                for oid in objs
                if obj_meta[oid]["segment"] == seg
            )
        pinned_mask[:, 0] = True

        for j in range(1, n_cols):
            col = all_ras_cols[j]
            c_tot = col_targets[j]
            if abs(c_tot) < 1e-12:
                cost_seed_mat[:, j] = 0.0
                pinned_mask[:, j] = True
                continue
            raw_seg = np.array(
                [
                    sum(
                        obj_cost_weights[col][oid]
                        for oid in objs
                        if obj_meta[oid]["segment"] == seg
                    )
                    for seg in segments
                ],
                dtype=float,
            )
            cost_seed_mat[:, j] = c_tot * (raw_seg / np.sum(raw_seg))
            if col not in CORPORATE_NATURES:
                # Non-corporate natures have 0 in Unallocated; pin (2, j) at 0
                pinned_mask[2, j] = True

        # Compute exact Segment Cost row targets for the RAS columns
        # Total SegCost_s = SegRev_s + OI_s - SegResult_s
        tot_seg_cost = {
            "Offshore": tmap["SEG.REV.OFF"] + oi_seg_map["Offshore"] - tmap["SEG.RES.OFF"],
            "Onshore": tmap["SEG.REV.ON"] + oi_seg_map["Onshore"] - tmap["SEG.RES.ON"],
            "Unallocated": 0.0 + oi_seg_map["Unallocated"] - tmap["SEG.UNALLOC"],
        }

        # Pinned non-Note35 items by segment:
        # 1. PL.DDA (SEG.DDA.*)
        # 2. N37.IMPAIRMENT_NET (SEG.IMP.*)
        # 3. PL.PROVISIONS (SEG.WO.*)
        # 4. PL.PURCHASES_TRADED (allocated to plants: 85% Offshore, 15% Onshore)
        # 5. PL.INVENTORY_CHANGE (allocated to CO-HQ Unallocated if negative, or Offshore/Onshore if positive,
        #    Wait: let's put PL.INVENTORY_CHANGE on CO-HQ Unallocated or split 55% Offshore / 45% Onshore!)
        purch_tot = tmap["PL.PURCHASES_TRADED"]
        purch_off = round(purch_tot * 0.85, 2)
        purch_on = round(purch_tot - purch_off, 2)

        inv_tot = tmap["PL.INVENTORY_CHANGE"]
        inv_off = round(inv_tot * 0.55, 2)
        inv_on = round(inv_tot - inv_off, 2)

        # Exceptional items (negative cost = income, positive cost = expense):
        # In Note 44, FY20/FY21/FY23 exceptional items are inside Offshore/Onshore segment results
        excep_cost_tot = -tmap.get("PL.EXCEPTIONAL", 0.0)
        excep_cost_off = round(excep_cost_tot * (rev_off / rev_tot), 2)
        excep_cost_on = round(excep_cost_tot - excep_cost_off, 2)

        non_ras_pinned = {
            "Offshore": (
                tmap["SEG.DDA.OFF"]
                + tmap["SEG.IMP.OFF"]
                + tmap["SEG.WO.OFF"]
                + purch_off
                + inv_off
                + excep_cost_off
            ),
            "Onshore": (
                tmap["SEG.DDA.ON"]
                + tmap["SEG.IMP.ON"]
                + tmap["SEG.WO.ON"]
                + purch_on
                + inv_on
                + excep_cost_on
            ),
            "Unallocated": (
                tmap["SEG.DDA.UNALLOC"]
                + tmap["SEG.IMP.UNALLOC"]
                + tmap["SEG.WO.UNALLOC"]
            ),
        }

        row_targets = np.array(
            [tot_seg_cost[s] - non_ras_pinned[s] for s in segments], dtype=float
        )

        # Align seed row sums with row_targets on unpinned entries so priors are well-calibrated
        # and ras_fit converges cleanly in <50 iterations with factors near 1.0:
        cost_fitted_mat = ras_fit(
            cost_seed_mat,
            row_targets,
            col_targets,
            tol=1e-9,
            max_iter=1000,
            pinned_mask=pinned_mask,
        )

        # Record audit rows for all 24 Note 35 + Exploration lines
        for j, col in enumerate(all_ras_cols):
            for s_i, seg in enumerate(segments):
                s_val = float(cost_seed_mat[s_i, j])
                f_val = float(cost_fitted_mat[s_i, j])
                if s_val == 0.0 and f_val == 0.0:
                    continue
                factor = f_val / s_val if abs(s_val) > 1e-12 else 1.0
                audit_rows.append(
                    {
                        "fy": fy,
                        "segment": seg,
                        "nature": col,
                        "seed": round(s_val, 4),
                        "ras_factor": round(factor, 6),
                        "final": round(f_val, 4),
                    }
                )
                if col == "N35.STAFF_EXPENDITURE":
                    audit_rows.append(
                        {
                            "fy": fy,
                            "segment": seg,
                            "nature": "staff_expenditure",
                            "seed": round(s_val, 4),
                            "ras_factor": round(factor, 6),
                            "final": round(f_val, 4),
                        }
                    )

        # Down-allocate each RAS column to objects with exact rounding at both segment and company levels
        # To guarantee that both column sums (by nature) AND row sums (by segment) are exact to ₹0.01 mn
        # after rounding, we round the 3 x n_cols matrix cells so each column sums to col_targets[j]
        # and adjust the largest corporate nature (N35.GAE) across segments by any 0.01 rounding residual.
        rounded_mat = np.zeros_like(cost_fitted_mat)
        for j, col in enumerate(all_ras_cols):
            c_tot = round(float(col_targets[j]), 2)
            if abs(c_tot) < 1e-12:
                continue
            rounded_mat[:, j] = largest_remainder_round(
                cost_fitted_mat[:, j], c_tot, precision=2
            )

        # Check row sum residuals after column rounding and absorb into N35.GAE / N35.OTHER_PRODUCTION_EXP
        gae_idx = all_ras_cols.index("N35.GAE")
        other_prod_idx = all_ras_cols.index("N35.OTHER_PRODUCTION_EXP")
        row_Targets_2d = np.array([round(rt, 2) for rt in row_targets])
        row_diffs = np.round(row_Targets_2d - np.sum(rounded_mat, axis=1), 2)
        # Since sum(row_Targets_2d) == sum(col_targets), sum(row_diffs) == 0.00!
        # Adjust Unallocated via N35.GAE and Offshore/Onshore via N35.GAE
        if abs(row_diffs[2]) > 0:
            rounded_mat[2, gae_idx] = round(rounded_mat[2, gae_idx] + row_diffs[2], 2)
            rounded_mat[0, gae_idx] = round(rounded_mat[0, gae_idx] - row_diffs[2], 2)
            row_diffs = np.round(row_Targets_2d - np.sum(rounded_mat, axis=1), 2)
        if abs(row_diffs[0]) > 0:
            rounded_mat[0, other_prod_idx] = round(
                rounded_mat[0, other_prod_idx] + row_diffs[0], 2
            )
            rounded_mat[1, other_prod_idx] = round(
                rounded_mat[1, other_prod_idx] - row_diffs[0], 2
            )

        for j, col in enumerate(all_ras_cols):
            for s_i, seg in enumerate(segments):
                cell_target = round(float(rounded_mat[s_i, j]), 2)
                if abs(cell_target) < 1e-12:
                    continue
                seg_oids = [
                    oid
                    for oid in objs
                    if obj_meta[oid]["segment"] == seg
                    and obj_cost_weights[col].get(oid, 0.0) > 0
                ]
                w_dict = {oid: obj_cost_weights[col][oid] for oid in seg_oids}
                if col == "N35.STAFF_EXPENDITURE":
                    m_prof = {oid: m_staff[oid] for oid in seg_oids}
                elif col in NOTE35_LEVIES:
                    m_prof = {
                        oid: alloc_m.get((oid, "PL.REV_OPS"), m_boe[oid])
                        for oid in seg_oids
                    }
                else:
                    m_prof = {oid: m_boe[oid] for oid in seg_oids}
                allocate_line_to_objects(
                    col, w_dict, cell_target, m_prof, basis="RT", precision=2
                )

        # ------------------------------------------------------------------
        # 5. Pinned Segment Costs: PL.DDA, N37.IMPAIRMENT_NET, PL.PROVISIONS,
        #    PL.PURCHASES_TRADED, PL.INVENTORY_CHANGE (SPEC-05 §4.F, FLD-R06, FLD-R07)
        # ------------------------------------------------------------------
        for seg, dda_code, imp_code, wo_code in [
            ("Offshore", "SEG.DDA.OFF", "SEG.IMP.OFF", "SEG.WO.OFF"),
            ("Onshore", "SEG.DDA.ON", "SEG.IMP.ON", "SEG.WO.ON"),
            ("Unallocated", "SEG.DDA.UNALLOC", "SEG.IMP.UNALLOC", "SEG.WO.UNALLOC"),
        ]:
            if seg == "Unallocated":
                w_dict = {"CO-HQ": 1.0}
                m_prof = {"CO-HQ": np.ones(12)}
            else:
                seg_oids = [
                    oid for oid in rev_objs_all if obj_meta[oid]["segment"] == seg
                ]
                w_dict = {
                    oid: max(float(np.sum(m_boe[oid])), 1.0) for oid in seg_oids
                }
                m_prof = {oid: m_boe[oid] for oid in seg_oids}

            allocate_line_to_objects(
                "PL.DDA", w_dict, tmap[dda_code], m_prof, basis="RT", precision=2
            )
            allocate_line_to_objects(
                "N37.IMPAIRMENT_NET",
                w_dict,
                tmap[imp_code],
                m_prof,
                basis="RT",
                precision=2,
            )
            allocate_line_to_objects(
                "PL.PROVISIONS",
                w_dict,
                tmap[wo_code],
                m_prof,
                basis="RT",
                precision=2,
            )

            for nat, code in [
                ("PL.DDA", dda_code),
                ("N37.IMPAIRMENT_NET", imp_code),
                ("PL.PROVISIONS", wo_code),
            ]:
                val = float(tmap[code])
                if abs(val) > 1e-12:
                    audit_rows.append(
                        {
                            "fy": fy,
                            "segment": seg,
                            "nature": nat,
                            "seed": round(val, 4),
                            "ras_factor": 1.0,
                            "final": round(val, 4),
                        }
                    )

        # Purchases traded -> plants (Offshore WC-URN/WC-HAZ, Onshore WC-DAH)
        allocate_line_to_objects(
            "PL.PURCHASES_TRADED",
            {"WC-URN": 0.45, "WC-HAZ": 0.40},
            purch_off,
            {"WC-URN": np.ones(12), "WC-HAZ": np.ones(12)},
            basis="RT",
            precision=2,
        )
        allocate_line_to_objects(
            "PL.PURCHASES_TRADED",
            {"WC-DAH": 1.0},
            purch_on,
            {"WC-DAH": np.ones(12)},
            basis="RT",
            precision=2,
        )

        # Inventory change -> Offshore / Onshore fields proportional to crude production
        for seg, inv_val in [("Offshore", inv_off), ("Onshore", inv_on)]:
            seg_oids = [
                oid for oid in prod_field_jv if obj_meta[oid]["segment"] == seg
            ]
            w_dict = {
                oid: max(float(np.sum(m_oil_mt[oid] + m_cond_mt[oid])), 1.0)
                for oid in seg_oids
            }
            m_prof = {oid: m_boe[oid] for oid in seg_oids}
            allocate_line_to_objects(
                "PL.INVENTORY_CHANGE",
                w_dict,
                inv_val,
                m_prof,
                basis="RT",
                precision=2,
            )

        # ------------------------------------------------------------------
        # 6. Non-Operating Corporate Lines, Capex, Total Emp Cost, Segment Result & PBT
        # ------------------------------------------------------------------
        allocate_line_to_objects(
            "PL.FIN_COST",
            {"CO-FIN": 1.0},
            tmap["PL.FIN_COST"],
            {"CO-FIN": np.ones(12)},
            basis="R",
            precision=2,
        )
        allocate_line_to_objects(
            "SEG.INT_DIV",
            {"CO-TREASURY": 1.0},
            tmap["SEG.INT_DIV"],
            {"CO-TREASURY": np.ones(12)},
            basis="R",
            precision=2,
        )
        allocate_line_to_objects(
            "SEG.UNALLOC",
            {"CO-HQ": 1.0},
            tmap["SEG.UNALLOC"],
            {"CO-HQ": np.ones(12)},
            basis="R",
            precision=2,
        )
        for seg, ex_val in [("Offshore", -excep_cost_off), ("Onshore", -excep_cost_on)]:
            seg_oids = [
                oid for oid in rev_objs_all if obj_meta[oid]["segment"] == seg
            ]
            w_dict = {
                oid: float(np.sum(alloc_m.get((oid, "PL.REV_OPS"), np.zeros(12))))
                for oid in seg_oids
            }
            m_prof = {oid: alloc_m.get((oid, "PL.REV_OPS"), np.ones(12)) for oid in seg_oids}
            allocate_line_to_objects(
                "PL.EXCEPTIONAL",
                w_dict,
                ex_val,
                m_prof,
                basis="R",
                precision=2,
            )

        # Capex (FLD-R13)
        capex_weights = {
            oid: max(float(np.sum(m_boe[oid])), 1.0)
            * (1.35 if obj_meta[oid]["segment"] == "Offshore" else 0.90)
            for oid in rev_objs_all
        }
        allocate_line_to_objects(
            "CAPEX.TOTAL",
            capex_weights,
            tmap["CAPEX.TOTAL"],
            {oid: m_boe[oid] for oid in rev_objs_all},
            basis="RT",
            precision=2,
        )

        # Total Employee Benefit Expense (N351.EMP_TOTAL)
        emp_tot_weights = {
            oid: max(float(np.sum(m_emp_tot[oid])), 1.0) for oid in rev_objs_all
        }
        allocate_line_to_objects(
            "N351.EMP_TOTAL",
            emp_tot_weights,
            tmap["N351.EMP_TOTAL"],
            {oid: m_emp_tot[oid] for oid in rev_objs_all},
            basis="RT",
            precision=2,
        )

        # Compute SEGMENT_RESULT_CONTRIB and PL.PBT (PBT_CONTRIB) on every object & month
        cost_lines_all = (
            ALL_NOTE35
            + [
                "PL.EXPL_SURVEY",
                "PL.EXPL_WELLS",
                "PL.DDA",
                "N37.IMPAIRMENT_NET",
                "PL.PROVISIONS",
                "PL.PURCHASES_TRADED",
                "PL.INVENTORY_CHANGE",
            ]
        )
        for oid in objs:
            if oid in ("CO-FIN", "CO-TREASURY"):
                seg_res_m = np.zeros(12)
            else:
                rev_m = alloc_m.get((oid, "PL.REV_OPS"), np.zeros(12))
                oi_m = alloc_m.get((oid, "OTHER_INCOME_SEGMENT"), np.zeros(12))
                ex_m = alloc_m.get((oid, "PL.EXCEPTIONAL"), np.zeros(12))
                c_m = sum(
                    alloc_m.get((oid, cl), np.zeros(12)) for cl in cost_lines_all
                )
                seg_res_m = np.round(rev_m + oi_m + ex_m - c_m, 2)
            alloc_m[(oid, "SEGMENT_RESULT_CONTRIB")] = seg_res_m
            basis_map[(oid, "SEGMENT_RESULT_CONTRIB")] = "D"

            if oid == "CO-FIN":
                pbt_m = -alloc_m.get((oid, "PL.FIN_COST"), np.zeros(12))
            elif oid == "CO-TREASURY":
                pbt_m = alloc_m.get((oid, "SEG.INT_DIV"), np.zeros(12))
            else:
                pbt_m = seg_res_m
            alloc_m[(oid, "PL.PBT")] = pbt_m
            basis_map[(oid, "PL.PBT")] = "D"

        # Emit monthly records for this FY
        for (oid, lcode), m_vals in sorted(alloc_m.items()):
            if np.all(np.abs(m_vals) < 1e-12):
                continue
            b_tag = basis_map[(oid, lcode)]
            for m_idx, m_str in enumerate(months):
                val = float(m_vals[m_idx])
                if abs(val) < 1e-12:
                    continue
                copa_rows.append(
                    {
                        "fy": fy,
                        "month": m_str,
                        "object_id": oid,
                        "line_code": lcode,
                        "amount_inr_mn": val,
                        "basis": b_tag,
                    }
                )

    df_copa = pd.DataFrame(copa_rows)
    df_audit = pd.DataFrame(audit_rows)
    df_copa.to_csv(LANDING_SAP / "CO_PA_v3.csv", index=False)
    df_audit.to_csv(LANDING_SAP / "field_alloc_audit.csv", index=False)
    print(
        f"Generated CO_PA_v3.csv ({len(df_copa)} rows) and field_alloc_audit.csv ({len(df_audit)} rows)"
    )


if __name__ == "__main__":
    run_allocation()
