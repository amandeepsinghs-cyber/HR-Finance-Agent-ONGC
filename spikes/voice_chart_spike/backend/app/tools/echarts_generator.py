"""Declarative ECharts option JSON generator for ONGC HR & Finance Spike.
Generates interactive donut chart by grade and stacked bar chart by discipline.
"""

from typing import Any, Dict, List


def generate_headcount_echarts(
    rows: List[Dict[str, Any]],
    location: str = "Delhi",
    min_years: int = 5,
    title_override: str | None = None
) -> Dict[str, Any]:
    """Generates an ECharts option dict containing donut chart by grade

    and stacked bar chart by discipline.
    """
    # 1. Aggregate headcount by grade
    grade_totals: Dict[str, int] = {}
    grade_exempt: Dict[str, int] = {}
    grade_non_exempt: Dict[str, int] = {}

    # 2. Aggregate headcount by discipline
    discipline_totals: Dict[str, int] = {}
    # grade x discipline breakdown
    matrix: Dict[str, Dict[str, int]] = {}

    all_grades = ["E1", "E2", "E3", "E4", "E5", "E6", "E7", "E8", "E9"]
    all_disciplines = [
        "DISC-DRL", "DISC-FIN", "DISC-HR", "DISC-HSE", "DISC-IT",
        "DISC-LEG", "DISC-MED", "DISC-MM", "DISC-PRD"
    ]

    for g in all_grades:
        grade_totals[g] = 0
        grade_exempt[g] = 0
        grade_non_exempt[g] = 0
        matrix[g] = {d: 0 for d in all_disciplines}

    for d in all_disciplines:
        discipline_totals[d] = 0

    for r in rows:
        g = r.get("grade_id")
        d = r.get("discipline_id")
        count = int(r.get("delhi_executives_ge_5yr", 0))
        exempt = int(r.get("exempt_retiring_3yr", 0))
        non_exempt = int(r.get("non_exempt_due_transfer", 0))

        if g in grade_totals:
            grade_totals[g] += count
            grade_exempt[g] += exempt
            grade_non_exempt[g] += non_exempt
        if d in discipline_totals:
            discipline_totals[d] += count
        if g in matrix and d in matrix[g]:
            matrix[g][d] += count

    total_executives = sum(grade_totals.values())
    title_text = title_override or f"{location}: Executives with ≥{min_years} Years Tenure (Total: {total_executives})"

    donut_data = [
        {"name": g, "value": grade_totals[g]}
        for g in all_grades if grade_totals[g] > 0
    ]

    # Friendly discipline labels
    disc_labels = {
        "DISC-DRL": "Drilling",
        "DISC-FIN": "Finance",
        "DISC-HR": "HR",
        "DISC-HSE": "HSE",
        "DISC-IT": "IT / Info",
        "DISC-LEG": "Legal",
        "DISC-MED": "Medical",
        "DISC-MM": "Materials",
        "DISC-PRD": "Production",
    }
    short_disc_names = [disc_labels.get(d, d) for d in all_disciplines]

    series_stacked = []
    grade_palette = [
        "#1E3A8A", "#2563EB", "#3B82F6", "#0D9488", "#10B981",
        "#F59E0B", "#EA580C", "#DC2626", "#8B5CF6"
    ]

    for idx, g in enumerate(all_grades):
        series_stacked.append({
            "name": g,
            "type": "bar",
            "stack": "total",
            "emphasis": {"focus": "series"},
            "itemStyle": {"color": grade_palette[idx % len(grade_palette)]},
            "data": [matrix[g][d] for d in all_disciplines]
        })

    echarts_spec = {
        "title": {
            "text": title_text,
            "subtext": "ONGC HR Continuous Stay Analysis (hrfin_gold.v_continuous_stay)",
            "left": "center",
            "textStyle": {"fontSize": 16, "fontWeight": "bold", "color": "#111827"},
            "subtextStyle": {"fontSize": 12, "color": "#6B7280"}
        },
        "tooltip": {
            "trigger": "item",
            "formatter": "{a} <br/>{b}: <b>{c}</b> ({d}%)"
        },
        "legend": {
            "orient": "horizontal",
            "bottom": "0%",
            "left": "center",
            "itemGap": 12,
            "textStyle": {"fontSize": 11}
        },
        "color": grade_palette,
        "grid": {
            "top": "18%",
            "left": "10%",
            "right": "10%",
            "bottom": "25%",
            "containLabel": True
        },
        "views": {
            "donut": {
                "title": f"Grade Distribution (Total: {total_executives})",
                "series": [
                    {
                        "name": "Executives by Grade",
                        "type": "pie",
                        "radius": ["42%", "70%"],
                        "center": ["50%", "52%"],
                        "avoidLabelOverlap": True,
                        "itemStyle": {
                            "borderRadius": 6,
                            "borderColor": "#ffffff",
                            "borderWidth": 2
                        },
                        "label": {
                            "show": True,
                            "formatter": "{b}: {c} ({d}%)"
                        },
                        "emphasis": {
                            "label": {"show": True, "fontSize": 14, "fontWeight": "bold"}
                        },
                        "data": donut_data
                    }
                ]
            },
            "stacked_bar": {
                "title": "Discipline Breakdown by Grade",
                "xAxis": {
                    "type": "category",
                    "data": short_disc_names,
                    "axisLabel": {"interval": 0, "rotate": 25, "fontSize": 11}
                },
                "yAxis": {
                    "type": "value",
                    "name": "Headcount"
                },
                "series": series_stacked
            }
        },
        # Default active series is the donut view
        "series": [
            {
                "name": "Executives by Grade",
                "type": "pie",
                "radius": ["42%", "70%"],
                "center": ["50%", "52%"],
                "avoidLabelOverlap": True,
                "itemStyle": {
                    "borderRadius": 6,
                    "borderColor": "#ffffff",
                    "borderWidth": 2
                },
                "label": {
                    "show": True,
                    "formatter": "{b}: {c} ({d}%)"
                },
                "emphasis": {
                    "label": {"show": True, "fontSize": 14, "fontWeight": "bold"}
                },
                "data": donut_data
            }
        ],
        "animation": True,
        "animationDuration": 1000,
        "animationEasing": "cubicOut"
    }

    return echarts_spec
