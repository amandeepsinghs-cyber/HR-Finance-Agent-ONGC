/**
 * Yukti surface primitives (U1.3, FEAT-005).
 *
 * Executive "tactile minimalism": frosted-glass headers, hairline borders, ambient shadows.
 * Every colour/radius/shadow comes from design tokens (src/design/tokens.json) via CSS variables,
 * so light/dark parity is automatic. Prefer these primitives over ad-hoc `div` + Tailwind styling.
 *
 *   <Card>                       surface container (variants: 'raised' | 'flat' | 'glass')
 *     <CardHeader eyebrow title subtitle actions chips />
 *     <CardBody>…</CardBody>
 *     <CardFooter>…</CardFooter>
 *   </Card>
 *   <Chip>            interactive pill (suggestion / drill-down / filter); `selected`, `icon`
 *   <Badge>           non-interactive status label (tones: neutral | accent | positive | warning | critical | maroon | intel)
 *   <ContextChips>    metadata row, e.g. CMD · Delhi HQ · Executives · FY26 · Source: SSOT
 *   <Toolbar>         compact segmented control (e.g. chart-type switcher)
 *   <IconButton>      square icon action with accessible label
 */
import React, { createContext, useContext, useRef } from 'react';
import clsx from 'clsx';

/* ------------------------------------------------------------------ Card */

export type CardVariant = 'raised' | 'flat' | 'glass';

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: CardVariant;
  /** remove inner padding (e.g. full-bleed charts/tables) */
  bleed?: boolean;
  as?: 'div' | 'section' | 'article';
}

/** Cards with `bleed` render header/body/footer without horizontal padding (full-bleed charts/tables). */
const CardBleedContext = createContext(false);

const CARD_VARIANT: Record<CardVariant, string> = {
  raised: 'bg-[var(--card)] border border-[var(--hairline)] shadow-[var(--card-shadow)]',
  flat: 'bg-[var(--surface)] border border-[var(--hairline)]',
  glass: 'bg-[var(--glass)] border border-[var(--hairline)] shadow-[var(--card-shadow)] backdrop-blur-md',
};

export const Card = React.forwardRef<HTMLDivElement, CardProps>(function Card(
  { variant = 'raised', bleed = false, as = 'div', className, children, ...rest },
  ref,
) {
  const Tag = as as any;
  return (
    <Tag
      ref={ref}
      data-ui="card"
      data-variant={variant}
      data-bleed={bleed || undefined}
      className={clsx('rounded-card overflow-hidden', CARD_VARIANT[variant], className)}
      {...rest}
    >
      <CardBleedContext.Provider value={bleed}>{children}</CardBleedContext.Provider>
    </Tag>
  );
});

export interface CardHeaderProps extends Omit<React.HTMLAttributes<HTMLDivElement>, 'title'> {
  /** heading level for the title (default h2) */
  titleAs?: 'h1' | 'h2' | 'h3' | 'h4';
  /** small uppercase kicker above the title (e.g. "Executive briefing") */
  eyebrow?: React.ReactNode;
  title?: React.ReactNode;
  subtitle?: React.ReactNode;
  /** right-aligned actions (IconButton / Toolbar / export) */
  actions?: React.ReactNode;
  /** metadata row under the title (ContextChips) */
  chips?: React.ReactNode;
  /** frosted sticky header for scrolling cards */
  sticky?: boolean;
}

export const CardHeader = React.forwardRef<HTMLDivElement, CardHeaderProps>(function CardHeader(
  { eyebrow, title, subtitle, actions, chips, sticky, titleAs: TitleTag = 'h2', className, children, ...rest },
  ref,
) {
  const bleed = useContext(CardBleedContext);
  return (
    <div
      ref={ref}
      data-ui="card-header"
      className={clsx(
        'flex items-start justify-between gap-4 pt-5 pb-4',
        bleed ? 'px-0' : 'px-6',
        sticky && 'sticky top-0 z-10 bg-[var(--glass)] backdrop-blur-md border-b border-[var(--hairline)]',
        className,
      )}
      {...rest}
    >
      <div className="min-w-0 flex-1">
        {eyebrow && <div className="text-label uppercase tracking-[0.08em] text-[var(--accent-deep)] dark:text-[var(--accent-soft)] mb-1">{eyebrow}</div>}
        {title && <TitleTag className="text-headline font-display text-[var(--ink)] truncate">{title}</TitleTag>}
        {subtitle && <p className="text-body text-[var(--ink-2)] mt-1">{subtitle}</p>}
        {chips && <div className="mt-2.5">{chips}</div>}
        {children}
      </div>
      {actions && <div className="flex shrink-0 items-center gap-1.5">{actions}</div>}
    </div>
  );
});

export const CardBody = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(function CardBody({ className, ...rest }, ref) {
  const bleed = useContext(CardBleedContext);
  return <div ref={ref} data-ui="card-body" className={clsx(bleed ? 'px-0 pb-0' : 'px-6 pb-6', className)} {...rest} />;
});

export const CardFooter = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(function CardFooter({ className, ...rest }, ref) {
  const bleed = useContext(CardBleedContext);
  return (
    <div
      ref={ref}
      data-ui="card-footer"
      className={clsx('flex items-center justify-between gap-3 py-3 border-t border-[var(--hairline)] text-caption text-[var(--ink-3)]', bleed ? 'px-0' : 'px-6', className)}
      {...rest}
    />
  );
});

/* ------------------------------------------------------------------ Chip */

export interface ChipProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  selected?: boolean;
  icon?: React.ReactNode;
  size?: 'sm' | 'md';
}

export const Chip = React.forwardRef<HTMLButtonElement, ChipProps>(function Chip(
  { selected, icon, size = 'md', className, children, type = 'button', ...rest },
  ref,
) {
  return (
    <button
      ref={ref}
      type={type}
      data-ui="chip"
      aria-pressed={selected}
      className={clsx(
        'inline-flex items-center gap-1.5 rounded-pill border font-medium transition-colors duration-fast',
        'focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--accent)]',
        size === 'sm' ? 'px-2.5 py-1 text-caption' : 'px-3.5 py-1.5 text-label',
        selected
          ? // AA for small text: light = white on accent-deep (6.2:1); dark = tonal accent-soft on accent-pale (≥7:1)
            'bg-[var(--accent-deep)] border-[var(--accent-deep)] text-[var(--on-accent)] dark:bg-[var(--accent-pale)] dark:border-[var(--accent-soft)] dark:text-[var(--accent-soft)]'
          : 'bg-[var(--card)] border-[var(--hairline)] text-[var(--ink)] hover:bg-[var(--accent-pale)] hover:text-[var(--accent-deep)] dark:hover:text-[var(--accent-soft)]',
        className,
      )}
      {...rest}
    >
      {icon && <span className="shrink-0 [&>svg]:w-3.5 [&>svg]:h-3.5">{icon}</span>}
      {children}
    </button>
  );
});

/* ------------------------------------------------------------------ Badge */

export type BadgeTone = 'neutral' | 'accent' | 'positive' | 'warning' | 'critical' | 'maroon' | 'intel';

const BADGE_TONE: Record<BadgeTone, string> = {
  neutral: 'bg-[var(--surface-2)] text-[var(--ink-2)]',
  accent: 'bg-[var(--accent-pale)] text-[var(--accent-deep)] dark:text-[var(--accent-soft)]',
  positive: 'bg-[var(--positive-pale)] text-[var(--positive)]',
  warning: 'bg-[var(--warning-pale)] text-[var(--warning)]',
  critical: 'bg-[var(--maroon-pale)] text-[var(--maroon)] font-semibold', // AA: maroon ink (8.4:1 light / 4.6:1 dark); bright --critical is for fills/icons only
  maroon: 'bg-[var(--maroon-pale)] text-[var(--maroon)]',
  intel: 'bg-[var(--accent-pale)] text-[var(--intel)]',
};

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  tone?: BadgeTone;
  /** leading status dot */
  dot?: boolean;
  icon?: React.ReactNode;
}

export const Badge = React.forwardRef<HTMLSpanElement, BadgeProps>(function Badge({ tone = 'neutral', dot, icon, className, children, ...rest }, ref) {
  return (
    <span
      ref={ref}
      data-ui="badge"
      data-tone={tone}
      className={clsx('inline-flex items-center gap-1.5 rounded-pill px-2.5 py-0.5 text-caption font-medium whitespace-nowrap', BADGE_TONE[tone], className)}
      {...rest}
    >
      {dot && <span aria-hidden className="w-1.5 h-1.5 rounded-full bg-current" />}
      {icon && <span className="shrink-0 [&>svg]:w-3 [&>svg]:h-3">{icon}</span>}
      {children}
    </span>
  );
});

/* ------------------------------------------------------------------ ContextChips */

export interface ContextChipsProps extends React.HTMLAttributes<HTMLDivElement> {
  /** e.g. ['CMD', 'Delhi HQ', 'Executives', 'FY26'] */
  items: React.ReactNode[];
  /** trailing source label, e.g. "SSOT" */
  source?: React.ReactNode;
}

export function ContextChips({ items, source, className, ...rest }: ContextChipsProps) {
  const parts = items.filter(Boolean);
  return (
    <div data-ui="context-chips" className={clsx('flex flex-wrap items-center gap-x-2 gap-y-1 text-label font-normal text-[var(--ink-3)]', className)} {...rest}>
      {parts.map((p, i) => (
        <React.Fragment key={i}>
          {i > 0 && <span aria-hidden className="text-[var(--ink-3)]">·</span>}
          <span className="text-[var(--ink-2)]">{p}</span>
        </React.Fragment>
      ))}
      {source && (
        <>
          {parts.length > 0 && <span aria-hidden className="text-[var(--ink-3)]">·</span>}
          <span>Source: {source}</span>
        </>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ Toolbar (segmented control) */

export interface ToolbarOption<T extends string = string> {
  value: T;
  label: React.ReactNode;
  icon?: React.ReactNode;
  disabled?: boolean;
  /** tooltip / accessible description */
  title?: string;
}

export interface ToolbarProps<T extends string = string> {
  options: ToolbarOption<T>[];
  value: T;
  onChange: (v: T) => void;
  /** accessible group label */
  label: string;
  size?: 'sm' | 'md';
  className?: string;
}

export function Toolbar<T extends string = string>({ options, value, onChange, label, size = 'sm', className }: ToolbarProps<T>) {
  // WAI-ARIA radio-group pattern: one tab stop (the checked radio), arrows/Home/End move + select.
  const refs = useRef<(HTMLButtonElement | null)[]>([]);
  const enabled = options.map((o, i) => (o.disabled ? -1 : i)).filter((i) => i >= 0);
  const move = (from: number, dir: 1 | -1 | 'home' | 'end') => {
    if (!enabled.length) return;
    const pos = enabled.indexOf(from);
    const next =
      dir === 'home' ? enabled[0] : dir === 'end' ? enabled[enabled.length - 1] : enabled[(pos + (dir as number) + enabled.length) % enabled.length];
    onChange(options[next].value);
    refs.current[next]?.focus();
  };
  const onKey = (e: React.KeyboardEvent, i: number) => {
    if (e.key === 'ArrowRight' || e.key === 'ArrowDown') { e.preventDefault(); move(i, 1); }
    else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') { e.preventDefault(); move(i, -1); }
    else if (e.key === 'Home') { e.preventDefault(); move(i, 'home'); }
    else if (e.key === 'End') { e.preventDefault(); move(i, 'end'); }
  };
  const activeIdx = Math.max(0, options.findIndex((o) => o.value === value));
  return (
    <div
      role="radiogroup"
      aria-label={label}
      data-ui="toolbar"
      className={clsx('inline-flex items-center gap-0.5 p-0.5 rounded-pill bg-[var(--surface)] border border-[var(--hairline)]', className)}
    >
      {options.map((o, i) => {
        const active = o.value === value;
        return (
          <button
            key={o.value}
            ref={(el) => {
              refs.current[i] = el;
            }}
            type="button"
            role="radio"
            aria-checked={active}
            tabIndex={i === activeIdx ? 0 : -1}
            onKeyDown={(e) => onKey(e, i)}
            disabled={o.disabled}
            title={o.title}
            onClick={() => !o.disabled && onChange(o.value)}
            className={clsx(
              'inline-flex items-center gap-1.5 rounded-pill font-medium transition-colors duration-fast',
              'focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-[var(--accent)]',
              size === 'sm' ? 'px-2.5 py-1 text-caption' : 'px-3.5 py-1.5 text-label',
              active
                ? 'bg-[var(--card)] text-[var(--ink)] shadow-[var(--card-shadow)]'
                : 'text-[var(--ink-2)] hover:text-[var(--ink)]',
              o.disabled && 'opacity-40 cursor-not-allowed',
            )}
          >
            {o.icon && <span className="shrink-0 [&>svg]:w-3.5 [&>svg]:h-3.5">{o.icon}</span>}
            {o.label}
          </button>
        );
      })}
    </div>
  );
}

/* ------------------------------------------------------------------ IconButton */

export interface IconButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  /** required accessible label */
  label: string;
  active?: boolean;
}

export const IconButton = React.forwardRef<HTMLButtonElement, IconButtonProps>(function IconButton(
  { label, active, className, children, type = 'button', ...rest },
  ref,
) {
  return (
    <button
      ref={ref}
      type={type}
      aria-label={label}
      title={label}
      data-ui="icon-button"
      className={clsx(
        'inline-grid place-items-center w-9 h-9 rounded-[var(--radius-md)] transition-colors duration-fast',
        'focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--accent)]',
        active ? 'bg-[var(--accent-pale)] text-[var(--accent-deep)] dark:text-[var(--accent-soft)]' : 'text-[var(--ink-2)] hover:bg-[var(--surface-2)] hover:text-[var(--ink)]',
        '[&>svg]:w-[1.1rem] [&>svg]:h-[1.1rem]',
        className,
      )}
      {...rest}
    >
      {children}
    </button>
  );
});
