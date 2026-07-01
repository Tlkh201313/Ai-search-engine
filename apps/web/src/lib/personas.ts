import { Globe, Moon, Sun, Wind, type LucideIcon } from 'lucide-react';

import type { Persona } from './types';

export interface PersonaMeta {
  key: Persona;
  name: string;
  tagline: string;
  icon: LucideIcon;
}

export const PERSONAS: PersonaMeta[] = [
  { key: 'solstice', name: 'Solstice', tagline: 'Deepest reasoning & verification', icon: Sun },
  { key: 'lunar', name: 'Lunar', tagline: 'Balanced, reliable, fast enough', icon: Moon },
  { key: 'tellus', name: 'Tellus', tagline: 'Practical and grounded', icon: Globe },
  { key: 'zephyr', name: 'Zephyr', tagline: 'Fast dual-model fusion', icon: Wind },
];

export const PERSONA_MAP: Record<Persona, PersonaMeta> = PERSONAS.reduce(
  (acc, p) => ({ ...acc, [p.key]: p }),
  {} as Record<Persona, PersonaMeta>,
);

export const DEFAULT_PERSONA: Persona = 'lunar';
