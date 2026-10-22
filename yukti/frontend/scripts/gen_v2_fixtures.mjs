/**
 * Generator script for Yukti contract-v2 deterministic test fixtures.
 * Seeded PRNG ensures byte-identical output across runs.
 */

import { fileURLToPath } from 'url';
import { dirname, resolve, join } from 'path';
import fs from 'fs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const V2_FIXTURES_DIR = resolve(__dirname, '../src/fixtures/v2');

// Seeded PRNG: Mulberry32
function mulberry32(seed) {
  let s = seed >>> 0;
  return function() {
    s = (s + 0x6D2B79F5) >>> 0;
    let t = Math.imul(s ^ (s >>> 15), 1 | s);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const rng = mulberry32(20261022);

const FIRST_NAMES = [
  'Rajesh', 'Sunita', 'Amit', 'Priya', 'Suresh', 'Anita', 'Vikram', 'Pooja', 'Sanjay', 'Neha',
  'Manoj', 'Anjali', 'Ramesh', 'Kavita', 'Deepak', 'Swati', 'Alok', 'Divya', 'Rahul', 'Meera',
  'Arun', 'Preeti', 'Ajay', 'Ritu', 'Sandeep', 'Rekha', 'Pradeep', 'Shweta', 'Ashok', 'Rashmi',
  'Dinesh', 'Vandana', 'Vivek', 'Sneha', 'Harish', 'Shilpa', 'Gaurav', 'Archana', 'Manish', 'Seema',
  'Anil', 'Sangeeta', 'Vijay', 'Jyoti', 'Sanjeev', 'Geeta', 'Rajiv', 'Pratibha', 'Pankaj', 'Kishore',
  'Deepa', 'Mukesh', 'Usha', 'Rakesh', 'Aarti', 'Bhupendra', 'Poonam', 'Hemant', 'Shashi', 'Naveen',
  'Asha', 'Jitendra', 'Sarita', 'Arvind', 'Madhu', 'Rohit', 'Pallavi', 'Nitin', 'Anupama', 'Satish',
  'Smita', 'Tarun', 'Radhika', 'Mahesh', 'Kalpana', 'Girish', 'Sushma', 'Vinod', 'Aparna', 'Kamal',
  'Kiran', 'Vinay', 'Manju', 'Brijesh', 'Renu', 'Dharmendra', 'Suman', 'Pramod', 'Indu', 'Subhash',
  'Shobha', 'Naresh', 'Ranjana', 'Sunil', 'Maya', 'Abhay', 'Nalini', 'Akhilesh', 'Mamta', 'Devendra'
];

const LAST_NAMES = [
  'Sharma', 'Verma', 'Singh', 'Patel', 'Gupta', 'Kumar', 'Mishra', 'Joshi', 'Nair', 'Rao',
  'Reddy', 'Chatterjee', 'Banerjee', 'Mukherjee', 'Sen', 'Ghosh', 'Das', 'Roy', 'Bose', 'Dutta',
  'Desai', 'Mehta', 'Shah', 'Bhatt', 'Trivedi', 'Pandya', 'Dave', 'Shukla', 'Tiwari', 'Tripathi',
  'Pandey', 'Dubey', 'Chaubey', 'Jha', 'Thakur', 'Chauhan', 'Rathore', 'Yadav', 'Prasad', 'Srivastava',
  'Saxena', 'Mathur', 'Bhatnagar', 'Agarwal', 'Goel', 'Bansal', 'Mittal', 'Singhal', 'Garg', 'Jindal',
  'Jain', 'Sethi', 'Kapoor', 'Malhotra', 'Khanna', 'Chopra', 'Arora', 'Bhatia', 'Grover', 'Anand',
  'Chawla', 'Ahuja', 'Gill', 'Dhillon', 'Sandhu', 'Grewal', 'Sidhu', 'Mann', 'Brar', 'Pillai',
  'Menon', 'Nambiar', 'Kurup', 'Varma', 'Iyer', 'Iyengar', 'Balakrishnan', 'Raman', 'Natarajan',
  'Swaminathan', 'Krishnan', 'Venkat', 'Murthy', 'Naidu', 'Choudhury', 'Borah', 'Saikia', 'Gogoi', 'Hazarika',
  'Barua', 'Sarma', 'Phukan', 'Kakati', 'Mahanta', 'Goswami', 'Bezbaruah', 'Medhi', 'Dasgupta', 'Deka'
];

function generateUniqueNames(count) {
  const names = [];
  const used = new Set();
  
  for (let l = 0; l < LAST_NAMES.length && names.length < count; l++) {
    for (let f = 0; f < FIRST_NAMES.length && names.length < count; f++) {
      const name = `${FIRST_NAMES[f]} ${LAST_NAMES[l]}`;
      if (!used.has(name)) {
        used.add(name);
        names.push(name);
      }
    }
  }

  // Middle initials if more are needed
  const initials = ['K.', 'R.', 'S.', 'M.', 'A.', 'P.', 'V.', 'N.', 'B.', 'D.'];
  for (let i = 0; i < initials.length && names.length < count; i++) {
    for (let l = 0; l < LAST_NAMES.length && names.length < count; l++) {
      for (let f = 0; f < FIRST_NAMES.length && names.length < count; f++) {
        const name = `${FIRST_NAMES[f]} ${initials[i]} ${LAST_NAMES[l]}`;
        if (!used.has(name)) {
          used.add(name);
          names.push(name);
        }
      }
    }
  }

  // Deterministic shuffle
  for (let i = names.length - 1; i > 0; i--) {
    const j = Math.floor(rng() * (i + 1));
    [names[i], names[j]] = [names[j], names[i]];
  }

  return names.slice(0, count);
}

function shuffleArray(arr) {
  for (let i = arr.length - 1; i > 0; i--) {
    const j = Math.floor(rng() * (i + 1));
    [arr[i], arr[j]] = [arr[j], arr[i]];
  }
  return arr;
}

function stayToDate(years, refDateStr = '2026-10-22') {
  const ref = new Date(refDateStr + 'T00:00:00Z');
  const days = Math.round(years * 365.25);
  const posted = new Date(ref.getTime() - days * 24 * 3600 * 1000);
  return posted.toISOString().split('T')[0];
}

// -----------------------------------------------------------------------------
// 1. Fixture 1: v2_roster_419.json
// -----------------------------------------------------------------------------
function buildRoster419() {
  const total = 419;
  const names = generateUniqueNames(total);

  // Exact grade distribution summing to 419:
  // E1: 35, E2: 90, E3: 87, E4: 67, E5: 57, E6: 35, E7: 33, E8: 12, E9: 3
  const gradeDistribution = [
    { grade: 'E1', count: 35, minStay: 5.0, maxStay: 7.6 },
    { grade: 'E2', count: 90, minStay: 5.0, maxStay: 9.0 },
    { grade: 'E3', count: 87, minStay: 5.5, maxStay: 10.5 },
    { grade: 'E4', count: 67, minStay: 6.2, maxStay: 12.5 },
    { grade: 'E5', count: 57, minStay: 7.5, maxStay: 14.5 },
    { grade: 'E6', count: 35, minStay: 9.5, maxStay: 16.5 },
    { grade: 'E7', count: 33, minStay: 12.0, maxStay: 19.0 },
    { grade: 'E8', count: 12, minStay: 15.0, maxStay: 20.8 },
    { grade: 'E9', count: 3,  minStay: 18.5, maxStay: 22.0 }
  ];

  // Realistic discipline distribution for Corporate HQ (Finance, HR, MM, IT, Engineering)
  const disciplinesDelhi = [
    'Finance & Accounts', 'HR', 'Materials Management', 'IT', 'Civil',
    'Electrical', 'Mechanical', 'Production', 'Drilling', 'Geology',
    'Geophysics', 'Reservoir', 'Chemistry'
  ];

  const rawRows = [];
  let nameIndex = 0;

  for (const g of gradeDistribution) {
    for (let c = 0; c < g.count; c++) {
      // Stay correlated with seniority
      const stayVal = g.minStay + rng() * (g.maxStay - g.minStay);
      const stay = Math.max(5.0, Math.min(22.0, Math.round(stayVal * 10) / 10));
      const disc = disciplinesDelhi[(nameIndex * 3 + c) % disciplinesDelhi.length];

      rawRows.push({
        emp_name: names[nameIndex],
        grade: g.grade,
        discipline: disc,
        work_centre: 'Delhi (Corporate HQ)',
        continuous_stay_years: stay
      });
      nameIndex++;
    }
  }

  // Sort rows by continuous_stay_years DESCENDING
  rawRows.sort((a, b) => b.continuous_stay_years - a.continuous_stay_years);

  // Assign emp_id and posted_since after sorting
  const rows = rawRows.map((r, idx) => ({
    emp_name: r.emp_name,
    emp_id: String(104001 + idx),
    grade: r.grade,
    discipline: r.discipline,
    work_centre: r.work_centre,
    continuous_stay_years: r.continuous_stay_years,
    posted_since: stayToDate(r.continuous_stay_years)
  }));

  // Dynamically compute all KPIs and insights
  const stays = rows.map(r => r.continuous_stay_years);
  const medianStay = stays[Math.floor(total / 2)];
  const e7PlusRows = rows.filter(r => ['E7', 'E8', 'E9'].includes(r.grade));
  const e7PlusCount = e7PlusRows.length;
  const maxStay = rows[0].continuous_stay_years;
  const maxStayDiscipline = rows[0].discipline;
  const maxStayGrade = rows[0].grade;

  const data = {
    turn_id: 'turn_v2_roster_419',
    language: 'en',
    persona: 'CMD',
    spoken_summary: `Across Delhi Corporate HQ, 419 executives have completed five or more continuous years of posting. Senior executives in grades E7 to E9 account for ${e7PlusCount} officers, with the longest tenure reaching ${maxStay} years in ${maxStayDiscipline}. A draft rotational transfer note can be initiated directly for eligible officers.`,
    display_text: `Analysis of hrfin_gold.ssot_workforce_employee identifies 419 active executives with >= 5.0 years continuous stay at Delhi HQ (WC-DEL) [1]. ${e7PlusCount} officers are at E7+ grade level. Actionable transfer workflows are available for eligible candidates under rotational transfer norms.`,
    contract_version: 2,
    visual: {
      type: 'table',
      mode: 'replace',
      title: 'Delhi HQ: executives with 5+ years continuous stay',
      table: {
        columns: [
          'emp_name',
          'emp_id',
          'grade',
          'discipline',
          'work_centre',
          'continuous_stay_years',
          'posted_since'
        ],
        rows: rows,
        total_rows: 419,
        masking: {
          level: 'none'
        },
        row_actions: [
          {
            id: 'transfer',
            label: 'Draft transfer note',
            action: 'draft_transfer_note',
            question_template: 'Draft a transfer note for {emp_name} ({emp_id})',
            min_role: 'DIR_HR'
          }
        ]
      },
      kpis: [
        {
          label: 'Total Delhi 5+ Yr',
          value: 419,
          unit: 'Executives'
        },
        {
          label: 'Median Stay',
          value: medianStay,
          unit: 'Years'
        },
        {
          label: 'E7+ Senior Count',
          value: e7PlusCount,
          unit: 'Executives'
        }
      ]
    },
    insights_v2: [
      {
        text: '419 executives at Delhi Corporate HQ have completed five or more continuous years of posting.',
        kind: 'headline',
        value: 419,
        unit: 'Executives'
      },
      {
        text: `Longest continuous stay reaches ${maxStay} years in the ${maxStayDiscipline} discipline (${maxStayGrade}).`,
        kind: 'outlier',
        value: maxStay,
        unit: 'Years',
        ref: maxStayDiscipline
      },
      {
        text: `${e7PlusCount} senior executives (grades E7–E9) exceed the 5-year stay norm at Delhi HQ.`,
        kind: 'risk',
        value: e7PlusCount,
        unit: 'Executives',
        ref: 'E7+'
      }
    ],
    drilldowns: [
      {
        label: 'Only E7 and above',
        question: 'Show executives in grade E7 and above with 5+ years stay in Delhi',
        spec_patch: {
          add_filters: [
            { field: 'grade', op: 'in', value: ['E7', 'E8', 'E9'] }
          ]
        }
      },
      {
        label: 'By discipline',
        question: 'Break down Delhi 5+ year executives by discipline',
        spec_patch: {
          dimensions: ['discipline'],
          chart_kind: 'hbar'
        }
      },
      {
        label: 'Over 10 years',
        question: 'Show executives with over 10 years continuous stay in Delhi',
        spec_patch: {
          add_filters: [
            { field: 'continuous_stay_years', op: '>=', value: 10 }
          ]
        }
      }
    ],
    context_chips: [
      { label: 'CMD', kind: 'role' },
      { label: 'Delhi HQ', kind: 'subject' },
      { label: 'Executives', kind: 'population' },
      { label: '5+ years', kind: 'filter' }
    ],
    query_spec: {
      version: 1,
      domain: 'hr',
      metric: 'headcount',
      aggregation: 'count',
      grain: 'row',
      filters: [
        { field: 'wc_id', op: '=', value: 'DEL' },
        { field: 'continuous_stay_years', op: '>=', value: 5 },
        { field: 'employment_status', op: '=', value: 'Active' }
      ],
      sort: {
        by: 'continuous_stay_years',
        dir: 'desc'
      }
    },
    sources: [
      {
        kind: 'data',
        object: 'hrfin_gold.ssot_workforce_employee'
      }
    ],
    access: {
      status: 'allowed'
    },
    export_options: ['sheets', 'docs', 'word', 'pdf']
  };

  return { data, rows, gradeDistribution };
}

// -----------------------------------------------------------------------------
// 2. Fixture 2: v2_roster_2000.json
// -----------------------------------------------------------------------------
function buildRoster2000() {
  const total = 2000;
  const names = generateUniqueNames(total);

  // Weighted Work Centres:
  // Mumbai 22%, Delhi 14%, Vadodara 10%, Ahmedabad 9%, Dehradun 8%,
  // Mehsana 7%, Ankleshwar 6%, Jorhat 5%, Sivasagar 5%, Rajahmundry 4%,
  // Chennai 3%, Kolkata 3%, Karaikal 2%, Agartala 1%, Cambay 1%
  const workCentreWeights = [
    { name: 'Mumbai (Western Offshore)', count: 440 }, // 22%
    { name: 'Delhi (Corporate HQ)', count: 280 },       // 14%
    { name: 'Vadodara', count: 200 },                  // 10%
    { name: 'Ahmedabad', count: 180 },                 // 9%
    { name: 'Dehradun', count: 160 },                  // 8%
    { name: 'Mehsana', count: 140 },                   // 7%
    { name: 'Ankleshwar', count: 120 },                // 6%
    { name: 'Jorhat', count: 100 },                    // 5%
    { name: 'Sivasagar', count: 100 },                 // 5%
    { name: 'Rajahmundry', count: 80 },                // 4%
    { name: 'Chennai', count: 60 },                    // 3%
    { name: 'Kolkata', count: 60 },                    // 3%
    { name: 'Karaikal', count: 40 },                   // 2%
    { name: 'Agartala', count: 20 },                   // 1%
    { name: 'Cambay', count: 20 }                      // 1%
  ];

  // Weighted Disciplines: Production 24% + Drilling 18% = 42% (> 40%)
  const disciplineWeights = [
    { name: 'Production', count: 480 },          // 24%
    { name: 'Drilling', count: 360 },            // 18%
    { name: 'Reservoir', count: 160 },           // 8%
    { name: 'Geology', count: 160 },             // 8%
    { name: 'Geophysics', count: 140 },          // 7%
    { name: 'Mechanical', count: 140 },          // 7%
    { name: 'Electrical', count: 120 },          // 6%
    { name: 'Finance & Accounts', count: 120 },  // 6%
    { name: 'HR', count: 100 },                  // 5%
    { name: 'Chemistry', count: 80 },            // 4%
    { name: 'Materials Management', count: 80 }, // 4%
    { name: 'Civil', count: 80 },                // 4%
    { name: 'IT', count: 60 }                    // 3%
  ];

  // Grade weights with seniority-correlated stay ranges:
  const gradeWeights = [
    { grade: 'E0', count: 60,  minStay: 8.0,  maxStay: 10.5 },
    { grade: 'E1', count: 200, minStay: 8.0,  maxStay: 11.5 },
    { grade: 'E2', count: 440, minStay: 8.5,  maxStay: 13.0 },
    { grade: 'E3', count: 460, minStay: 9.5,  maxStay: 14.5 },
    { grade: 'E4', count: 340, minStay: 11.0, maxStay: 16.5 },
    { grade: 'E5', count: 240, minStay: 12.5, maxStay: 18.5 },
    { grade: 'E6', count: 140, minStay: 14.5, maxStay: 20.5 },
    { grade: 'E7', count: 80,  minStay: 16.5, maxStay: 22.0 },
    { grade: 'E8', count: 30,  minStay: 18.5, maxStay: 23.5 },
    { grade: 'E9', count: 10,  minStay: 20.5, maxStay: 24.0 }
  ];

  const workCentresPool = [];
  for (const w of workCentreWeights) {
    for (let i = 0; i < w.count; i++) workCentresPool.push(w.name);
  }
  shuffleArray(workCentresPool);

  const disciplinesPool = [];
  for (const d of disciplineWeights) {
    for (let i = 0; i < d.count; i++) disciplinesPool.push(d.name);
  }
  shuffleArray(disciplinesPool);

  const rawRows = [];
  let nameIndex = 0;

  for (const g of gradeWeights) {
    for (let c = 0; c < g.count; c++) {
      const stayVal = g.minStay + rng() * (g.maxStay - g.minStay);
      const stay = Math.max(8.0, Math.min(24.0, Math.round(stayVal * 10) / 10));

      rawRows.push({
        emp_name: names[nameIndex],
        grade: g.grade,
        discipline: disciplinesPool[nameIndex],
        work_centre: workCentresPool[nameIndex],
        continuous_stay_years: stay
      });
      nameIndex++;
    }
  }

  // Sort rows by continuous_stay_years DESCENDING
  rawRows.sort((a, b) => b.continuous_stay_years - a.continuous_stay_years);

  // Assign emp_id and posted_since
  const rows = rawRows.map((r, idx) => ({
    emp_name: r.emp_name,
    emp_id: String(200001 + idx),
    grade: r.grade,
    discipline: r.discipline,
    work_centre: r.work_centre,
    continuous_stay_years: r.continuous_stay_years,
    posted_since: stayToDate(r.continuous_stay_years)
  }));

  // Dynamically compute KPIs and insight numbers
  const stays = rows.map(r => r.continuous_stay_years);
  const medianStay = stays[Math.floor(total / 2)];

  // Dynamic counts per work centre
  const wcCounts = {};
  for (const r of rows) {
    wcCounts[r.work_centre] = (wcCounts[r.work_centre] || 0) + 1;
  }
  const mumbaiCount = wcCounts['Mumbai (Western Offshore)'];
  const delhiCount = wcCounts['Delhi (Corporate HQ)'];
  const uniqueCentresCount = Object.keys(wcCounts).length;

  // Dynamic discipline shares
  const prodDrillCount = rows.filter(r => ['Production', 'Drilling'].includes(r.discipline)).length;
  const prodDrillPct = Math.round((prodDrillCount / total) * 1000) / 10; // e.g. 42.0

  const data = {
    turn_id: 'turn_v2_roster_2000',
    language: 'en',
    persona: 'CMD',
    spoken_summary: `Across all ONGC work centres, 2,000 executives have completed eight or more continuous years at their current station. Mumbai Western Offshore (${mumbaiCount} officers) and Delhi HQ (${delhiCount} officers) account for the largest clusters of long-stay personnel. Production and Drilling disciplines comprise ${prodDrillPct}% of the population.`,
    display_text: `Pan-India query across hrfin_gold.ssot_workforce_employee identifies 2,000 active executives with >= 8.0 years continuous stay across ${uniqueCentresCount} work centres [1]. Mumbai (${mumbaiCount}) and Delhi (${delhiCount}) form the largest concentrations; technical disciplines account for ${prodDrillPct}%.`,
    contract_version: 2,
    visual: {
      type: 'table',
      mode: 'replace',
      title: 'All-India: executives with 8+ years continuous stay',
      table: {
        columns: [
          'emp_name',
          'emp_id',
          'grade',
          'discipline',
          'work_centre',
          'continuous_stay_years',
          'posted_since'
        ],
        rows: rows,
        total_rows: 2000,
        masking: {
          level: 'none'
        },
        row_actions: [
          {
            id: 'transfer',
            label: 'Draft transfer note',
            action: 'draft_transfer_note',
            question_template: 'Draft a transfer note for {emp_name} ({emp_id})',
            min_role: 'DIR_HR'
          }
        ]
      },
      kpis: [
        {
          label: 'Long-Stay Executives',
          value: 2000,
          unit: 'Officers'
        },
        {
          label: 'Median Stay',
          value: medianStay,
          unit: 'Years'
        },
        {
          label: 'Work Centres',
          value: uniqueCentresCount,
          unit: 'Locations'
        },
        {
          label: 'Prod & Drilling Share',
          value: prodDrillPct,
          unit: '%'
        }
      ]
    },
    insights_v2: [
      {
        text: '2,000 executives across all ONGC assets have completed 8 or more years at their current posting.',
        kind: 'headline',
        value: 2000,
        unit: 'Executives'
      },
      {
        text: `Western Offshore (Mumbai, ${mumbaiCount} executives) and Corporate HQ (Delhi, ${delhiCount} executives) represent the largest clusters of overstay.`,
        kind: 'trend',
        value: mumbaiCount,
        unit: 'Officers',
        ref: 'Mumbai (Western Offshore)'
      },
      {
        text: `Production and Drilling disciplines represent ${prodDrillPct}% (${prodDrillCount} officers) of the long-stay population, exceeding the 40% operational threshold.`,
        kind: 'risk',
        value: prodDrillPct,
        unit: '%',
        ref: 'Production'
      }
    ],
    drilldowns: [
      {
        label: 'By work centre',
        question: 'Break down all-India long stay executives by work centre',
        spec_patch: {
          dimensions: ['work_centre'],
          chart_kind: 'hbar'
        }
      },
      {
        label: 'Over 12 years',
        question: 'Show executives with 12 or more years continuous stay',
        spec_patch: {
          add_filters: [
            { field: 'continuous_stay_years', op: '>=', value: 12 }
          ]
        }
      }
    ],
    context_chips: [
      { label: 'CMD', kind: 'role' },
      { label: 'All-India', kind: 'subject' },
      { label: 'Executives', kind: 'population' },
      { label: '8+ years', kind: 'filter' }
    ],
    query_spec: {
      version: 1,
      domain: 'hr',
      metric: 'headcount',
      aggregation: 'count',
      grain: 'row',
      filters: [
        { field: 'continuous_stay_years', op: '>=', value: 8 },
        { field: 'employment_status', op: '=', value: 'Active' }
      ],
      sort: {
        by: 'continuous_stay_years',
        dir: 'desc'
      }
    },
    sources: [
      {
        kind: 'data',
        object: 'hrfin_gold.ssot_workforce_employee'
      }
    ],
    access: {
      status: 'allowed'
    },
    export_options: ['sheets', 'docs', 'word', 'pdf']
  };

  return data;
}

// -----------------------------------------------------------------------------
// 3. Fixture 3: v2_roster_partial_dirfin.json
// -----------------------------------------------------------------------------
function buildRosterPartialDirFin(delhiRows) {
  // First 60 rows from Delhi roster, masked columns: emp_id, posted_since, continuous_stay_years
  const partialRows = delhiRows.slice(0, 60).map(row => ({
    ...row,
    emp_id: '••••',
    posted_since: '••••',
    continuous_stay_years: '••••'
  }));

  const data = {
    turn_id: 'turn_v2_roster_partial_dirfin',
    language: 'en',
    persona: 'DIR_FIN',
    spoken_summary: 'Displaying the Delhi HQ executive roster for Finance review with employee identifiers and exact station tenures masked under data governance rule RBAC-HR-02. The first sixty records of the four hundred nineteen eligible executives are shown. Grade, discipline, and station location remain fully visible for financial planning.',
    display_text: 'Delhi HQ executive roster (5+ years continuous stay) under DIR_FIN persona [1]. In compliance with RBAC-HR-02, personal identifiers (emp_id, posted_since) and exact tenure years are masked. Showing first 60 of 419 matching records.',
    contract_version: 2,
    visual: {
      type: 'table',
      mode: 'replace',
      title: 'Delhi HQ: executives with 5+ years stay (Finance View)',
      table: {
        columns: [
          'emp_name',
          'emp_id',
          'grade',
          'discipline',
          'work_centre',
          'continuous_stay_years',
          'posted_since'
        ],
        rows: partialRows,
        total_rows: 419,
        masking: {
          level: 'partial',
          masked_columns: ['emp_id', 'posted_since', 'continuous_stay_years'],
          reason: 'Personal identifiers and exact tenures are limited to HR and the CMD.',
          rule_ref: 'RBAC-HR-02'
        }
      },
      kpis: [
        {
          label: 'Total Delhi 5+ Yr',
          value: 419,
          unit: 'Officers'
        },
        {
          label: 'Sample Displayed',
          value: 60,
          unit: 'Rows'
        }
      ]
    },
    insights_v2: [
      {
        text: 'Employee identifiers and exact tenure years are redacted under RBAC-HR-02 for non-HR leadership roles.',
        kind: 'note'
      }
    ],
    context_chips: [
      { label: 'DIR_FIN', kind: 'role' },
      { label: 'Delhi HQ', kind: 'subject' },
      { label: 'Partial Access', kind: 'filter' }
    ],
    query_spec: {
      version: 1,
      domain: 'hr',
      metric: 'headcount',
      aggregation: 'count',
      grain: 'row',
      filters: [
        { field: 'wc_id', op: '=', value: 'DEL' },
        { field: 'continuous_stay_years', op: '>=', value: 5 },
        { field: 'employment_status', op: '=', value: 'Active' }
      ],
      sort: {
        by: 'continuous_stay_years',
        dir: 'desc'
      },
      limit: 60
    },
    sources: [
      {
        kind: 'data',
        object: 'hrfin_gold.ssot_workforce_employee'
      }
    ],
    access: {
      status: 'partial',
      reason: 'Personal identifiers and exact tenures are limited to HR and the CMD.',
      rule_ref: 'RBAC-HR-02'
    },
    export_options: ['sheets', 'docs', 'word', 'pdf']
  };

  return data;
}

// -----------------------------------------------------------------------------
// 4. Fixture 4: v2_roster_aggregate_e2.json
// -----------------------------------------------------------------------------
function buildRosterAggregateE2(gradeDistribution) {
  const aggregateRows = gradeDistribution.map(item => ({
    grade: item.grade,
    executives: item.count
  }));

  const totalExecs = aggregateRows.reduce((sum, r) => sum + r.executives, 0);

  const data = {
    turn_id: 'turn_v2_roster_aggregate_e2',
    language: 'en',
    persona: 'E2_HR',
    spoken_summary: 'Aggregated Delhi HQ executive counts by grade for officers with five or more years of continuous stay. In accordance with rule RBAC-HR-01, individual roster rows are restricted and summary totals are presented. Across all grades, four hundred nineteen executives meet the criteria.',
    display_text: 'Aggregated grade breakdown for 419 Delhi HQ executives with 5+ years continuous stay [1]. Individual personnel records are restricted under RBAC-HR-01; aggregate grade counts displayed.',
    contract_version: 2,
    visual: {
      type: 'table',
      mode: 'replace',
      title: 'Delhi HQ: 5+ years stay by grade (Aggregate Summary)',
      table: {
        columns: ['grade', 'executives'],
        rows: aggregateRows,
        total_rows: aggregateRows.length,
        masking: {
          level: 'aggregate',
          reason: 'Individual records are not available at your level; showing totals only.',
          rule_ref: 'RBAC-HR-01'
        }
      },
      kpis: [
        {
          label: 'Total Executives',
          value: totalExecs,
          unit: 'Officers'
        }
      ]
    },
    insights_v2: [
      {
        text: 'Total 419 executives aggregated across grades E1 through E9.',
        kind: 'headline',
        value: totalExecs,
        unit: 'Executives'
      }
    ],
    context_chips: [
      { label: 'E2_HR', kind: 'role' },
      { label: 'Delhi HQ', kind: 'subject' },
      { label: 'Aggregate Only', kind: 'filter' }
    ],
    query_spec: {
      version: 1,
      domain: 'hr',
      metric: 'headcount',
      aggregation: 'count',
      grain: 'aggregate',
      dimensions: ['grade'],
      filters: [
        { field: 'wc_id', op: '=', value: 'DEL' },
        { field: 'continuous_stay_years', op: '>=', value: 5 },
        { field: 'employment_status', op: '=', value: 'Active' }
      ]
    },
    sources: [
      {
        kind: 'data',
        object: 'hrfin_gold.ssot_workforce_employee'
      }
    ],
    access: {
      status: 'partial',
      reason: 'Individual records are not available at your level; showing totals only.',
      rule_ref: 'RBAC-HR-01'
    },
    export_options: ['sheets', 'docs', 'word', 'pdf']
  };

  return data;
}

// -----------------------------------------------------------------------------
// 5. Fixture 5: v2_compare_delhi_mumbai.json
// -----------------------------------------------------------------------------
function buildCompareDelhiMumbai() {
  const comparisonData = [
    { grade: 'E0', Delhi: 45, Mumbai: 120 },
    { grade: 'E1', Delhi: 180, Mumbai: 620 },
    { grade: 'E2', Delhi: 390, Mumbai: 1340 },
    { grade: 'E3', Delhi: 460, Mumbai: 1480 },
    { grade: 'E4', Delhi: 410, Mumbai: 1210 },
    { grade: 'E5', Delhi: 380, Mumbai: 980 },
    { grade: 'E6', Delhi: 290, Mumbai: 650 },
    { grade: 'E7', Delhi: 195, Mumbai: 280 },
    { grade: 'E8', Delhi: 75, Mumbai: 110 },
    { grade: 'E9', Delhi: 25, Mumbai: 30 }
  ];

  const delhiTotal = comparisonData.reduce((acc, row) => acc + row.Delhi, 0);
  const mumbaiTotal = comparisonData.reduce((acc, row) => acc + row.Mumbai, 0);

  const delhiE7Plus = comparisonData.filter(r => ['E7', 'E8', 'E9'].includes(r.grade)).reduce((acc, r) => acc + r.Delhi, 0);
  const mumbaiE7Plus = comparisonData.filter(r => ['E7', 'E8', 'E9'].includes(r.grade)).reduce((acc, r) => acc + r.Mumbai, 0);

  // Store numbers (not strings with '%')
  const delhiE7Share = Math.round((delhiE7Plus / delhiTotal) * 1000) / 10; // 12.0
  const mumbaiE7Share = Math.round((mumbaiE7Plus / mumbaiTotal) * 1000) / 10; // 6.2

  const data = {
    turn_id: 'turn_v2_compare_delhi_mumbai',
    language: 'en',
    persona: 'CMD',
    spoken_summary: `Comparing executive headcount across grades E0 to E9 between Delhi Corporate HQ and Mumbai Western Offshore. Mumbai maintains a higher operational workforce of ${mumbaiTotal.toLocaleString('en-IN')} executives compared to Delhi\'s ${delhiTotal.toLocaleString('en-IN')}. However, Delhi concentrates a higher proportion of senior management at grade E7 and above (${delhiE7Share}% vs ${mumbaiE7Share}%).`,
    display_text: `Headcount comparison across grades E0–E9 for Delhi HQ (WC-DEL) vs Mumbai Western Offshore (WC-MUM) from hrfin_gold.ssot_workforce_employee [1]. Mumbai leads in junior to mid operational grades (${mumbaiTotal}), while Delhi has higher senior leadership concentration (${delhiE7Share}% vs ${mumbaiE7Share}%).`,
    contract_version: 2,
    visual: {
      type: 'chart',
      mode: 'compare',
      title: 'Headcount Comparison: Delhi HQ vs Mumbai (Western Offshore) by Grade',
      chart: {
        kind: 'grouped_bar',
        x: 'grade',
        unit: 'Executives',
        data: comparisonData
      },
      compare: {
        metric: 'headcount',
        shared_axis: true,
        items: [
          {
            label: 'Delhi HQ',
            chart: {
              kind: 'bar',
              x: 'grade',
              y: 'headcount',
              unit: 'Executives',
              data: comparisonData.map(r => ({ grade: r.grade, headcount: r.Delhi }))
            },
            kpis: [
              {
                label: 'Total Headcount',
                value: delhiTotal,
                unit: 'Executives'
              },
              {
                label: 'E7+ Share',
                value: delhiE7Share,
                unit: '%'
              }
            ],
            filter: {
              field: 'wc_id',
              op: '=',
              value: 'DEL'
            }
          },
          {
            label: 'Mumbai (Western Offshore)',
            chart: {
              kind: 'bar',
              x: 'grade',
              y: 'headcount',
              unit: 'Executives',
              data: comparisonData.map(r => ({ grade: r.grade, headcount: r.Mumbai }))
            },
            kpis: [
              {
                label: 'Total Headcount',
                value: mumbaiTotal,
                unit: 'Executives'
              },
              {
                label: 'E7+ Share',
                value: mumbaiE7Share,
                unit: '%'
              }
            ],
            filter: {
              field: 'wc_id',
              op: '=',
              value: 'MUM'
            }
          }
        ]
      }
    },
    insights_v2: [
      {
        text: `Mumbai has ${(mumbaiTotal / delhiTotal).toFixed(1)}x the total executive headcount of Delhi, driven by offshore operational installations.`,
        kind: 'comparison'
      },
      {
        text: `Delhi exhibits nearly double the concentration of senior executives (E7+) at ${delhiE7Share}% versus ${mumbaiE7Share}% in Mumbai.`,
        kind: 'outlier',
        value: delhiE7Share,
        unit: '%',
        ref: 'Delhi HQ'
      }
    ],
    drilldowns: [
      {
        label: 'Only senior leadership (E7+)',
        question: 'Compare senior leadership (E7–E9) between Delhi and Mumbai',
        spec_patch: {
          add_filters: [
            { field: 'grade', op: 'in', value: ['E7', 'E8', 'E9'] }
          ]
        }
      }
    ],
    context_chips: [
      { label: 'CMD', kind: 'role' },
      { label: 'Headcount', kind: 'subject' },
      { label: 'Delhi vs Mumbai', kind: 'filter' }
    ],
    query_spec: {
      version: 1,
      domain: 'hr',
      metric: 'headcount',
      aggregation: 'count',
      dimensions: ['grade', 'wc_id'],
      filters: [
        { field: 'wc_id', op: 'in', value: ['DEL', 'MUM'] }
      ]
    },
    sources: [
      {
        kind: 'data',
        object: 'hrfin_gold.ssot_workforce_employee'
      }
    ],
    access: {
      status: 'allowed'
    },
    export_options: ['sheets', 'docs', 'word', 'pdf']
  };

  return data;
}

// -----------------------------------------------------------------------------
// 6. Fixture 6: v2_insights_drilldowns.json
// -----------------------------------------------------------------------------
function buildInsightsDrilldowns() {
  const workCentreData = [
    { work_centre: 'Mumbai (Western Offshore)', headcount: 6820 },
    { work_centre: 'Delhi (Corporate HQ)', headcount: 2450 },
    { work_centre: 'Dehradun (GEOPIC/KDMIPE)', headcount: 1890 },
    { work_centre: 'Ahmedabad', headcount: 1640 },
    { work_centre: 'Ankleshwar', headcount: 1520 },
    { work_centre: 'Vadodara', headcount: 1380 },
    { work_centre: 'Mehsana', headcount: 1290 },
    { work_centre: 'Rajahmundry', headcount: 1150 },
    { work_centre: 'Sivasagar', headcount: 1080 },
    { work_centre: 'Jorhat', headcount: 960 },
    { work_centre: 'Chennai', headcount: 840 },
    { work_centre: 'Kolkata', headcount: 710 },
    { work_centre: 'Karaikal', headcount: 620 },
    { work_centre: 'Agartala', headcount: 540 }
  ];

  const totalHeadcount = workCentreData.reduce((acc, row) => acc + row.headcount, 0);
  const mumbaiHeadcount = workCentreData[0].headcount;
  const mumbaiShare = Math.round((mumbaiHeadcount / totalHeadcount) * 1000) / 10; // 29.8
  const assamHeadcount = workCentreData.find(w => w.work_centre === 'Sivasagar').headcount +
                         workCentreData.find(w => w.work_centre === 'Jorhat').headcount; // 2040

  const data = {
    turn_id: 'turn_v2_insights_drilldowns',
    language: 'en',
    persona: 'CMD',
    spoken_summary: `Total executive headcount across fourteen ONGC work centres for fiscal year 2026. Mumbai Western Offshore remains the largest work centre with ${mumbaiHeadcount.toLocaleString('en-IN')} executives, followed by Delhi HQ with 2,450. North-East assets including Jorhat and Sivasagar deploy ${assamHeadcount.toLocaleString('en-IN')} executives with localized vacancy challenges.`,
    display_text: `FY26 executive distribution across 14 ONGC work centres [1]. Western Offshore (Mumbai) accounts for the largest deployment (${mumbaiHeadcount}, ${mumbaiShare}%), followed by Delhi Corporate HQ and Dehradun. Interactive drilldowns and category insights available.`,
    contract_version: 2,
    visual: {
      type: 'chart',
      mode: 'replace',
      title: 'Executive Headcount by Work Centre, FY26',
      chart: {
        kind: 'hbar',
        x: 'work_centre',
        y: 'headcount',
        unit: 'Executives',
        sort: 'desc',
        data: workCentreData
      },
      kpis: [
        {
          label: 'Total Headcount',
          value: totalHeadcount,
          unit: 'Executives'
        },
        {
          label: 'Work Centres',
          value: workCentreData.length,
          unit: 'Locations'
        },
        {
          label: 'Largest Centre',
          value: 'Mumbai',
          unit: `${mumbaiHeadcount.toLocaleString('en-IN')} Execs`
        }
      ]
    },
    insights_v2: [
      {
        text: `Total FY26 executive strength reaches ${totalHeadcount.toLocaleString('en-IN')} across 14 major work centres.`,
        kind: 'headline',
        value: totalHeadcount,
        unit: 'Executives'
      },
      {
        text: `Mumbai Western Offshore constitutes ${mumbaiShare}% of ONGC's total executive workforce with ${mumbaiHeadcount.toLocaleString('en-IN')} executives.`,
        kind: 'outlier',
        value: mumbaiHeadcount,
        unit: 'Executives',
        ref: 'Mumbai (Western Offshore)'
      },
      {
        text: `Assam assets (Sivasagar and Jorhat) together deploy ${assamHeadcount.toLocaleString('en-IN')} executives in active exploration blocks.`,
        kind: 'trend',
        value: assamHeadcount,
        unit: 'Executives',
        ref: 'Jorhat'
      },
      {
        text: 'Mehsana and Ankleshwar face near-term rotational shortages in mechanical and electrical disciplines.',
        kind: 'risk',
        ref: 'Mehsana'
      }
    ],
    drilldowns: [
      {
        label: 'Mumbai offshore vs onshore',
        question: 'Break down Mumbai headcount into offshore and onshore installations',
        spec_patch: {
          add_filters: [
            { field: 'wc_id', op: '=', value: 'MUM' }
          ],
          dimensions: ['facility_type']
        }
      },
      {
        label: 'Delhi HQ disciplines',
        question: 'Show discipline breakdown for Delhi Corporate HQ',
        spec_patch: {
          add_filters: [
            { field: 'wc_id', op: '=', value: 'DEL' }
          ],
          dimensions: ['discipline'],
          chart_kind: 'hbar'
        }
      },
      {
        label: 'North-East assets grade mix',
        question: 'Show grade distribution across Jorhat, Sivasagar, and Agartala',
        spec_patch: {
          add_filters: [
            { field: 'wc_id', op: 'in', value: ['JOR', 'SIV', 'AGA'] }
          ],
          dimensions: ['grade']
        }
      },
      {
        label: 'Compare Delhi and Mumbai',
        question: 'Compare Delhi HQ and Mumbai headcount by grade',
        spec_patch: {
          add_filters: [
            { field: 'wc_id', op: 'in', value: ['DEL', 'MUM'] }
          ],
          dimensions: ['grade', 'wc_id'],
          chart_kind: 'grouped_bar'
        }
      }
    ],
    context_chips: [
      { label: 'CMD', kind: 'role' },
      { label: 'FY26', kind: 'period' },
      { label: 'Work Centres', kind: 'population' }
    ],
    query_spec: {
      version: 1,
      domain: 'hr',
      metric: 'headcount',
      aggregation: 'count',
      dimensions: ['wc_id'],
      period: {
        fy: 'FY26'
      }
    },
    sources: [
      {
        kind: 'data',
        object: 'hrfin_gold.ssot_workforce_employee'
      }
    ],
    access: {
      status: 'allowed'
    },
    export_options: ['sheets', 'docs', 'word', 'pdf']
  };

  return data;
}

// -----------------------------------------------------------------------------
// 7. Fixture 7: v2_finance_pnl.json
// -----------------------------------------------------------------------------
function buildFinancePnl() {
  const pnlData = [
    { field: 'Mumbai High', profit_cr: 22450 },
    { field: 'Bassein', profit_cr: 8920 },
    { field: 'Gandhar', profit_cr: 4150 },
    { field: 'Ankleshwar', profit_cr: 1820 },
    { field: 'Ravva', profit_cr: 1240 },
    { field: 'Neelam & Heera', profit_cr: 980 },
    { field: 'Cambay', profit_cr: 310 },
    { field: 'Cauvery', profit_cr: 150 },
    { field: 'Rajasthan', profit_cr: -320 },
    { field: 'Jorhat', profit_cr: -680 },
    { field: 'Tripura', profit_cr: -1120 },
    { field: 'KG Deepwater', profit_cr: -1750 }
  ];

  const netProfit = pnlData.reduce((acc, r) => acc + r.profit_cr, 0);
  const lossMakingFields = pnlData.filter(r => r.profit_cr < 0);
  const lossCount = lossMakingFields.length;
  const totalLoss = lossMakingFields.reduce((acc, r) => acc + r.profit_cr, 0);
  const topAsset = pnlData[0].profit_cr;
  const topAssetShare = Math.round((topAsset / netProfit) * 1000) / 10; // 62.1

  const data = {
    turn_id: 'turn_v2_finance_pnl',
    language: 'en',
    persona: 'DIR_FIN',
    spoken_summary: `Field-wise profit and loss performance for fiscal year 2026 across twelve primary producing assets. Total net surplus is ${netProfit.toLocaleString('en-IN')} crore rupees, with Mumbai High generating ${topAsset.toLocaleString('en-IN')} crore rupees. Four frontier and mature fields registered operating losses requiring portfolio review.`,
    display_text: `FY26 asset-level profit & loss statement across 12 producing fields from hrfin_gold.ssot_asset_pnl [1]. Mumbai High (${topAsset.toLocaleString('en-IN')} Cr) and Bassein remain primary profit contributors, while 4 fields report net losses under prevailing realization and lifting cost structures.`,
    contract_version: 2,
    visual: {
      type: 'chart',
      mode: 'replace',
      title: 'Field-wise Profit & Loss (P&L), FY26',
      chart: {
        kind: 'hbar',
        x: 'field',
        y: 'profit_cr',
        unit: '₹ Cr',
        sort: 'desc',
        data: pnlData
      },
      kpis: [
        {
          label: 'Net Profit',
          value: netProfit,
          unit: '₹ Cr',
          delta: '+8.4% vs FY25'
        },
        {
          label: 'Loss-Making Fields',
          value: lossCount,
          unit: 'Fields',
          delta: '-1 vs FY25'
        },
        {
          label: 'Top Asset (Mumbai High)',
          value: topAsset,
          unit: '₹ Cr',
          delta: `${topAssetShare}% of total`
        }
      ]
    },
    insights_v2: [
      {
        text: `Net field-level profit for FY26 reached ₹${netProfit.toLocaleString('en-IN')} Cr, driven by offshore production gains.`,
        kind: 'headline',
        value: netProfit,
        unit: '₹ Cr'
      },
      {
        text: `Mumbai High generated ₹${topAsset.toLocaleString('en-IN')} Cr, contributing over ${topAssetShare}% of net operational surplus.`,
        kind: 'outlier',
        value: topAsset,
        unit: '₹ Cr',
        ref: 'Mumbai High'
      },
      {
        text: `Four fields (Rajasthan, Jorhat, Tripura, KG Deepwater) recorded cumulative losses of ₹${Math.abs(totalLoss).toLocaleString('en-IN')} Cr due to high operating and drilling amortizations.`,
        kind: 'risk',
        value: totalLoss,
        unit: '₹ Cr',
        ref: 'KG Deepwater'
      }
    ],
    drilldowns: [
      {
        label: 'Loss-making asset breakdown',
        question: 'Break down OPEX and lifting costs for the 4 loss-making fields',
        spec_patch: {
          add_filters: [
            { field: 'profit_cr', op: '<', value: 0 }
          ],
          dimensions: ['field', 'cost_head']
        }
      },
      {
        label: 'Offshore vs Onshore P&L',
        question: 'Compare total profit between offshore and onshore assets',
        spec_patch: {
          dimensions: ['asset_type']
        }
      }
    ],
    context_chips: [
      { label: 'DIR_FIN', kind: 'role' },
      { label: 'FY26', kind: 'period' },
      { label: 'Profit & Loss', kind: 'subject' },
      { label: '₹ Cr', kind: 'filter' }
    ],
    query_spec: {
      version: 1,
      domain: 'finance',
      metric: 'profit_cr',
      aggregation: 'sum',
      period: {
        fy: 'FY26'
      }
    },
    sources: [
      {
        kind: 'data',
        object: 'hrfin_gold.ssot_asset_pnl'
      }
    ],
    access: {
      status: 'allowed'
    },
    export_options: ['sheets', 'docs', 'word', 'pdf']
  };

  return data;
}

// -----------------------------------------------------------------------------
// Main execution
// -----------------------------------------------------------------------------
function main() {
  if (!fs.existsSync(V2_FIXTURES_DIR)) {
    fs.mkdirSync(V2_FIXTURES_DIR, { recursive: true });
  }

  const { data: roster419, rows: delhiRows, gradeDistribution } = buildRoster419();
  const roster2000 = buildRoster2000();
  const rosterPartial = buildRosterPartialDirFin(delhiRows);
  const rosterAggregate = buildRosterAggregateE2(gradeDistribution);
  const compareDelhiMumbai = buildCompareDelhiMumbai();
  const insightsDrilldowns = buildInsightsDrilldowns();
  const financePnl = buildFinancePnl();

  const fixtures = [
    { filename: 'v2_roster_419.json', content: roster419 },
    { filename: 'v2_roster_2000.json', content: roster2000 },
    { filename: 'v2_roster_partial_dirfin.json', content: rosterPartial },
    { filename: 'v2_roster_aggregate_e2.json', content: rosterAggregate },
    { filename: 'v2_compare_delhi_mumbai.json', content: compareDelhiMumbai },
    { filename: 'v2_insights_drilldowns.json', content: insightsDrilldowns },
    { filename: 'v2_finance_pnl.json', content: financePnl }
  ];

  console.log(`Writing ${fixtures.length} contract-v2 fixtures to: ${V2_FIXTURES_DIR}`);

  for (const f of fixtures) {
    const filePath = join(V2_FIXTURES_DIR, f.filename);
    const jsonStr = JSON.stringify(f.content, null, 2) + '\n';
    fs.writeFileSync(filePath, jsonStr, 'utf-8');
    const stats = fs.statSync(filePath);
    console.log(`  - ${f.filename.padEnd(32)}: ${stats.size.toString().padStart(8)} bytes`);
  }

  console.log('Contract-v2 fixtures generated successfully.');
}

main();
