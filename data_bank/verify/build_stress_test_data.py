import json

# Define the 50 questions and their 2 followups
QUESTIONS = [
    # -------------------------------------------------------------
    # CMD (Q01 - Q25)
    # -------------------------------------------------------------
    {
        "num": 1,
        "persona": "CMD",
        "primary": {
            "text": "What is the correlation between water cut percentage and lifting cost across our top 10 producing onshore fields in FY26?",
            "kind": "primary (cross-silo)",
            "status": "ANSWERABLE",
            "sql": """
                SELECT field_name, asset_name, ROUND(AVG(water_cut_pct), 1) as avg_wc_pct, 
                       ROUND(AVG(lifting_cost_per_boe_usd), 2) as lifting_cost_usd, 
                       ROUND(SUM(water_handling_cost_inr_cr), 2) as water_handling_cr
                FROM hrfin_gold.mart_field_economics 
                WHERE fiscal_year = 'FY26' AND onshore_offshore = 'Onshore'
                GROUP BY 1, 2 ORDER BY avg_wc_pct DESC LIMIT 10
            """
        },
        "fu1": {
            "text": "Which fields in Mehsana and Ahmedabad have water cut exceeding 80%, and how much did they spend on water handling opex?",
            "kind": "drill_down",
            "status": "ANSWERABLE",
            "sql": """
                SELECT field_name, asset_name, ROUND(AVG(water_cut_pct), 1) as wc_pct, 
                       ROUND(SUM(water_handling_cost_inr_cr), 2) as water_handling_cr, 
                       ROUND(SUM(total_opex_inr_cr), 2) as total_opex_cr
                FROM hrfin_gold.mart_field_economics 
                WHERE fiscal_year = 'FY26' AND asset_name IN ('Mehsana Asset', 'Ahmedabad Asset')
                GROUP BY 1, 2 HAVING wc_pct > 80 ORDER BY wc_pct DESC
            """
        },
        "fu2": {
            "text": "How does the water handling cost per barrel in mature Gujarat fields compare with offshore Mumbai High?",
            "kind": "compare_or_so_what",
            "status": "ANSWERABLE",
            "sql": """
                SELECT asset_name, ROUND(SUM(water_handling_cost_inr_cr), 2) as total_water_cost_cr, 
                       ROUND(SUM(total_production_boe), 0) as total_boe,
                       ROUND(SUM(water_handling_cost_inr_cr) * 10000000 / NULLIF(SUM(total_production_boe), 0), 2) as water_cost_per_boe_inr
                FROM hrfin_gold.mart_field_economics 
                WHERE fiscal_year = 'FY26' AND asset_name IN ('Mehsana Asset', 'Ahmedabad Asset', 'Mumbai High Asset')
                GROUP BY 1
            """
        }
    },
    {
        "num": 2,
        "persona": "CMD",
        "primary": {
            "text": "Western Offshore aur Onshore assets mein kitne producing wells active hain and average downtime hours kitne hain?",
            "kind": "primary (operations)",
            "status": "ANSWERABLE",
            "sql": """
                SELECT onshore_offshore, COUNT(DISTINCT field_id) as fields_count, 
                       SUM(active_producing_wells) as active_wells, 
                       ROUND(SUM(well_downtime_hours), 0) as total_downtime_hrs, 
                       ROUND(AVG(operational_uptime_pct), 1) as avg_uptime_pct
                FROM hrfin_gold.mart_production_reserves 
                WHERE fiscal_year = 'FY26' GROUP BY 1
            """
        },
        "fu1": {
            "text": "What are the primary operational bottlenecks causing well downtime in Neelam & Heera asset?",
            "kind": "why",
            "status": "ANSWERABLE",
            "sql": """
                SELECT field_name, month, well_downtime_hours, operational_uptime_pct
                FROM hrfin_gold.mart_production_reserves 
                WHERE fiscal_year = 'FY26' AND asset_name LIKE '%Neelam%' AND well_downtime_hours > 0
                ORDER BY well_downtime_hours DESC LIMIT 5
            """
        },
        "fu2": {
            "text": "Agar hum Western Offshore mein 5% uptime improve karein, what is the estimated incremental liquids production?",
            "kind": "what_if",
            "status": "ANSWERABLE",
            "sql": """
                SELECT asset_name, ROUND(SUM(total_liquids_production_mt), 1) as curr_liquids_mt, 
                       ROUND(SUM(total_liquids_production_mt) * 0.05, 1) as est_incremental_mt_at_5pct_gain
                FROM hrfin_gold.mart_production_reserves 
                WHERE fiscal_year = 'FY26' AND onshore_offshore = 'Offshore'
                GROUP BY 1
            """
        }
    },
    {
        "num": 3,
        "persona": "CMD",
        "primary": {
            "text": "What is the ratio of contract workforce to regular employees in our major processing plants (Uran and Hazira)?",
            "kind": "primary (people+money)",
            "status": "ANSWERABLE",
            "sql": """
                SELECT wc_name, SUM(headcount) as contractor_count, 
                       MAX(regular_employee_count_matching) as regular_count, 
                       ROUND(SUM(headcount) / NULLIF(MAX(regular_employee_count_matching), 0), 2) as contractor_ratio, 
                       ROUND(SUM(monthly_cost_inr)/10000000, 2) as annual_contract_spend_cr 
                FROM hrfin_gold.mart_contract_workforce 
                WHERE fiscal_year = 'FY26' AND (wc_name LIKE '%Hazira%' OR wc_name LIKE '%Uran%') 
                GROUP BY 1
            """
        },
        "fu1": {
            "text": "Hazira Plant contract spend kitna hai and what percentage goes to Micro and Small Enterprise (MSE) vendors?",
            "kind": "drill_down",
            "status": "ANSWERABLE",
            "sql": """
                SELECT is_mse_vendor, COUNT(DISTINCT vendor_id) as vendors, 
                       SUM(headcount) as total_contractors, 
                       ROUND(SUM(monthly_cost_inr)/10000000, 2) as cost_cr 
                FROM hrfin_gold.mart_contract_workforce 
                WHERE fiscal_year = 'FY26' AND wc_name LIKE '%Hazira%' 
                GROUP BY 1
            """
        },
        "fu2": {
            "text": "Are any contract agencies deployed at Hazira or Uran operating with non-compliant CLRA licenses?",
            "kind": "risk_compliance",
            "status": "ANSWERABLE",
            "sql": """
                SELECT wc_name, clra_compliance_status, COUNT(DISTINCT contract_id) as contracts_count 
                FROM hrfin_gold.mart_contract_workforce 
                WHERE (wc_name LIKE '%Hazira%' OR wc_name LIKE '%Uran%') 
                GROUP BY 1, 2
            """
        }
    },
    {
        "num": 4,
        "persona": "CMD",
        "primary": {
            "text": "MoPNG review prep: How many exploratory wells were drilled vs exploratory drilling expenditure across FY24, FY25, and FY26?",
            "kind": "primary (ministry_prep)",
            "status": "ANSWERABLE",
            "sql": """
                SELECT fiscal_year, SUM(CASE WHEN well_type = 'Exploratory' THEN 1 ELSE 0 END) as exploratory_wells, 
                       ROUND(SUM(CASE WHEN well_type = 'Exploratory' THEN drilling_cost_inr_cr ELSE 0 END), 2) as exploratory_cost_cr 
                FROM hrfin_gold.mart_production_reserves 
                GROUP BY 1 ORDER BY 1
            """
        },
        "fu1": {
            "text": "Of the exploratory wells drilled in FY26, what was the discovery success rate versus dry wells?",
            "kind": "drill_down",
            "status": "ANSWERABLE",
            "sql": """
                SELECT result_status, COUNT(*) as wells_count, 
                       ROUND(SUM(drilling_cost_inr_cr), 2) as cost_cr 
                FROM hrfin_gold.mart_production_reserves 
                WHERE fiscal_year = 'FY26' AND well_type = 'Exploratory' 
                GROUP BY 1
            """
        },
        "fu2": {
            "text": "What was the average finding cost per BOE across Frontier vs KG basins over the last 3 years?",
            "kind": "compare_or_so_what",
            "status": "ANSWERABLE",
            "sql": """
                SELECT basin_name, fiscal_year, ROUND(AVG(finding_cost_usd_per_boe), 2) as avg_finding_cost_usd, 
                       ROUND(AVG(reserve_replacement_ratio_rrr_2p), 2) as avg_rrr 
                FROM hrfin_gold.mart_production_reserves 
                WHERE basin_name IN ('KG-PG Basin', 'Frontier Basin') 
                GROUP BY 1, 2 ORDER BY 1, 2
            """
        }
    },
    {
        "num": 5,
        "persona": "CMD",
        "primary": {
            "text": "What is our cumulative capital expenditure in renewable energy projects under ONGC Green Limited (OGL), and current installed capacity?",
            "kind": "primary (energy_transition)",
            "status": "ANSWERABLE",
            "sql": """
                SELECT technology_type, COUNT(DISTINCT transition_project_id) as projects, 
                       SUM(installed_capacity_mw) as capacity_mw, 
                       ROUND(SUM(annual_capex_inr_cr), 2) as capex_fy26_cr, 
                       ROUND(MAX(cumulative_capex_inr_cr), 2) as cumulative_capex_cr 
                FROM hrfin_gold.mart_energy_transition 
                WHERE fiscal_year = 'FY26' GROUP BY 1
            """
        },
        "fu1": {
            "text": "What is the annual Scope 1 and Scope 2 avoided emissions (in MTCO2e) achieved from operational renewable projects?",
            "kind": "drill_down",
            "status": "ANSWERABLE",
            "sql": """
                SELECT fiscal_year, ROUND(SUM(generation_gwh), 1) as gen_gwh, 
                       ROUND(SUM(scope1_avoided_emissions_mtco2e), 1) as scope1_avoided, 
                       ROUND(SUM(scope2_avoided_emissions_mtco2e), 1) as scope2_avoided 
                FROM hrfin_gold.mart_energy_transition 
                GROUP BY 1 ORDER BY 1
            """
        },
        "fu2": {
            "text": "Are our renewable projects meeting the Net Zero 2038 interim roadmap milestones?",
            "kind": "what_if_target",
            "status": "ANSWERABLE",
            "sql": """
                SELECT technology_type, net_zero_2038_roadmap_milestone_met, COUNT(*) as milestones_count 
                FROM hrfin_gold.mart_energy_transition 
                WHERE fiscal_year = 'FY26' GROUP BY 1, 2
            """
        }
    }
]

print(f"Loaded {len(QUESTIONS)} questions in build_stress_test_data.py test stub")
