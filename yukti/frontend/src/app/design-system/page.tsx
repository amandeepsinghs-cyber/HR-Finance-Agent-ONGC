'use client';

import React, { useEffect, useState } from 'react';
import { Sun, Moon, Filter, Bookmark, BarChart3, PieChart, TrendingUp, Layers, Check } from 'lucide-react';
import {
  Card,
  CardHeader,
  CardBody,
  Chip,
  Badge,
  BadgeTone,
  ContextChips,
  Toolbar,
  IconButton,
} from '@/components/ui/primitives';
import { ChartRenderer } from '@/components/renderers/ChartRenderer';
import { KpiRenderer } from '@/components/renderers/KpiRenderer';
import { TableRenderer } from '@/components/renderers/TableRenderer';
import { AuraShowcase } from './AuraShowcase';
import {
  KPI_SAMPLES,
  TABLE_SAMPLE,
  BAR_SPEC,
  HBAR_SPEC,
  DONUT_SPEC,
  LINE_SPEC,
  HISTOGRAM_SPEC,
  TREEMAP_SPEC,
  RANKED_SPEC,
} from './samples';

/* ------------------------------------------------------------------ Tokens config */

const SEMANTIC_TOKENS = [
  'canvas',
  'card',
  'surface',
  'surface-2',
  'ink',
  'ink-2',
  'ink-3',
  'hairline',
  'accent',
  'accent-deep',
  'accent-pale',
  'intel',
  'positive',
  'warning',
  'critical',
  'maroon',
  'brand-saffron',
  'brand-petrol',
] as const;

const CHART_CAT_TOKENS = [
  'chart-cat-1',
  'chart-cat-2',
  'chart-cat-3',
  'chart-cat-4',
  'chart-cat-5',
  'chart-cat-6',
  'chart-cat-7',
  'chart-cat-8',
  'chart-cat-9',
] as const;

const CHART_SEQ_TOKENS = [
  'chart-seq-1',
  'chart-seq-2',
  'chart-seq-3',
  'chart-seq-4',
  'chart-seq-5',
  'chart-seq-6',
] as const;

const BADGE_TONES: BadgeTone[] = ['neutral', 'accent', 'positive', 'warning', 'critical', 'maroon', 'intel'];

export default function DesignSystemPage() {
  const [theme, setTheme] = useState<'light' | 'dark'>('light');
  const [filterActive, setFilterActive] = useState<boolean>(false);
  const [toolbarChartType, setToolbarChartType] = useState<string>('bar');
  const [iconBtnActive, setIconBtnActive] = useState<boolean>(false);

  // Initialize theme from ?theme=dark query or html class on mount
  useEffect(() => {
    const q = new URLSearchParams(window.location.search);
    const urlDark = q.get('theme') === 'dark';
    if (urlDark) {
      setTheme('dark');
      document.documentElement.classList.add('dark');
    } else if (document.documentElement.classList.contains('dark')) {
      setTheme('dark');
    }
  }, []);

  const handleThemeChange = (newTheme: 'light' | 'dark') => {
    setTheme(newTheme);
    document.documentElement.classList.toggle('dark', newTheme === 'dark');
  };

  const isDark = theme === 'dark';

  return (
    <div className="bg-[var(--canvas)] min-h-screen h-screen overflow-auto">
      <div className="max-w-[88rem] mx-auto p-8 space-y-10">
        {/* Header with CardHeader-style title + theme switch Toolbar */}
        <header className="flex flex-wrap items-center justify-between gap-4 pb-6 border-b border-[var(--hairline)]">
          <div>
            <div className="text-label uppercase tracking-[0.08em] text-[var(--accent-deep)] dark:text-[var(--accent-soft)] mb-1">
              Internal Showcase
            </div>
            <h1 className="text-display font-display text-[var(--ink)]">
              Yukti Design System
            </h1>
            <p className="text-body text-[var(--ink-2)] mt-1">
              Visual review and light/dark theme verification for primitives, tokens, and reference charts
            </p>
          </div>
          <div className="flex items-center gap-3">
            <Toolbar<'light' | 'dark'>
              label="Theme mode"
              value={theme}
              onChange={handleThemeChange}
              options={[
                { value: 'light', label: 'Light', icon: <Sun className="w-3.5 h-3.5" /> },
                { value: 'dark', label: 'Dark', icon: <Moon className="w-3.5 h-3.5" /> },
              ]}
            />
          </div>
        </header>

        {/* 1. Typography */}
        <AuraShowcase isDark={isDark} />

        <Card as="section" data-testid="ds-typography">
          <CardHeader
            eyebrow="Type scale & Numerals"
            title="Typography"
            subtitle="Fluid type scale with Google Sans Flex / Text and tabular numeral styling"
          />
          <CardBody className="space-y-6">
            <div className="space-y-4 p-5 rounded-[var(--radius-card)] bg-[var(--surface)] border border-[var(--hairline)]">
              <div className="flex flex-col sm:flex-row sm:items-baseline justify-between gap-2 border-b border-[var(--hairline)] pb-3">
                <span className="text-caption font-mono text-[var(--ink-3)] w-32 shrink-0">text-display</span>
                <span className="text-display font-display text-[var(--ink)]">
                  Executive Briefing on ONGC HR & Financial Operations
                </span>
              </div>
              <div className="flex flex-col sm:flex-row sm:items-baseline justify-between gap-2 border-b border-[var(--hairline)] pb-3">
                <span className="text-caption font-mono text-[var(--ink-3)] w-32 shrink-0">text-headline</span>
                <span className="text-headline font-display text-[var(--ink)]">
                  Rotational Transfer Compliance and Station Overstay
                </span>
              </div>
              <div className="flex flex-col sm:flex-row sm:items-baseline justify-between gap-2 border-b border-[var(--hairline)] pb-3">
                <span className="text-caption font-mono text-[var(--ink-3)] w-32 shrink-0">text-title</span>
                <span className="text-title text-[var(--ink)]">
                  Delhi Corporate Headquarters (WC-DEL) Analysis
                </span>
              </div>
              <div className="flex flex-col sm:flex-row sm:items-baseline justify-between gap-2 border-b border-[var(--hairline)] pb-3">
                <span className="text-caption font-mono text-[var(--ink-3)] w-32 shrink-0">text-body</span>
                <span className="text-body text-[var(--ink)]">
                  Pursuant to JRTP Clause 3.0, regular executives completing five continuous years become due for rotation across 9 disciplines.
                </span>
              </div>
              <div className="flex flex-col sm:flex-row sm:items-baseline justify-between gap-2 border-b border-[var(--hairline)] pb-3">
                <span className="text-caption font-mono text-[var(--ink-3)] w-32 shrink-0">text-label</span>
                <span className="text-label text-[var(--ink-2)]">
                  STATION TENURE COMPLIANCE · CRITICAL
                </span>
              </div>
              <div className="flex flex-col sm:flex-row sm:items-baseline justify-between gap-2 border-b border-[var(--hairline)] pb-3">
                <span className="text-caption font-mono text-[var(--ink-3)] w-32 shrink-0">text-caption</span>
                <span className="text-caption text-[var(--ink-3)]">
                  Source: HR-SSOT database, verified against SAP ERP. Updated 22 October 2026.
                </span>
              </div>
            </div>

            <div className="p-5 rounded-[var(--radius-card)] bg-[var(--surface)] border border-[var(--hairline)]">
              <span className="text-caption font-mono text-[var(--ink-3)] block mb-2">tabular numerals · .tabular</span>
              <div className="tabular text-title font-medium text-[var(--ink)] flex flex-wrap items-baseline gap-10">
                <div>
                  <span className="text-caption text-[var(--ink-3)] block mb-0.5">FY26 Revenue</span>
                  <span>₹1,32,508 Cr</span>
                </div>
                <div>
                  <span className="text-caption text-[var(--ink-3)] block mb-0.5">Headcount</span>
                  <span>23,117</span>
                </div>
                <div>
                  <span className="text-caption text-[var(--ink-3)] block mb-0.5">Operating Ratio</span>
                  <span>21.5%</span>
                </div>
              </div>
            </div>
          </CardBody>
        </Card>

        {/* 2. Colour Tokens */}
        <Card as="section" data-testid="ds-colours">
          <CardHeader
            eyebrow="Tokens"
            title="Colour Tokens"
            subtitle="Semantic surface, ink, and chart palettes reflecting light and dark themes"
          />
          <CardBody className="space-y-6">
            <div>
              <div className="text-label uppercase tracking-[0.06em] text-[var(--ink-2)] mb-3">
                System & Brand Tokens
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3">
                {SEMANTIC_TOKENS.map((token) => (
                  <div
                    key={token}
                    className="flex items-center gap-3 p-2 rounded-[var(--radius-sm)] border border-[var(--hairline)] bg-[var(--surface)]"
                  >
                    <div
                      className="w-9 h-9 rounded-[var(--radius-sm)] border border-[var(--hairline)] shrink-0"
                      style={{ background: `var(--${token})` }}
                    />
                    <div className="min-w-0">
                      <div className="text-caption font-mono text-[var(--ink)] whitespace-nowrap">
                        --{token}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div>
              <div className="text-label uppercase tracking-[0.06em] text-[var(--ink-2)] mb-3">
                Chart Categorical Tokens (CVD-Aware)
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
                {CHART_CAT_TOKENS.map((token) => (
                  <div
                    key={token}
                    className="flex items-center gap-2.5 p-2 rounded-[var(--radius-sm)] border border-[var(--hairline)] bg-[var(--surface)]"
                  >
                    <div
                      className="w-8 h-8 rounded-[var(--radius-sm)] border border-[var(--hairline)] shrink-0"
                      style={{ background: `var(--${token})` }}
                    />
                    <div className="min-w-0">
                      <div className="text-caption font-mono text-[var(--ink)] whitespace-nowrap">
                        --{token}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div>
              <div className="text-label uppercase tracking-[0.06em] text-[var(--ink-2)] mb-3">
                Chart Sequential Tokens (Low → High Magnitude)
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-3 lg:grid-cols-6 gap-3">
                {CHART_SEQ_TOKENS.map((token) => (
                  <div
                    key={token}
                    className="flex items-center gap-2.5 p-2 rounded-[var(--radius-sm)] border border-[var(--hairline)] bg-[var(--surface)]"
                  >
                    <div
                      className="w-8 h-8 rounded-[var(--radius-sm)] border border-[var(--hairline)] shrink-0"
                      style={{ background: `var(--${token})` }}
                    />
                    <div className="min-w-0">
                      <div className="text-caption font-mono text-[var(--ink)] whitespace-nowrap">
                        --{token}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </CardBody>
        </Card>

        {/* 3. Primitives */}
        <Card as="section" data-testid="ds-primitives">
          <CardHeader
            eyebrow="Foundations"
            title="UI Primitives"
            subtitle="Executive tactile surface containers, interactive pills, status badges, and segmented toolbars"
          />
          <CardBody className="space-y-8">
            {/* Card Variants */}
            <div>
              <div className="text-label uppercase tracking-[0.06em] text-[var(--ink-2)] mb-3">
                Card Variants
              </div>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <Card variant="raised">
                  <CardHeader eyebrow="Variant" title="Raised Card" />
                  <CardBody>
                    <p className="text-body text-[var(--ink-2)]">
                      Default card surface with subtle card-shadow and hairline border.
                    </p>
                  </CardBody>
                </Card>
                <Card variant="flat">
                  <CardHeader eyebrow="Variant" title="Flat Card" />
                  <CardBody>
                    <p className="text-body text-[var(--ink-2)]">
                      Surface background with hairline border for nested or lower-elevation panels.
                    </p>
                  </CardBody>
                </Card>
                <Card variant="glass">
                  <CardHeader eyebrow="Variant" title="Glass Card" />
                  <CardBody>
                    <p className="text-body text-[var(--ink-2)]">
                      Frosted glass surface with backdrop blur for floating overlays and modals.
                    </p>
                  </CardBody>
                </Card>
              </div>
            </div>

            {/* Chips */}
            <div>
              <div className="text-label uppercase tracking-[0.06em] text-[var(--ink-2)] mb-3">
                Chips (Pills)
              </div>
              <div className="flex flex-wrap items-center gap-3">
                <Chip>
                  Default Chip
                </Chip>
                <Chip selected>
                  Selected Chip
                </Chip>
                <Chip
                  selected={filterActive}
                  onClick={() => setFilterActive((v) => !v)}
                  icon={<Filter className="w-3.5 h-3.5" />}
                >
                  Filter with Icon
                </Chip>
                <Chip size="sm" icon={<Check className="w-3.5 h-3.5" />}>
                  Small Chip (sm)
                </Chip>
                <Chip size="md">
                  Medium Chip (md)
                </Chip>
              </div>
            </div>

            {/* Badges */}
            <div>
              <div className="text-label uppercase tracking-[0.06em] text-[var(--ink-2)] mb-3">
                Badges (All 7 Tones)
              </div>
              <div className="flex flex-wrap items-center gap-3">
                {BADGE_TONES.map((tone) => (
                  <Badge key={tone} tone={tone} dot={tone === 'accent'}>
                    {tone.charAt(0).toUpperCase() + tone.slice(1)}
                    {tone === 'accent' ? ' (dot)' : ''}
                  </Badge>
                ))}
              </div>
            </div>

            {/* ContextChips */}
            <div>
              <div className="text-label uppercase tracking-[0.06em] text-[var(--ink-2)] mb-3">
                ContextChips
              </div>
              <div className="p-4 rounded-[var(--radius-card)] bg-[var(--surface)] border border-[var(--hairline)]">
                <ContextChips
                  items={['CMD', 'Delhi HQ', 'Executives', 'FY26']}
                  source="SSOT"
                />
              </div>
            </div>

            {/* Toolbar and IconButton */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <div className="text-label uppercase tracking-[0.06em] text-[var(--ink-2)] mb-3">
                  Toolbar (5 Chart Types)
                </div>
                <Toolbar
                  label="Chart type selector"
                  value={toolbarChartType}
                  onChange={setToolbarChartType}
                  options={[
                    { value: 'bar', label: 'Bar', icon: <BarChart3 className="w-3.5 h-3.5" /> },
                    { value: 'hbar', label: 'H-Bar' },
                    { value: 'donut', label: 'Donut', icon: <PieChart className="w-3.5 h-3.5" /> },
                    { value: 'line', label: 'Line', icon: <TrendingUp className="w-3.5 h-3.5" /> },
                    { value: 'treemap', label: 'Treemap', icon: <Layers className="w-3.5 h-3.5" /> },
                  ]}
                />
              </div>

              <div>
                <div className="text-label uppercase tracking-[0.06em] text-[var(--ink-2)] mb-3">
                  IconButton (Normal + Active)
                </div>
                <div className="flex items-center gap-3">
                  <IconButton
                    label="Bookmark filter"
                    active={iconBtnActive}
                    onClick={() => setIconBtnActive((v) => !v)}
                  >
                    <Bookmark className="w-4 h-4" />
                  </IconButton>
                  <IconButton label="Bookmark active" active>
                    <Bookmark className="w-4 h-4" />
                  </IconButton>
                  <span className="text-caption text-[var(--ink-3)]">
                    Click first button to toggle active state
                  </span>
                </div>
              </div>
            </div>
          </CardBody>
        </Card>

        {/* 4. KPI */}
        <Card as="section" data-testid="ds-kpi">
          <CardHeader
            eyebrow="Metric Highlights"
            title="KPI Indicators"
            subtitle="Executive KPI card tiles with delta badges, formatting, and unit handling (e.g. Vacancy rate 8.5% · ▼1.2 pts vs FY25)"
          />
          <CardBody>
            <KpiRenderer kpis={KPI_SAMPLES} isDark={isDark} />
          </CardBody>
        </Card>

        {/* 5. Table */}
        <Card as="section" data-testid="ds-table">
          <CardHeader
            eyebrow="Tabular Data"
            title="Table View"
            subtitle="6 columns × 8 rows of executive tenure records with interactive sorting"
          />
          <CardBody>
            <TableRenderer table={TABLE_SAMPLE} isDark={isDark} />
          </CardBody>
        </Card>

        {/* 6. Reference Charts */}
        <Card as="section" data-testid="ds-charts">
          <CardHeader
            eyebrow="Visualisation Suite"
            title="Reference Charts"
            subtitle="7 responsive ECharts visual forms rendered at fixed height with live theme synchronization"
          />
          <CardBody>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* 1. Bar */}
              <Card className="h-[24rem] flex flex-col">
                <CardHeader eyebrow="Reference chart" title="Bar · Headcount by Work Centre" />
                <CardBody className="flex-1 min-h-0 pt-0 pb-4">
                  <div className="h-full w-full">
                    <ChartRenderer spec={BAR_SPEC} isDark={isDark} />
                  </div>
                </CardBody>
              </Card>

              {/* 2. H-Bar with negative values */}
              <Card className="h-[24rem] flex flex-col">
                <CardHeader eyebrow="Reference chart" title="H-bar · FY26 PBT by Field" />
                <CardBody className="flex-1 min-h-0 pt-0 pb-4">
                  <div className="h-full w-full">
                    <ChartRenderer spec={HBAR_SPEC} isDark={isDark} />
                  </div>
                </CardBody>
              </Card>

              {/* 3. Donut */}
              <Card className="h-[24rem] flex flex-col">
                <CardHeader eyebrow="Reference chart" title="Donut · Executives by Grade E1–E9" />
                <CardBody className="flex-1 min-h-0 pt-0 pb-4">
                  <div className="h-full w-full">
                    <ChartRenderer spec={DONUT_SPEC} isDark={isDark} />
                  </div>
                </CardBody>
              </Card>

              {/* 4. Line */}
              <Card className="h-[24rem] flex flex-col">
                <CardHeader eyebrow="Reference chart" title="Line · Revenue FY17–FY26" />
                <CardBody className="flex-1 min-h-0 pt-0 pb-4">
                  <div className="h-full w-full">
                    <ChartRenderer spec={LINE_SPEC} isDark={isDark} />
                  </div>
                </CardBody>
              </Card>

              {/* 5. Histogram */}
              <Card className="h-[24rem] flex flex-col">
                <CardHeader eyebrow="Reference chart" title="Histogram · Employee Age Distribution" />
                <CardBody className="flex-1 min-h-0 pt-0 pb-4">
                  <div className="h-full w-full">
                    <ChartRenderer spec={HISTOGRAM_SPEC} isDark={isDark} />
                  </div>
                </CardBody>
              </Card>

              {/* 6. Treemap */}
              <Card className="h-[24rem] flex flex-col">
                <CardHeader eyebrow="Reference chart" title="Treemap · Capex by Asset" />
                <CardBody className="flex-1 min-h-0 pt-0 pb-4">
                  <div className="h-full w-full">
                    <ChartRenderer spec={TREEMAP_SPEC} isDark={isDark} />
                  </div>
                </CardBody>
              </Card>

              {/* 7. Ranked H-Bar (non-diverging with "Others (6)") */}
              <Card data-testid="ds-chart-ranked" className="h-[24rem] flex flex-col">
                <CardHeader eyebrow="Reference chart" title="Ranked H-bar · Headcount by Discipline" />
                <CardBody className="flex-1 min-h-0 pt-0 pb-4">
                  <div className="h-full w-full">
                    <ChartRenderer spec={RANKED_SPEC} isDark={isDark} />
                  </div>
                </CardBody>
              </Card>
            </div>
          </CardBody>
        </Card>
      </div>
    </div>
  );
}
