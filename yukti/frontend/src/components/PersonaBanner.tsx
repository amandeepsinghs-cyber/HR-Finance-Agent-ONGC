'use client';

import React, { useEffect, useState } from 'react';
import { PersonaType } from '@/contracts/answerContract';
import { UserCheck, X } from 'lucide-react';

interface PersonaBannerProps {
  persona: PersonaType;
}

const PERSONA_DETAILS: Record<
  PersonaType,
  { name?: string; title: string; clearance: string }
> = {
  CMD: {
    name: 'Arun',
    title: 'Chairman & CEO (CMD)',
    clearance: 'Full Enterprise Clearance: All Board, Operational, Financial & Confidential HR Records.',
  },
  DIR_HR: {
    title: 'Director (HR)',
    clearance: 'Directorate Clearance: All Corporate & Field HR records, draft transfers, and finance aggregates.',
  },
  DIR_FIN: {
    title: 'Director (Finance)',
    clearance: 'Directorate Clearance: Full enterprise financial records, field P&Ls, and HR manpower summaries.',
  },
  E2_HR: {
    name: 'Pooja Verma',
    title: 'E2, HR',
    clearance: 'Officer Clearance: Personal records, published policy manuals, and authorized aggregate data.',
  },
  E3_FIN: {
    name: 'Rajesh Kulkarni',
    title: 'E3, Finance',
    clearance: 'Officer Clearance: Assigned ledger books, published policy, and authorized expenditure aggregates.',
  },
};

export const PersonaBanner: React.FC<PersonaBannerProps> = ({ persona }) => {
  const [visible, setVisible] = useState(false);
  const [prevPersona, setPrevPersona] = useState<PersonaType>(persona);

  useEffect(() => {
    if (persona !== prevPersona) {
      setPrevPersona(persona);
      setVisible(true);
      const timer = setTimeout(() => {
        setVisible(false);
      }, 5000);
      return () => clearTimeout(timer);
    }
  }, [persona, prevPersona]);

  if (!visible) return null;

  const details = PERSONA_DETAILS[persona];

  return (
    <div
      role="status"
      data-testid="persona-banner"
      className="absolute left-1/2 -translate-x-1/2 top-[1rem] z-40 flex items-center gap-3 pl-3 pr-2 py-2 rounded-full bg-[var(--ink)] text-[var(--canvas)] shadow-[var(--panel-shadow)] text-[0.86rem] max-w-[90%]"
    >
      <UserCheck className="w-4 h-4 shrink-0 opacity-80" />
      <span className="font-medium truncate">
        Now speaking as {details.name ? `${details.name} (${details.title})` : details.title}
      </span>
      <button onClick={() => setVisible(false)} className="p-1 rounded-full hover:bg-white/15 dark:hover:bg-black/10" aria-label="Dismiss">
        <X className="w-4 h-4" />
      </button>
    </div>
  );
};
