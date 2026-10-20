'use client';

import React, { useEffect, useState } from 'react';
import { PersonaType } from '@/contracts/answerContract';
import { ShieldCheck, UserCheck, X } from 'lucide-react';

interface PersonaBannerProps {
  persona: PersonaType;
}

const PERSONA_DETAILS: Record<
  PersonaType,
  { name?: string; title: string; clearance: string }
> = {
  CMD: {
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
    title: 'Assistant Manager (E2 · HR)',
    clearance: 'Officer Clearance: Personal records, published policy manuals, and authorized aggregate data.',
  },
  E3_FIN: {
    name: 'Rajesh Kulkarni',
    title: 'Deputy Manager (E3 · Finance)',
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
    <div className="w-full bg-gradient-to-r from-blue-600 via-indigo-600 to-blue-700 text-white px-6 py-2.5 flex items-center justify-between shadow-md text-xs md:text-sm animate-in slide-in-from-top-2 duration-200 z-20">
      <div className="flex items-center gap-3">
        <div className="p-1 rounded-lg bg-white/20">
          <UserCheck className="w-4 h-4 text-white" />
        </div>
        <div>
          <span className="font-bold text-white">
            Now speaking as {details.name ? `${details.name} (${details.title})` : details.title}
          </span>
          <span className="opacity-90 ml-2 hidden sm:inline">— {details.clearance}</span>
        </div>
      </div>
      <button
        onClick={() => setVisible(false)}
        className="p-1 rounded-md hover:bg-white/20 transition-colors text-white/80 hover:text-white"
      >
        <X className="w-4 h-4" />
      </button>
    </div>
  );
};
