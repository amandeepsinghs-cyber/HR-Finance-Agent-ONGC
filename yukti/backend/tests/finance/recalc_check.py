import os
import subprocess
import json
import openpyxl
from app.finance.dcf.xlsx_writer import write_dcf_xlsx
from app.finance.dcf.assumptions import defaults_from_ssot
from app.finance.dcf.run import run_dcf

def check_recalc():
    a = defaults_from_ssot([], [], "2026-10-23")
    res = run_dcf(a)
    
    file_path = "test_dcf_recalc.xlsx"
    write_dcf_xlsx(res, file_path)
    
    # Check if soffice is available
    has_soffice = subprocess.call("command -v soffice", shell=True, stdout=subprocess.DEVNULL) == 0

    if has_soffice:
        out_dir = "recalc_out"
        os.makedirs(out_dir, exist_ok=True)
        
        # Recalculate using soffice headless
        subprocess.run(["soffice", "--headless", "--convert-to", "xlsx", "--outdir", out_dir, file_path], check=True)
        
        recalc_path = os.path.join(out_dir, "test_dcf_recalc.xlsx")
        wb = openpyxl.load_workbook(recalc_path, data_only=True)
        
        calc_val = wb["Valuation"]["B15"].value
        py_val = res["per_share"].get("intrinsic_inr")
        
        if calc_val and py_val:
            assert abs(calc_val - py_val) < 0.1, f"Mismatch: {calc_val} vs {py_val}"
            print("Recalc check passed via soffice!")
    else:
        # Pure Python formula parity check when soffice is not installed
        print("soffice not found, running pure-Python formula parity check...")
        try:
            from tests.finance.evaluator import evaluate_dcf_excel
        except ImportError:
            import sys
            sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
            from tests.finance.evaluator import evaluate_dcf_excel
            
        wb = openpyxl.load_workbook(file_path)
        calc_val = evaluate_dcf_excel(wb, "Valuation!B15")
        py_val = res["per_share"].get("intrinsic_inr")
        
        assert abs(calc_val - py_val) < 0.01, f"Parity mismatch: {calc_val} vs {py_val}"
        print("Pure-Python recalc check passed!")
        
        # Proving parity with 3 Sensitivity grid cells
        # The grid is 9x9, WACC row 3 to 11, g col 2(B) to 10(J)
        # B2 is center? No, w_base is at row 7 (-4 to +4 -> +0 is at index 4, which is row 7)
        # Let's just pick 3 cells: C5, F7, J9
        s_c5 = evaluate_dcf_excel(wb, "Sensitivity!C5")
        s_f7 = evaluate_dcf_excel(wb, "Sensitivity!F7")
        s_j9 = evaluate_dcf_excel(wb, "Sensitivity!J9")
        
        grid = res["sensitivity"]["values_inr"]
        # C is col index 3 -> j=1 in 0..8
        # row 5 -> i=2 in 0..8
        py_c5 = grid[2][1]
        
        # F is col index 6 -> j=4
        # row 7 -> i=4
        py_f7 = grid[4][4]
        
        # J is col index 10 -> j=8
        # row 9 -> i=6
        py_j9 = grid[6][8]
        
        assert abs(s_c5 - py_c5) < 0.01, f"Sensitivity C5 mismatch: {s_c5} vs {py_c5}"
        assert abs(s_f7 - py_f7) < 0.01, f"Sensitivity F7 mismatch: {s_f7} vs {py_f7}"
        assert abs(s_j9 - py_j9) < 0.01, f"Sensitivity J9 mismatch: {s_j9} vs {py_j9}"
        
        # "proving changing wacc_pct in Assumptions changes Valuation!B15"
        calc_val_new = evaluate_dcf_excel(wb, "Valuation!B15", wacc_override=12.0)
        assert abs(calc_val_new - calc_val) > 1.0, f"wacc_pct override didn't change B15 enough: {calc_val} -> {calc_val_new}"
        
        print("Sensitivity parity and override check passed!")

    if os.path.exists(file_path): os.remove(file_path)

if __name__ == "__main__":
    check_recalc()
