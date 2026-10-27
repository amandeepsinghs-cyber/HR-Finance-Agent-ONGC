/**
 * Content for the "How Yukti works" explorer (27-Oct).
 * Keep in step with docs/ARCHITECTURE.md and docs/ORCHESTRATION_EXPLANATION.md.
 * Card boxes use the coordinates of public/architecture/yukti_architecture.svg (1520 × 620).
 */

export const DIAGRAM_W = 1520;
export const DIAGRAM_H = 620;

export interface ComponentDetail {
  id: string;
  title: string;
  kind: string;
  box: { x: number; y: number; w: number; h: number };
  oneLiner: string;
  plain: string[];
  how: string[];
  inputs: string;
  outputs: string;
  guardrails: string[];
  code: string[];
  example?: string;
}

export const COMPONENTS: ComponentDetail[] = [
  {
    id: 'users',
    title: 'ONGC users',
    kind: 'People',
    box: { x: 20, y: 140, w: 178, h: 150 },
    oneLiner: 'Leaders and HR / Finance staff ask questions by voice or text.',
    plain: [
      'Anyone approved can open Yukti in a browser and talk or type.',
      'Each person picks a role at sign-in; that role decides what they are allowed to see on every single answer.',
      'Answers come back as speech plus charts, tables, KPI cards or documents.',
    ],
    how: [
      'Eleven demo personas: CMD, Director HR, Director Finance and E1–E4 HR / Finance officers.',
      'The chosen role is stored in a server-signed cookie; saying “I am the CMD” does not change it.',
    ],
    inputs: 'Voice (microphone) or typed questions',
    outputs: 'Spoken answer, on-screen visual, exports',
    guardrails: ['Role cannot be changed by what the user says', 'Role-switch is a deliberate, signed action'],
    code: ['yukti/frontend/src/personas.ts', 'yukti/backend/app/auth.py'],
    example: 'Director Finance: “What was PAT in FY25?”',
  },
  {
    id: 'iap',
    title: 'Identity-Aware Proxy',
    kind: 'Google Cloud security',
    box: { x: 242, y: 140, w: 160, h: 150 },
    oneLiner: 'Google sign-in in front of the whole app; only approved accounts get in.',
    plain: [
      'Before anything loads, Google checks who you are.',
      'Only accounts explicitly approved for Yukti can reach it — there is no public link.',
    ],
    how: [
      'IAP is enabled directly on the Cloud Run service.',
      'Access is granted per user with the role “IAP-secured Web App User”.',
    ],
    inputs: 'Browser request',
    outputs: 'Authenticated request to Cloud Run, or a Google sign-in page',
    guardrails: ['No anonymous access', 'Access list managed in Google Cloud IAM'],
    code: ['APP_LINK.md — commands to add or remove users'],
  },
  {
    id: 'cloudbuild',
    title: 'Cloud Build',
    kind: 'Google Cloud delivery',
    box: { x: 242, y: 360, w: 160, h: 190 },
    oneLiner: 'Builds the container and releases it safely, with one-step rollback.',
    plain: [
      'Every release is built the same way and stored as a versioned image.',
      'A new version first goes live with no users on it, is checked, and only then receives traffic.',
      'If anything looks wrong, one command switches back to the previous version.',
    ],
    how: [
      'Cloud Build runs the Dockerfile: design-token and contrast lint, type check, Next.js build, Python dependencies.',
      'Image stored in Artifact Registry; deployed with --no-traffic and a tag, startup logs checked, then update-traffic.',
      'Each revision is labelled with its git commit.',
    ],
    inputs: 'Source code at a git commit',
    outputs: 'Container image and a Cloud Run revision',
    guardrails: ['Build fails on lint or type errors', 'No-traffic first, then switch', 'Rollback documented in APP_LINK.md'],
    code: ['Dockerfile', 'start_cloudrun.sh'],
  },
  {
    id: 'webapp',
    title: 'Yukti web app',
    kind: 'Cloud Run · Next.js',
    box: { x: 442, y: 100, w: 232, h: 210 },
    oneLiner: 'The screen you use: voice orb, charts, tables, exports.',
    plain: [
      'Shows the aurora voice orb — tap to talk, tap again to stop.',
      'Draws every answer as a chart, table, KPI card or document, and lets you export to PDF, Excel or Word.',
      'Filters background noise on your device before sending your voice.',
    ],
    how: [
      'Next.js app served by server.js, which also proxies /api/*, /health and /ws/live to the backend in the same container (one origin, no CORS).',
      'Voice: microphone audio is streamed over a WebSocket to the backend, which relays it to Gemini Live.',
      'Answer contracts are rendered by ChartRenderer, TableRenderer, KpiRenderer and AnswerCard.',
    ],
    inputs: 'Your voice or text; answer contracts from the backend',
    outputs: 'Audio stream, questions, rendered answers, exports',
    guardrails: ['Only allow-listed paths are proxied to the backend', 'Local noise gate and gain cap on the microphone'],
    code: ['yukti/frontend/server.js', 'yukti/frontend/src/app/page.tsx', 'yukti/frontend/src/components/'],
  },
  {
    id: 'orchestrator',
    title: 'Turn orchestrator',
    kind: 'Cloud Run · FastAPI · code',
    box: { x: 704, y: 100, w: 238, h: 210 },
    oneLiner: 'Decides who answers each question — with a fixed ladder of checks, in code.',
    plain: [
      'Every question goes down a fixed list of about 15 checks; the first one that matches answers it.',
      'Safety comes first: your role is checked before any data is touched.',
      'Simple, specific questions are answered by fast specialist code; only open data questions reach the AI planner.',
      'After every answer, restricted fields are masked for your role before anything is shown or remembered.',
    ],
    how: [
      'AgentTurnRunner._execute_turn_inner: normalise speech, resolve the signed role, detect language, load session memory (including what is on screen).',
      'Ladder: control → access check → simple intents → specialists (DCF follow-up, coordinator, revenue drivers, oil) → planner → small talk.',
      'Each specialist is wrapped in try/except and falls through to the next check on failure.',
      'Post-processing on every turn: enforce_contract masking, session stores the masked contract, export registration, schema validation.',
    ],
    inputs: 'Question, signed role, session memory, on-screen context',
    outputs: 'A validated, masked answer contract',
    guardrails: ['Access check before any data handler', 'Masking on every answer', 'Fail soft — no dead ends'],
    code: ['yukti/backend/app/turn_runner.py', 'docs/ORCHESTRATION_EXPLANATION.md'],
    example: 'See “Inside the orchestrator” below for the full ladder.',
  },
  {
    id: 'specialists',
    title: 'Specialist modules & tools',
    kind: 'Code · agent-ready registry',
    box: { x: 972, y: 100, w: 236, h: 210 },
    oneLiner: 'Purpose-built code for valuation, diagnostics, HR actions, documents and market data.',
    plain: [
      'Specialists are declared in one registry with their trigger phrases, allowed roles and whether they need your confirmation.',
      'A DCF valuation only runs after you confirm the assumptions, and then runs in the background with progress steps.',
      'Today each specialist runs code, not its own AI — which keeps answers repeatable. The registry is ready to host AI sub-agents later.',
    ],
    how: [
      'Coordinator: resolve pending confirmations → first matching trigger regex in registry.yaml → requires_role gate.',
      'dcf_agent → proposal with editable inputs → background job (WACC, forecast, valuation, sensitivity, tornado, XLSX).',
      'Board note / memo / parliament reply → policy check → DocumentDraftingEngine using the data on screen.',
      'Other modules (fin_diagnostics, hr_transfer, analyst) delegate to the planner pipeline.',
      'Also: SQL compiler, DCF follow-ups, revenue drivers & product mix, oil and rupee overlays, exports.',
    ],
    inputs: 'Question routed by the orchestrator',
    outputs: 'Computed results: tables, valuations, drafts, files',
    guardrails: ['Per-module allowed roles', 'Confirmation gate for DCF', 'Numbers computed in code'],
    code: ['yukti/backend/app/agents/registry.yaml', 'yukti/backend/app/agents/coordinator.py', 'yukti/backend/app/finance/dcf/', 'yukti/backend/app/market/'],
    example: '“Run a DCF” → proposal → “Yes” → valuation, sensitivity and tornado.',
  },
  {
    id: 'live',
    title: 'Gemini Live',
    kind: 'AI agent — the only one',
    box: { x: 442, y: 370, w: 232, h: 190 },
    oneLiner: 'Hears and speaks; hands every data question to Yukti’s tools.',
    plain: [
      'Understands English, Hindi and Hinglish and replies in a natural voice.',
      'It is the only part of Yukti that reasons freely — but it is told never to answer data questions from memory.',
      'For any business question it calls Yukti’s engine and reads back the checked answer.',
    ],
    how: [
      'Native-audio Live model; audio relayed by app/live_session.py with server-side turn detection.',
      'Tools: ask_yukti (send a question to the orchestrator), ui_control and control_screen (change what is on screen).',
    ],
    inputs: 'Streaming microphone audio',
    outputs: 'Speech, plus tool calls to the orchestrator',
    guardrails: ['No figures from memory', 'Speaks only what the tools return for data questions'],
    code: ['yukti/backend/app/live_session.py'],
  },
  {
    id: 'flash',
    title: 'Gemini 2.5 Flash',
    kind: 'AI called like a function',
    box: { x: 704, y: 370, w: 238, h: 190 },
    oneLiner: 'Turns a question into a structured query plan, and writes explanations.',
    plain: [
      'Reads your question and fills in a structured form: which measure, which years, which breakdown, which chart.',
      'It never writes the database query and never invents numbers — code does the calculation.',
      'When it explains a result, every figure it mentions must exist in the data, or the sentence is replaced.',
    ],
    how: [
      'Planner returns a JSON QuerySpec (or a patch to the previous one); a deterministic compiler produces certified SQL.',
      'Narrator uses allowed_numbers from the result rows; anything else falls back to a deterministic summary.',
      'Also used for short conversational replies with no data and no digits.',
    ],
    inputs: 'Question, previous plan, recent history',
    outputs: 'QuerySpec JSON; number-checked explanation text',
    guardrails: ['Never writes SQL', 'Numbers checked against the result', 'Deterministic fallback'],
    code: ['yukti/backend/app/brain/planner.py', 'yukti/backend/app/brain/narrator.py', 'yukti/backend/app/brain/smalltalk.py'],
  },
  {
    id: 'bigquery',
    title: 'BigQuery',
    kind: 'ONGC single source of truth',
    box: { x: 972, y: 370, w: 236, h: 190 },
    oneLiner: 'Where every HR and finance number comes from.',
    plain: [
      'Holds the HR roster, postings and pay, ten years of financial statements, levies and valuation inputs.',
      'Only certified, pre-approved query shapes are run against it.',
    ],
    how: [
      'Datasets hrfin_*_v3 (BQ_DATASET_SUFFIX=v3).',
      'Compiled SQL is dry-run first (bytes checked), then executed.',
      'Pre-query policy checks the data classes a query would touch; junior roles get small-cell suppression on aggregates.',
    ],
    inputs: 'Certified SQL from the compiler',
    outputs: 'Result rows',
    guardrails: ['Certified queries only', 'Dry run before execution', 'Small-cell suppression'],
    code: ['yukti/backend/app/brain/compiler.py', 'dataform/'],
  },
  {
    id: 'yahoo',
    title: 'Yahoo Finance',
    kind: 'External market data',
    box: { x: 1282, y: 140, w: 208, h: 170 },
    oneLiner: 'Brent, WTI and the rupee against the dollar.',
    plain: [
      'Used to show oil prices and the rupee next to ONGC’s revenue, and to explain why revenue moved.',
      'Daily history is kept inside the app; only missing days are fetched, plus today’s price.',
      'If the feed is unavailable, Yukti uses the saved copy and says so.',
    ],
    how: ['History JSON files in app/market/history; incremental fetch; offline fallback.'],
    inputs: 'Ticker and date range',
    outputs: 'Daily and yearly average prices',
    guardrails: ['Cached copy if offline', 'Source shown on the chart'],
    code: ['yukti/backend/app/market/oil_prices.py', 'yukti/backend/app/market/revenue_drivers.py'],
  },
];

export interface LadderStep {
  n: string;
  title: string;
  example: string;
  plain: string;
  handler: string;
}

export interface LadderBand {
  id: string;
  name: string;
  why: string;
  tone: 'control' | 'safety' | 'simple' | 'specialist' | 'general';
  steps: LadderStep[];
}

export const LADDER: LadderBand[] = [
  {
    id: 'control',
    name: 'Control',
    why: 'Commands about the conversation or the screen are handled first — no data, no AI.',
    tone: 'control',
    steps: [
      { n: '1', title: 'Role switch', example: '“Sign in as Director HR”', plain: 'Opens the signed role switch; the role is never changed just because someone says so.', handler: 'turn_runner._role_switch_contract' },
      { n: '2', title: 'Screen command', example: '“Open the roster”, “export this”', plain: 'Recognises screen commands — but “plot Brent” or “what drives the valuation” are treated as new questions, not re-plots.', handler: 'live_session.detect_screen_control_intent' },
      { n: '3', title: 'Pending year question', example: 'Yukti asked “which year?” → “last year”', plain: 'Fills the year into the question you asked before and runs it.', handler: 'turn_runner (clarify) → run_planner_turn' },
      { n: '4', title: 'Chart / UI change', example: '“Make it a waterfall”', plain: 'Re-draws the data already on screen. No new query.', handler: 'intents.ui_control.handle_ui_control' },
    ],
  },
  {
    id: 'safety',
    name: 'Safety',
    why: 'Before any data, policy or specialist is touched, the role is checked.',
    tone: 'safety',
    steps: [
      { n: '5', title: 'Access check', example: 'A junior asks for named salaries', plain: 'Refuses with the rule that applies and offers a safe alternative, such as an aggregate view.', handler: 'check_access → build_refusal_contract' },
    ],
  },
  {
    id: 'simple',
    name: 'Simple intents',
    why: 'Common, well-defined requests have direct answers.',
    tone: 'simple',
    steps: [
      { n: '6', title: 'Greeting', example: '“Good morning”', plain: 'A friendly greeting with suggestions.', handler: 'intents.greeting.handle_greeting' },
      { n: '7', title: 'Coverage', example: '“Which years do you have?”', plain: 'What data is available.', handler: 'intents.coverage.handle_coverage' },
      { n: '8', title: 'HR policy', example: '“What is the transfer policy?”', plain: 'Answers from the policy corpus.', handler: 'intents.policy.handle_policy' },
      { n: '9', title: 'Transfer note', example: '“Draft a transfer note for these”', plain: 'Drafts a note from the employees selected on screen.', handler: 'brain.documents.transfer_note_contract' },
    ],
  },
  {
    id: 'specialist',
    name: 'Specialists',
    why: 'Specific before general: purpose-built code answers what it knows best.',
    tone: 'specialist',
    steps: [
      { n: '10', title: 'DCF follow-up', example: '“What drives the valuation?”, “What if WACC is 12%?”', plain: 'Answers from the DCF already run in this chat, or re-runs it with your change.', handler: 'finance.dcf.followup' },
      { n: '11', title: 'Coordinator', example: '“Run a DCF”, “Draft a board note”', plain: 'Matches the agent registry and checks your role. DCF waits for your confirmation; board notes are drafted; other modules hand on to the planner.', handler: 'agents.coordinator.route_turn' },
      { n: '12', title: 'Revenue drivers & mix', example: '“Why did revenue hold up while oil fell?”', plain: 'Splits the change into price, volume, rupee and product mix.', handler: 'market.revenue_drivers' },
      { n: '13', title: 'Oil & rupee plot', example: '“Plot Brent for 5 years”', plain: 'Market history; falls through if the feed is down.', handler: 'market.oil_intent' },
    ],
  },
  {
    id: 'general',
    name: 'General',
    why: 'Only when nothing specific matches does the AI planner run — and it still never writes SQL or numbers.',
    tone: 'general',
    steps: [
      { n: '14', title: 'Planner pipeline', example: '“Headcount by grade in FY25”', plain: 'Gemini Flash fills a structured plan → code compiles certified SQL → policy check → BigQuery → chart and number-checked explanation.', handler: 'brain.pipeline.run_planner_turn' },
      { n: '15', title: 'Small talk', example: '“Thanks!”', plain: 'A short conversational reply — no data, no figures.', handler: 'brain.smalltalk' },
    ],
  },
];

export const AFTER_EVERY_ANSWER = [
  'Role-based masking of rows and text (enforce_contract)',
  'Session memory keeps only the masked answer',
  'Export registration — PDF, Excel and Word use exactly what was shown',
  'Answer validated against the contract schema',
];
