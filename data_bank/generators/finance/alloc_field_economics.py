import sys
from pathlib import Path
import yaml
import numpy as np
import pandas as pd
from ras import ras_fit, largest_remainder_round

DATA_BANK_DIR = Path(__file__).resolve().parent.parent.parent
WORLD_BIBLE = DATA_BANK_DIR / "world_bible"
LANDING_SAP = DATA_BANK_DIR / "landing" / "sap"
DB_EXPORTS = DATA_BANK_DIR / "landing" / "db_exports"

def load_data():
    with open(WORLD_BIBLE / "reference" / "cost_objects.yaml") as f:
        cost_objects = yaml.safe_load(f)["cost_objects"]
    with open(WORLD_BIBLE / "reference" / "alloc_drivers.yaml") as f:
        alloc_drivers = yaml.safe_load(f)
    targets = pd.read_csv(WORLD_BIBLE / "reference" / "real_targets" / "field_econ_targets_fy.csv")
    prod = pd.read_csv(DB_EXPORTS / "production_monthly.csv")
    
    py_exp = pd.read_csv(LANDING_SAP / "PY_CLUSTER_EXP.csv")
    
    return cost_objects, alloc_drivers, targets, prod, py_exp

def run_allocation():
    cost_objects, alloc_drivers, targets, prod, py_exp = load_data()
    fys = targets['fiscal_year'].unique()
    copa_records = []
    audit_records = []
    
    obj_to_seg = {obj['object_id']: obj['segment'] for obj in cost_objects}
    obj_to_wc = {obj['object_id']: obj.get('wc_id', 'WC-DEL') for obj in cost_objects}
    
    segments = sorted(list(set(obj_to_seg.values())))
    objs = sorted(list(obj_to_seg.keys()))
    
    for fy in fys:
        print(f"Processing {fy}...", flush=True)
        fy_targets = targets[targets['fiscal_year'] == fy]
        target_map = dict(zip(fy_targets['line_code'].str.upper(), fy_targets['value']))
        line_code_map = dict(zip(fy_targets['line_code'].str.upper(), fy_targets['line_code']))
        
        segment_mappings = [
            ('SEG.REV.OFF', 'Offshore', 'PL.REV_OPS'),
            ('SEG.REV.ON', 'Onshore', 'PL.REV_OPS'),
            ('SEG.DDA.OFF', 'Offshore', 'PL.DDA'),
            ('SEG.DDA.ON', 'Onshore', 'PL.DDA'),
            ('SEG.DDA.UNALLOC', 'Unallocated', 'PL.DDA'),
        ]
        
        handled_line_codes = ['PL.REV_OPS', 'PL.DDA']
        
        fy_py = py_exp[py_exp['fiscal_year'] == fy]
        wc_staff_seed = fy_py.groupby('wc_id')[['cost_note35_a_inr', 'cost_note35_b_inr', 'cost_note35_c_inr', 'cost_note35_d_inr', 'cost_note35_e_inr', 'cost_note35_f_inr']].sum().sum(axis=1) / 1e7
        
        fy_prod = prod[prod['fiscal_year'] == fy]
        fy_obj_prod = fy_prod.groupby('field_id')['total_production_boe'].sum().to_dict()
        fy_obj_wells = fy_prod.groupby('field_id')['active_producing_wells'].sum().to_dict()
        
        start_year = int("20" + fy[2:]) - 1
        months = [f"{start_year + (1 if m > 12 else 0)}-{((m - 1) % 12) + 1:02d}" for m in range(4, 16)]
        
        # Precompute month prod for this FY
        fy_obj_month_prod = {}
        for obj in objs:
            mp = fy_prod[fy_prod['field_id'] == obj].groupby('month')['total_production_boe'].sum().values
            if len(mp) == 12 and np.sum(mp) > 0:
                fy_obj_month_prod[obj] = mp
            else:
                fy_obj_month_prod[obj] = np.ones(12)
                
        for nature in target_map.keys():
            if nature in handled_line_codes or nature.startswith('SEG.'):
                continue
            
            total_target = target_map[nature]
            seed = np.zeros(len(objs))
            for i, obj in enumerate(objs):
                wc = obj_to_wc.get(obj, 'WC-DEL')
                if 'STAFF' in nature or 'N35' in nature:
                    wc_tot_wells = sum(fy_obj_wells.get(o, 1) for o, w in obj_to_wc.items() if w == wc)
                    wells = fy_obj_wells.get(obj, 1) if obj in fy_obj_wells else 1
                    seed[i] = wc_staff_seed.get(wc, 0) * (wells / wc_tot_wells if wc_tot_wells else 0)
                else:
                    seed[i] = fy_obj_prod.get(obj, 1)
            
            if np.sum(seed) == 0:
                seed = np.ones(len(objs))
                
            factor = total_target / np.sum(seed) if np.sum(seed) > 0 else 1.0
            obj_allocated = largest_remainder_round(seed * factor, total_target, precision=2)
            
            for i, obj_id in enumerate(objs):
                obj_total = obj_allocated[i]
                if obj_total == 0: continue
                month_seed = fy_obj_month_prod[obj_id]
                
                month_alloc = largest_remainder_round(month_seed / np.sum(month_seed) * obj_total, obj_total, precision=2)
                
                for m_idx, month_str in enumerate(months):
                    copa_records.append({
                        'fy': fy, 'month': month_str, 'object_id': obj_id,
                        'line_code': line_code_map[nature],
                        'amount_inr_mn': month_alloc[m_idx], 'basis': 'M'
                    })
                    
            for seg in segments:
                audit_records.append({
                    'fy': fy, 'segment': seg, 'nature': nature,
                    'seed': total_target / len(segments),
                    'ras_factor': 1.0, 'final': total_target / len(segments)
                })
                
        for seg_code, seg_name, line_code in segment_mappings:
            if seg_code in target_map:
                total_seg_target = target_map[seg_code]
                seg_objs = [obj for obj, s in obj_to_seg.items() if s == seg_name]
                if not seg_objs: continue
                
                seed = np.zeros(len(seg_objs))
                for i, obj in enumerate(seg_objs):
                    seed[i] = fy_obj_prod.get(obj, 1)
                        
                if np.sum(seed) == 0: seed = np.ones(len(seg_objs))
                factor = total_seg_target / np.sum(seed) if np.sum(seed) > 0 else 1.0
                
                obj_allocated = largest_remainder_round(seed * factor, total_seg_target, precision=2)
                
                for i, obj_id in enumerate(seg_objs):
                    obj_total = obj_allocated[i]
                    if obj_total == 0: continue
                    month_seed = fy_obj_month_prod[obj_id]
                        
                    month_alloc = largest_remainder_round(month_seed / np.sum(month_seed) * obj_total, obj_total, precision=2)
                    
                    for m_idx, month_str in enumerate(months):
                        copa_records.append({
                            'fy': fy, 'month': month_str, 'object_id': obj_id,
                            'line_code': line_code,
                            'amount_inr_mn': month_alloc[m_idx], 'basis': 'M'
                        })

    pd.DataFrame(copa_records).to_csv(LANDING_SAP / "CO_PA_v3.csv", index=False)
    pd.DataFrame(audit_records).to_csv(LANDING_SAP / "field_alloc_audit.csv", index=False)

if __name__ == "__main__":
    run_allocation()