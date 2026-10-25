/**
 * Persona directory for the UI (P2H.2; D-41 eleven personas, D-60 identities; D-66 real leadership names).
 *
 * The SERVER is the source of truth: the picker loads `/api/auth/personas` and the banner reads `/api/auth/me`.
 * This static mirror of `backend/app/brain/app_users.yaml` is only a fallback for labels when the directory has not
 * loaded yet (and for tests). Leadership names are the actual ONGC office-holders; their HR records in the
 * data bank are synthetic and labelled as such. E1–E4 identities are synthetic/illustrative.
 */
import type { PersonaType } from '@/contracts/answerContract';

export type PersonaGroup = 'Leadership' | 'HR' | 'Finance';

export interface PersonaInfo {
  id: PersonaType;
  /** short chip label, e.g. "E2 · HR" */
  short: string;
  display_name: string;
  designation: string;
  group: PersonaGroup;
  tier: 'cmd' | 'director' | 'junior';
  /** how Yukti addresses the user in the greeting */
  address: string;
}

export const PERSONA_DIRECTORY: PersonaInfo[] = [
  // Leadership = actual ONGC office-holders (ongcindia.com Board of Directors, retrieved 25-Oct-2026; D-66).
  { id: 'CMD', short: 'CMD', display_name: 'Arun Kumar Singh', designation: 'Chairman & CEO', group: 'Leadership', tier: 'cmd', address: 'Mr. Singh' },
  { id: 'DIR_HR', short: 'Director HR', display_name: 'Manish Patil', designation: 'Director (Human Resources)', group: 'Leadership', tier: 'director', address: 'Mr. Patil' },
  { id: 'DIR_FIN', short: 'Director Finance', display_name: 'Anupam Agarwal', designation: 'Director (Finance)', group: 'Leadership', tier: 'director', address: 'Mr. Agarwal' },
  // E1–E4 = synthetic employees; names must equal the Employee-360 record for the same emp_id.
  { id: 'E1_HR', short: 'E1 · HR', display_name: 'Dinesh Deshmukh', designation: 'HR Officer (E1)', group: 'HR', tier: 'junior', address: 'Dinesh' },
  { id: 'E2_HR', short: 'E2 · HR', display_name: 'Pooja Verma', designation: 'HR Executive (E2)', group: 'HR', tier: 'junior', address: 'Pooja' },
  { id: 'E3_HR', short: 'E3 · HR', display_name: 'Lokesh Verma', designation: 'Senior HR Executive (E3)', group: 'HR', tier: 'junior', address: 'Lokesh' },
  { id: 'E4_HR', short: 'E4 · HR', display_name: 'Umesh D. Bhatia', designation: 'Dy. Manager HR (E4)', group: 'HR', tier: 'junior', address: 'Umesh' },
  { id: 'E1_FIN', short: 'E1 · Finance', display_name: 'Ajay Deshmukh', designation: 'Accounts Officer (E1)', group: 'Finance', tier: 'junior', address: 'Ajay' },
  { id: 'E2_FIN', short: 'E2 · Finance', display_name: 'Praveen Nair', designation: 'Finance Executive (E2)', group: 'Finance', tier: 'junior', address: 'Praveen' },
  { id: 'E3_FIN', short: 'E3 · Finance', display_name: 'Shailesh E. Kapoor', designation: 'Finance Officer (E3)', group: 'Finance', tier: 'junior', address: 'Shailesh' },
  { id: 'E4_FIN', short: 'E4 · Finance', display_name: 'Santosh Banerjee', designation: 'Dy. Manager Finance (E4)', group: 'Finance', tier: 'junior', address: 'Santosh' },
];

export const PERSONA_IDS = PERSONA_DIRECTORY.map((p) => p.id);

export function personaInfo(id?: string | null): PersonaInfo | undefined {
  return PERSONA_DIRECTORY.find((p) => p.id === id);
}

export function isJunior(id?: string | null): boolean {
  return personaInfo(id)?.tier === 'junior';
}

/** Rank used for row-action gating (unknown → 0, never defaults to CMD). */
export function personaRank(id?: string | null): number {
  const t = personaInfo(id)?.tier;
  return t === 'cmd' ? 3 : t === 'director' ? 2 : t === 'junior' ? 1 : 0;
}

/** Shape returned by GET /api/auth/personas (P2H.1 backend). */
export interface PublicPersona {
  id: string;
  persona_id: string;
  display_name: string;
  designation: string;
  functional_designation?: string;
  function?: string;
  grade?: string;
  work_centre?: string;
}

/** Question text of a refusal alternative (object or legacy string). */
export function altQuestion(a: { question?: string } | string | null | undefined): string | undefined {
  if (!a) return undefined;
  return typeof a === 'string' ? a : a.question || undefined;
}
