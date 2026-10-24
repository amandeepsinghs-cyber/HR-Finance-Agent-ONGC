'use client';

import React, { useEffect, useState } from 'react';
import { PersonaType } from '@/contracts/answerContract';
import { UserCheck, X } from 'lucide-react';
import { personaInfo } from '@/personas';

interface PersonaBannerProps {
  persona: PersonaType;
}

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

  // P2H.2: label from the shared directory (server-signed persona; illustrative identity)
  const info = personaInfo(persona);
  const details = { name: info?.display_name, title: info?.designation || persona };

  return (
    <div
      role="status"
      data-testid="persona-banner"
      className="absolute left-1/2 -translate-x-1/2 top-[1rem] z-40 flex items-center gap-3 pl-3 pr-2 py-2 rounded-full bg-[var(--ink)] text-[var(--canvas)] shadow-[var(--panel-shadow)] text-[0.86rem] max-w-[90%]"
    >
      <UserCheck className="w-4 h-4 shrink-0 opacity-80" />
      <span className="font-medium truncate" title="Illustrative identity">
        Signed in as {details.name ? `${details.name} (${details.title})` : details.title}
      </span>
      <button onClick={() => setVisible(false)} className="p-1 rounded-full hover:bg-white/15 dark:hover:bg-black/10" aria-label="Dismiss">
        <X className="w-4 h-4" />
      </button>
    </div>
  );
};
