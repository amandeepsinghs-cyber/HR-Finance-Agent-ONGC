def get_financial_coverage_fys() -> list[str]:
    # In a real environment, this would read from hrfin_gold.v_fin_coverage
    # or a cached v_fin_coverage.json manifest (SPEC-11).
    # RECORD: using v_fin_coverage snapshot fallback as coverage manifest is not yet available
    return ["FY17", "FY18", "FY19", "FY20", "FY21", "FY22", "FY23", "FY24", "FY25", "FY26"]
