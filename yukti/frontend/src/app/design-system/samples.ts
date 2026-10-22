import { ChartSpec, KpiTile, TableSpec } from '@/contracts/answerContract';

/* ------------------------------------------------------------------ KPI Samples */

export const KPI_SAMPLES: KpiTile[] = [
  {
    label: 'Active Employees',
    value: 23117,
    unit: '',
  },
  {
    label: 'FY26 Revenue',
    value: 132508,
    unit: '₹ Cr',
    delta: '+12.4% vs FY25',
  },
  {
    label: 'Vacancy Rate · ▼1.2 pts vs FY25',
    value: 8.5,
    unit: '%',
    delta: '-1.2 pts vs FY25',
  },
];

/* ------------------------------------------------------------------ Table Sample */

export const TABLE_SAMPLE: TableSpec = {
  columns: ['name', 'grade', 'discipline', 'ongc_tenure_yrs', 'delhi_tenure_yrs', 'retiring_le_3y'],
  rows: [
    { name: 'Rajesh Kumar Sharma', grade: 'E6', discipline: 'Production', ongc_tenure_yrs: 24, delhi_tenure_yrs: 7, retiring_le_3y: false },
    { name: 'Amit Verma', grade: 'E5', discipline: 'Drilling', ongc_tenure_yrs: 18, delhi_tenure_yrs: 5, retiring_le_3y: false },
    { name: 'Sunita Deshmukh', grade: 'E7', discipline: 'Geophysics', ongc_tenure_yrs: 28, delhi_tenure_yrs: 6, retiring_le_3y: true },
    { name: 'Vikramaditya Singh', grade: 'E4', discipline: 'Geology', ongc_tenure_yrs: 12, delhi_tenure_yrs: 5, retiring_le_3y: false },
    { name: 'Priya Natarajan', grade: 'E3', discipline: 'Finance & Accounts', ongc_tenure_yrs: 9, delhi_tenure_yrs: 3, retiring_le_3y: false },
    { name: 'Sanjay Bhattacharya', grade: 'E8', discipline: 'Mechanical', ongc_tenure_yrs: 31, delhi_tenure_yrs: 8, retiring_le_3y: true },
    { name: 'Neha Aggarwal', grade: 'E2', discipline: 'Human Resources', ongc_tenure_yrs: 5, delhi_tenure_yrs: 5, retiring_le_3y: false },
    { name: 'Manpreet Singh Gill', grade: 'E7', discipline: 'Chemistry', ongc_tenure_yrs: 27, delhi_tenure_yrs: 4, retiring_le_3y: false },
  ],
};

/* ------------------------------------------------------------------ Reference Chart 1: Bar */
// Headcount by work centre (8 rows)

export const BAR_SPEC: ChartSpec = {
  kind: 'bar',
  category: 'work_centre',
  value: 'headcount',
  unit: 'Executives',
  data: [
    { work_centre: 'Delhi HQ', headcount: 419 },
    { work_centre: 'Mumbai Offshore', headcount: 1850 },
    { work_centre: 'Ankleshwar', headcount: 1240 },
    { work_centre: 'Mehsana', headcount: 1120 },
    { work_centre: 'Assam Asset', headcount: 980 },
    { work_centre: 'Rajahmundry', headcount: 740 },
    { work_centre: 'Karaikal', headcount: 560 },
    { work_centre: 'Tripura Asset', headcount: 430 },
  ],
};

/* ------------------------------------------------------------------ Reference Chart 2: H-Bar */
// FY26 PBT by field (10 rows, including 2 negative values, unit ₹ Cr)

export const HBAR_SPEC: ChartSpec = {
  kind: 'hbar',
  category: 'field',
  value: 'pbt_cr',
  unit: '₹ Cr',
  data: [
    { field: 'Mumbai High', pbt_cr: 8420 },
    { field: 'Bassein', pbt_cr: 4150 },
    { field: 'Gandhar', pbt_cr: 2890 },
    { field: 'Ravva', pbt_cr: 1640 },
    { field: 'KG-DWN-98/2', pbt_cr: 1210 },
    { field: 'Neelam', pbt_cr: 890 },
    { field: 'Heera', pbt_cr: 540 },
    { field: 'Mehsana Onshore', pbt_cr: 320 },
    { field: 'Cauvery Onshore', pbt_cr: -180 },
    { field: 'Assam Shelf', pbt_cr: -450 },
  ],
};

/* ------------------------------------------------------------------ Reference Chart 3: Donut */
// Executives by grade E1–E9 (from c1_donut_by_grade.json)

export const DONUT_SPEC: ChartSpec = {
  kind: 'donut',
  category: 'grade',
  value: 'count',
  unit: 'Executives',
  data: [
    { grade: 'E1', count: 35 },
    { grade: 'E2', count: 90 },
    { grade: 'E3', count: 87 },
    { grade: 'E4', count: 67 },
    { grade: 'E5', count: 57 },
    { grade: 'E6', count: 35 },
    { grade: 'E7', count: 33 },
    { grade: 'E8', count: 12 },
    { grade: 'E9', count: 3 },
  ],
};

/* ------------------------------------------------------------------ Reference Chart 4: Line */
// Revenue FY17–FY26 (unit ₹ Cr)

export const LINE_SPEC: ChartSpec = {
  kind: 'line',
  category: 'fiscal_year',
  value: 'revenue_cr',
  unit: '₹ Cr',
  data: [
    { fiscal_year: 'FY17', revenue_cr: 77908 },
    { fiscal_year: 'FY18', revenue_cr: 85004 },
    { fiscal_year: 'FY19', revenue_cr: 109655 },
    { fiscal_year: 'FY20', revenue_cr: 96214 },
    { fiscal_year: 'FY21', revenue_cr: 68141 },
    { fiscal_year: 'FY22', revenue_cr: 110345 },
    { fiscal_year: 'FY23', revenue_cr: 155517 },
    { fiscal_year: 'FY24', revenue_cr: 138402 },
    { fiscal_year: 'FY25', revenue_cr: 142100 },
    { fiscal_year: 'FY26', revenue_cr: 148500 },
  ],
};

/* ------------------------------------------------------------------ Reference Chart 5: Histogram */
// Employee age values (≥ 120 raw numbers between 22 and 60)

const RAW_AGES: number[] = [
  22, 23, 23, 24, 24, 25, 25, 25, 26, 26, 27, 27, 27, 28, 28, 28, 29, 29, 29, 30,
  30, 30, 31, 31, 31, 32, 32, 32, 33, 33, 33, 34, 34, 34, 34, 35, 35, 35, 35, 36,
  36, 36, 36, 37, 37, 37, 37, 38, 38, 38, 38, 39, 39, 39, 39, 40, 40, 40, 40, 41,
  41, 41, 41, 42, 42, 42, 42, 43, 43, 43, 44, 44, 44, 45, 45, 45, 45, 46, 46, 46,
  47, 47, 47, 48, 48, 48, 49, 49, 49, 50, 50, 50, 50, 51, 51, 51, 52, 52, 52, 53,
  53, 53, 54, 54, 54, 55, 55, 55, 56, 56, 56, 57, 57, 57, 58, 58, 58, 59, 59, 60,
  60, 24, 28, 32, 35, 38, 42, 45, 48, 52, 55, 58,
];

export const HISTOGRAM_SPEC: ChartSpec = {
  kind: 'histogram',
  value: 'age',
  unit: 'Years',
  data: RAW_AGES.map((age) => ({ age })),
};

/* ------------------------------------------------------------------ Reference Chart 6: Treemap */
// Capex by asset (8 rows)

export const TREEMAP_SPEC: ChartSpec = {
  kind: 'treemap',
  category: 'asset',
  value: 'capex_cr',
  unit: '₹ Cr',
  data: [
    { asset: 'Mumbai High', capex_cr: 14200 },
    { asset: 'Bassein & Satellite', capex_cr: 8650 },
    { asset: 'KG-DWN-98/2', capex_cr: 9800 },
    { asset: 'Neelam & Heera', capex_cr: 5120 },
    { asset: 'Assam Asset', capex_cr: 4200 },
    { asset: 'Cambay Basin', capex_cr: 3450 },
    { asset: 'Cauvery Asset', capex_cr: 2750 },
    { asset: 'Tripura Asset', capex_cr: 1850 },
  ],
};

/* ------------------------------------------------------------------ Reference Chart 7: Ranked H-Bar */
// Non-diverging ranked hbar: Headcount by discipline (9 positive rows, with "Others (6)" as largest value)

export const RANKED_SPEC: ChartSpec = {
  kind: 'hbar',
  category: 'discipline',
  value: 'headcount',
  unit: 'Executives',
  sort: 'desc',
  data: [
    { discipline: 'Production', headcount: 1850 },
    { discipline: 'Drilling', headcount: 1620 },
    { discipline: 'Mechanical', headcount: 1410 },
    { discipline: 'Geology', headcount: 1180 },
    { discipline: 'Geophysics', headcount: 950 },
    { discipline: 'Finance & Accounts', headcount: 820 },
    { discipline: 'Human Resources', headcount: 690 },
    { discipline: 'Chemistry', headcount: 530 },
    { discipline: 'Others (6)', headcount: 2400 },
  ],
};
