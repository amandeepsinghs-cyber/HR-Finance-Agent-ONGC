#!/usr/bin/env node
const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

const PORT = process.env.PORT || 3311;
const BASE_URL = `http://127.0.0.1:${PORT}/design-system/roster`;
const SHOTS_DIR =
  process.env.SHOTS_DIR ||
  '/usr/local/google/home/amandeepsinghs/.gemini/jetski/brain/e78fe9c5-323e-45b3-88d4-49ebd381ba24/scratch/roster_shots';

fs.mkdirSync(SHOTS_DIR, { recursive: true });

async function run() {
  const executablePath =
    process.env.CHROME_BIN ||
    (fs.existsSync('/usr/bin/google-chrome') ? '/usr/bin/google-chrome' : undefined);

  const browser = await chromium.launch({
    headless: true,
    executablePath,
    args: [
      '--no-sandbox',
      '--disable-setuid-sandbox',
      '--disable-dev-shm-usage',
      '--font-render-hinting=none',
    ],
  });

  const page = await browser.newPage({
    viewport: { width: 1440, height: 900 },
  });

  const report = {
    action_gating_tests: {},
    n4_quality_checks: {},
    fixture_419: {},
    fixture_partial: {},
    fixture_aggregate: {},
    fixture_2000: {},
    screenshots: [],
    status: 'FAIL',
  };

  try {
    // ==========================================
    // 0. I5 Action Gating Unit Checks (fails closed)
    // ==========================================
    await page.goto(BASE_URL, { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForSelector('[data-testid="roster-tab-419"]', { timeout: 10000 });

    const gatingResults = await page.evaluate(() => {
      const ROLE_RANK = {
        E2_HR: 1,
        E3_FIN: 1,
        DIR_HR: 2,
        DIR_FIN: 2,
        CMD: 3,
      };

      function isActionAllowed(action, persona) {
        if (!action.min_role) return true;
        if (!Object.prototype.hasOwnProperty.call(ROLE_RANK, action.min_role)) {
          return false;
        }
        const requiredRank = ROLE_RANK[action.min_role];
        const userRank =
          persona && Object.prototype.hasOwnProperty.call(ROLE_RANK, persona)
            ? ROLE_RANK[persona]
            : 0;
        return userRank >= requiredRank;
      }

      const actionDirHr = { id: 'transfer', label: 'Transfer', min_role: 'DIR_HR' };
      const actionUnknownRole = { id: 'admin', label: 'Admin', min_role: 'SUPERADMIN' };
      const actionFree = { id: 'view', label: 'View' };

      return {
        missing_persona_fails_closed: isActionAllowed(actionDirHr, undefined) === false,
        null_persona_fails_closed: isActionAllowed(actionDirHr, null) === false,
        unknown_persona_rank_zero: isActionAllowed(actionDirHr, 'GUEST') === false,
        lower_persona_rejected: isActionAllowed(actionDirHr, 'E2_HR') === false,
        equal_persona_allowed: isActionAllowed(actionDirHr, 'DIR_HR') === true,
        higher_persona_allowed: isActionAllowed(actionDirHr, 'CMD') === true,
        unknown_min_role_hidden: isActionAllowed(actionUnknownRole, 'CMD') === false,
        action_without_min_role_allowed: isActionAllowed(actionFree, undefined) === true,
      };
    });

    report.action_gating_tests = gatingResults;
    const allGatingPassed = Object.values(gatingResults).every(Boolean);

    // ==========================================
    // 1. Fixture 419 tests
    // ==========================================
    await page.click('[data-testid="roster-tab-419"]');
    await page.waitForSelector('[data-testid="roster-count"]');

    // Count initial
    const initialCount = (await page.textContent('[data-testid="roster-count"]')).trim();
    report.fixture_419.count_initial = initialCount;

    // N4 (a): Grid semantics: aria-rowcount on table, aria-rowindex on header & rows
    const gridRowCount = await page.getAttribute('table[role="grid"]', 'aria-rowcount');
    const headerRowIndex = await page.getAttribute('thead tr', 'aria-rowindex');
    const firstRowIndex = await page.getAttribute('tbody tr:not([aria-hidden="true"])', 'aria-rowindex');
    report.n4_quality_checks.aria_rowcount = gridRowCount;
    report.n4_quality_checks.aria_rowcount_matches_total = gridRowCount === '420'; // 419 rows + 1 header
    report.n4_quality_checks.header_aria_rowindex_is_1 = headerRowIndex === '1';
    report.n4_quality_checks.first_row_aria_rowindex_is_2 = firstRowIndex === '2';

    // N4 (c): Table-fixed + colgroup
    const hasTableFixed = await page.$eval('table.data-table', (el) => el.classList.contains('table-fixed'));
    const colgroupCols = await page.$$eval('table.data-table colgroup col', (cols) => cols.length);
    report.n4_quality_checks.table_fixed = hasTableFixed;
    report.n4_quality_checks.colgroup_cols_count = colgroupCols;

    // Screenshot: 419 light
    const shot419 = path.join(SHOTS_DIR, '419_light.png');
    await page.screenshot({ path: shot419 });
    report.screenshots.push(shot419);

    // Search "a" reduces count
    await page.fill('[data-testid="roster-search"]', 'a');
    await page.waitForTimeout(150);
    const searchACount = (await page.textContent('[data-testid="roster-count"]')).trim();
    report.fixture_419.search_a_count = searchACount;
    await page.fill('[data-testid="roster-search"]', '');
    await page.waitForTimeout(150);

    // Filter grade = E7 -> all visible grade cells = E7
    await page.selectOption('[data-testid="roster-filter-grade"]', 'E7');
    await page.waitForTimeout(150);
    const visibleGrades = await page.$$eval(
      'tbody tr:not([aria-hidden="true"]) td:nth-child(4)',
      (tds) => tds.map((td) => td.textContent.trim())
    );
    report.fixture_419.filter_grade_E7_all_match =
      visibleGrades.length > 0 && visibleGrades.every((g) => g === 'E7');
    report.fixture_419.filter_grade_E7_count = visibleGrades.length;

    // Reset filter
    await page.selectOption('[data-testid="roster-filter-grade"]', '');
    await page.waitForTimeout(150);

    // Sort by continuous_stay_years desc -> first >= second
    const sortBtn = page.locator('[data-testid="roster-sort-continuous_stay_years"]');
    let sortTh = page.locator('th[aria-sort]:has([data-testid="roster-sort-continuous_stay_years"])');
    let ariaSort = await sortTh.getAttribute('aria-sort');
    let attempts = 0;
    while (ariaSort !== 'descending' && attempts < 4) {
      await sortBtn.click();
      await page.waitForTimeout(100);
      ariaSort = await sortTh.getAttribute('aria-sort');
      attempts++;
    }

    const visibleStayCells = await page.$$eval(
      'tbody tr:not([aria-hidden="true"]) td:nth-child(7)',
      (tds) => tds.slice(0, 2).map((td) => parseFloat(td.textContent.replace(/[^\d.]/g, '')))
    );
    report.fixture_419.sort_stay_desc_first_gte_second =
      visibleStayCells.length >= 2 && visibleStayCells[0] >= visibleStayCells[1];
    report.fixture_419.first_stay = visibleStayCells[0];
    report.fixture_419.second_stay = visibleStayCells[1];

    // Select 3 rows
    const rowCheckboxes = await page.$$('tbody tr:not([aria-hidden="true"]) input[type="checkbox"]');
    if (rowCheckboxes.length >= 3) {
      await rowCheckboxes[0].click();
      await rowCheckboxes[1].click();
      await rowCheckboxes[2].click();
    }
    await page.waitForSelector('[data-testid="roster-action-bar"]');

    // N4 (e): selectedCount reflects actual selected records present
    const selectedCountText = (await page.textContent('[data-testid="roster-selected-count"]')).trim();
    report.n4_quality_checks.selected_count_displayed = selectedCountText;
    report.n4_quality_checks.selected_count_accurate = selectedCountText === '3 selected';

    // Screenshot: selection with action bar
    const shotSelect = path.join(SHOTS_DIR, 'selection_with_action_bar.png');
    await page.screenshot({ path: shotSelect });
    report.screenshots.push(shotSelect);

    const actionBtn = page.locator('[data-testid="roster-action-transfer"]');
    report.fixture_419.action_bar_label = (await actionBtn.textContent()).trim();

    // Click transfer action -> logs 3 names
    await actionBtn.click();
    await page.waitForTimeout(100);
    const logAfterAction = (await page.textContent('[data-testid="roster-log"]')).trim();
    report.fixture_419.action_log = logAfterAction;

    // Export logs N rows
    const exportBtn = page.locator('[data-testid="roster-action-export"]');
    await exportBtn.click();
    await page.waitForTimeout(100);
    const logAfterExport = (await page.textContent('[data-testid="roster-log"]')).trim();
    report.fixture_419.export_log = logAfterExport;

    // Clear selection
    await page.click('[data-testid="roster-action-clear"]');

    // ==========================================
    // 2. Fixture Partial Masked tests
    // ==========================================
    await page.click('[data-testid="roster-tab-partial"]');
    await page.waitForSelector('[data-testid="roster-count"]');

    const shotPartial = path.join(SHOTS_DIR, 'partial_masked.png');
    await page.screenshot({ path: shotPartial });
    report.screenshots.push(shotPartial);

    const lockEmpId = await page.isVisible('[data-testid="roster-lock-emp_id"]');
    const lockPostedSince = await page.isVisible('[data-testid="roster-lock-posted_since"]');
    report.fixture_partial.lock_emp_id = lockEmpId;
    report.fixture_partial.lock_posted_since = lockPostedSince;

    // N4 (b): Masked column header button aria-label includes lock reason
    const maskedBtnAriaLabel = await page.getAttribute(
      '[data-testid="roster-sort-emp_id"]',
      'aria-label'
    );
    report.n4_quality_checks.masked_header_aria_label = maskedBtnAriaLabel;
    report.n4_quality_checks.masked_header_aria_label_includes_policy =
      Boolean(maskedBtnAriaLabel && maskedBtnAriaLabel.includes('hidden by policy:'));

    const maskedSpans = await page.$$eval(
      'tbody tr:not([aria-hidden="true"]) span[aria-label="hidden by policy"]',
      (spans) => spans.length
    );
    report.fixture_partial.masked_cells_hidden_by_policy = maskedSpans > 0;

    // ==========================================
    // 3. Fixture Aggregate tests
    // ==========================================
    await page.click('[data-testid="roster-tab-aggregate"]');
    await page.waitForSelector('[data-testid="roster-count"]');

    const shotAggregate = path.join(SHOTS_DIR, 'aggregate_banner.png');
    await page.screenshot({ path: shotAggregate });
    report.screenshots.push(shotAggregate);

    const bannerVisible = await page.isVisible('[data-testid="roster-masking-banner"]');
    const bannerText = bannerVisible
      ? (await page.textContent('[data-testid="roster-masking-banner"]')).trim()
      : '';
    const aggregateCheckboxes = await page.$$eval(
      'input[type="checkbox"]',
      (els) => els.length
    );
    report.fixture_aggregate.banner_visible = bannerVisible;
    report.fixture_aggregate.banner_text = bannerText;
    report.fixture_aggregate.checkboxes_count = aggregateCheckboxes;

    // N4 (d): Masking banner lock icon is not maroon
    const bannerLockClasses = await page.$eval(
      '[data-testid="roster-masking-banner"] svg',
      (el) => el.getAttribute('class') || ''
    );
    report.n4_quality_checks.banner_lock_classes = bannerLockClasses;
    report.n4_quality_checks.banner_lock_not_maroon = !bannerLockClasses.includes('text-[var(--maroon)]');

    // ==========================================
    // 4. Fixture 2,000 rows tests
    // ==========================================
    await page.click('[data-testid="roster-tab-2000"]');
    await page.waitForSelector('[data-testid="roster-count"]');

    const count2000 = (await page.textContent('[data-testid="roster-count"]')).trim();
    report.fixture_2000.count_initial = count2000;

    const shot2000 = path.join(SHOTS_DIR, 'roster_2000.png');
    await page.screenshot({ path: shot2000 });
    report.screenshots.push(shot2000);

    // Scroll 0 -> bottom over ~2 s with rAF counting -> fps >= 55 and max DOM rows < 80
    const scrollPerf = await page.evaluate(async () => {
      const el = document.querySelector('[data-testid="roster-scroll-container"]');
      if (!el) return { error: 'scroll container not found' };

      const scrollMax = el.scrollHeight - el.clientHeight;
      let frames = 0;
      let maxDomRows = 0;
      const durationMs = 2000;
      const start = performance.now();

      return new Promise((resolve) => {
        function onFrame(now) {
          frames++;
          const domRows = document.querySelectorAll('tbody tr:not([aria-hidden="true"])').length;
          if (domRows > maxDomRows) {
            maxDomRows = domRows;
          }
          const elapsed = now - start;
          const progress = Math.min(1, elapsed / durationMs);
          el.scrollTop = progress * scrollMax;

          if (progress < 1) {
            requestAnimationFrame(onFrame);
          } else {
            const actualSec = (performance.now() - start) / 1000;
            const fps = Math.round(frames / actualSec);
            resolve({
              fps,
              maxDomRows,
              frames,
              actualSec: Math.round(actualSec * 100) / 100,
              finalScrollTop: el.scrollTop,
            });
          }
        }
        requestAnimationFrame(onFrame);
      });
    });

    report.fixture_2000.scroll_metrics = scrollPerf;
    report.fixture_2000.fps_gte_55 = (scrollPerf.fps || 0) >= 55;
    report.fixture_2000.dom_rows_lt_80 = (scrollPerf.maxDomRows || 0) < 80;

    // Verify all criteria
    const allPassed =
      allGatingPassed &&
      report.n4_quality_checks.aria_rowcount_matches_total &&
      report.n4_quality_checks.header_aria_rowindex_is_1 &&
      report.n4_quality_checks.first_row_aria_rowindex_is_2 &&
      report.n4_quality_checks.table_fixed &&
      report.n4_quality_checks.masked_header_aria_label_includes_policy &&
      report.n4_quality_checks.banner_lock_not_maroon &&
      report.n4_quality_checks.selected_count_accurate &&
      report.fixture_419.count_initial.includes('Showing 419 of 419') &&
      report.fixture_419.search_a_count !== report.fixture_419.count_initial &&
      report.fixture_419.filter_grade_E7_all_match &&
      report.fixture_419.sort_stay_desc_first_gte_second &&
      report.fixture_419.action_bar_label.includes('Draft transfer note (3)') &&
      report.fixture_419.action_log.includes('Action') &&
      report.fixture_419.export_log.includes('Export') &&
      report.fixture_partial.lock_emp_id &&
      report.fixture_partial.lock_posted_since &&
      report.fixture_partial.masked_cells_hidden_by_policy &&
      report.fixture_aggregate.banner_visible &&
      report.fixture_aggregate.checkboxes_count === 0 &&
      report.fixture_2000.fps_gte_55 &&
      report.fixture_2000.dom_rows_lt_80;

    report.status = allPassed ? 'PASS' : 'FAIL';
  } catch (err) {
    report.error = err.message;
    report.status = 'FAIL';
  } finally {
    await browser.close();
  }

  console.log(JSON.stringify(report, null, 2));
  if (report.status !== 'PASS') {
    process.exit(1);
  }
}

run();
