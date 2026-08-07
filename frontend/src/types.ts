// ─── Profile types ────────────────────────────────────────────────────────────

export interface Medication {
  name: string;
  timing: string;
  time: string;
  notes?: string;
}

export interface Followup {
  clinic?: string;
  interval?: string;
  next_date?: string;
  last_med_change_date?: string;
}

export interface ElderProfile {
  name: string;
  age?: number;
  conditions: string[];
  baseline_notes?: string;
  medications: Medication[];
  followups: Followup;
}

export interface EmployerProfile {
  name: string;
  language: string;
  relation?: string;
  work_schedule?: string;
  notes?: string;
}

export interface CaregiverProfile {
  name: string;
  home_country?: string;
  mother_tongue?: string;
  care_abilities?: string;
}

export interface Profiles {
  employer?: EmployerProfile;
  elder?: ElderProfile;
  caregiver?: CaregiverProfile;
  recent_observations?: Observation[];
}

// ─── Message / Observation types ─────────────────────────────────────────────

export type Grade = "record" | "routine" | "escalate";
export type Role = "helper" | "employer";

export interface HelperOutputs {
  family?: string;
  doctor?: string;
  helper?: string;
  raw?: string; // skill_on=false: plain response
}

export interface HelperResult {
  type: "helper";
  skill_on: boolean;
  raw_text: string;
  restored_text: string;
  grade: Grade;
  notify: string[];
  reason: string;
  outputs: HelperOutputs;
}

export interface Task {
  time?: string | null;
  item: string;
  detail?: string;
  confirmed: boolean;
}

export interface EmployerResult {
  type: "employer";
  skill_on: boolean;
  raw_instruction: string;
  understood: string;
  tasks: Task[];
  helper_message: string;
  confirmation_items: string[];
}

export type ApiResult = HelperResult | EmployerResult;

export interface Observation {
  id?: number;
  date?: string;
  raw_text: string;
  restored_text?: string;
  grade?: Grade;
  notify?: string[];
  reason?: string;
  created_at?: string;
}

// ─── Chat message (UI level) ──────────────────────────────────────────────────

export interface ChatMessage {
  id: string;
  role: Role | "bot";
  content: string; // display text
  timestamp: Date;
  result?: ApiResult; // structured result from API
  isVoice?: boolean;
  transcript?: string;
}

// ─── Onboard form ─────────────────────────────────────────────────────────────

export interface OnboardForm {
  elder: ElderProfile;
  employer: EmployerProfile;
  caregiver: CaregiverProfile;
}
