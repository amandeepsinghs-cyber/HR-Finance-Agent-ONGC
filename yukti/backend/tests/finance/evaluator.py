import re
import openpyxl

def evaluate_dcf_excel(wb: openpyxl.Workbook, cell_str: str, wacc_override: float = None):
    assumptions = {}
    ws_a = wb["Assumptions"]
    for row in range(2, 100):
        k = ws_a[f"A{row}"].value
        if not k:
            break
        v = ws_a[f"B{row}"].value
        assumptions[k] = v
        
    if wacc_override is not None:
        assumptions["wacc_pct"] = wacc_override
        
    ws_f = wb["Forecast"]
    fcff_t = []
    fcff_vals = []
    col = 2
    while True:
        c_letter = openpyxl.utils.get_column_letter(col)
        t_val = ws_f[f"{c_letter}2"].value
        if t_val is None:
            break
        fcff_t.append(float(t_val))
        fcff_vals.append(float(ws_f[f"{c_letter}3"].value))
        col += 1

    last_f_val = fcff_vals[-1] if fcff_vals else 0
    list_len = len(fcff_vals)

    def resolve_ref(ref: str, current_sheet: str):
        ref = ref.replace("$", "")
        if "!" in ref:
            sheet, cell = ref.split("!")
            val = wb[sheet][cell].value
            if isinstance(val, str) and val.startswith("="):
                return eval_formula(val, sheet)
            return float(val)
        if ref in assumptions:
            return float(assumptions[ref])
        
        val = wb[current_sheet][ref].value
        if isinstance(val, str) and val.startswith("="):
            return eval_formula(val, current_sheet)
        return float(val)

    def eval_formula(expr: str, current_sheet: str):
        if not str(expr).startswith("="):
            return float(expr)
        expr = str(expr)[1:].replace(" ", "")
        
        # If it's the giant Sensitivity equation
        if "SUMPRODUCT" in expr and "/shares_outstanding" in expr:
            m_w = re.search(r'\(1\+([^/]+)/100\)\^Forecast', expr)
            w_ref = m_w.group(1)
            w_val = resolve_ref(w_ref, current_sheet)
            
            m_g = re.search(r'\*\(1\+([^/]+)/100\)', expr)
            g_ref = m_g.group(1)
            g_val = resolve_ref(g_ref, current_sheet)
            
            sumpv = sum(f / ((1 + w_val/100)**t) for f, t in zip(fcff_vals, fcff_t))
            tv = (last_f_val * (1 + g_val/100) / (w_val/100 - g_val/100)) / ((1 + w_val/100)**list_len)
            
            adj = (
                - float(assumptions["borrowings_inr_cr"])
                - float(assumptions["lease_liab_inr_cr"])
                - float(assumptions["decom_provision_inr_cr"])
                + float(assumptions["cash_and_equivalents_inr_cr"])
                + float(assumptions["srf_deposits_inr_cr"])
                + float(assumptions["listed_investments_inr_cr"]) * (1 - float(assumptions.get("holdco_discount_pct", 0))/100)
                + float(assumptions["unlisted_investments_inr_cr"])
            )
            return (sumpv + tv + adj) / float(assumptions["shares_outstanding"])

        if expr.startswith("SUMPRODUCT("):
            m = re.search(r'\(1\+([^/]+)/100\)', expr)
            w_val = resolve_ref(m.group(1), current_sheet)
            return sum(f / ((1 + w_val/100)**t) for f, t in zip(fcff_vals, fcff_t))
            
        vars_to_replace = sorted(list(assumptions.keys()) + [f"B{i}" for i in range(1, 20)], key=len, reverse=True)
        expr_replaced = expr
        expr_replaced = re.sub(r'Forecast!\$?[A-Z]+\$?3', str(last_f_val), expr_replaced)
        
        for v in vars_to_replace:
            if v in expr_replaced:
                try:
                    val = str(resolve_ref(v, current_sheet))
                    expr_replaced = re.sub(rf'\b{v}\b', val, expr_replaced)
                except:
                    pass
                
        expr_replaced = expr_replaced.replace("^", "**")
        try:
            return eval(expr_replaced)
        except Exception as e:
            raise ValueError(f"Failed to evaluate {expr_replaced} from {expr}: {e}")

    sheet, cell = cell_str.split("!")
    val = wb[sheet][cell].value
    return eval_formula(val, sheet)
