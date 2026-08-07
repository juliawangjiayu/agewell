// ─── Profile types ────────────────────────────────────────────────────────────

export interface Medication {
  /** 后端规范字段；onboard 表单历史上发的是 name/notes，两者都容忍 */
  drug?: string;
  name?: string;
  timing: string;
  time: string;
  note?: string;
  notes?: string;
}

export interface Followup {
  clinic?: string;
  interval?: string;
  next_date?: string;
  last_med_change_date?: string;
}

/** 最近一次调药：必须说明是哪一个药、怎么调的，否则医生端会把整张用药表都列出来 */
export interface MedChange {
  drug?: string;
  from?: string;
  to?: string;
  date?: string;
}

export interface ElderProfile {
  name: string;
  age?: number;
  conditions: string[];
  baseline_notes?: string;
  medications: Medication[];
  followups: Followup;
  last_med_change?: MedChange;
  last_med_change_date?: string;
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
  family?: string | null;
  doctor?: string | null;
  helper?: string | null;
  /** 给老人的一句话——系统把事情说出去时，她是知情的 */
  elder?: string | null;
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
  /** 0–2 条；只在答案会改变分级、且女佣当场答得上来时才问 */
  clarifying_questions?: string[];
  outputs: HelperOutputs;
}

export interface Task {
  time?: string | null;
  /** 提前量：该在什么时候动手，对应「6点炒菜就5点告诉她」 */
  tell_by?: string | null;
  item: string;
  detail?: string;
  confirmed: boolean;
}

/** 指令与用药表冲突：雇主说错了，系统当场接住并回问 */
export interface Conflict {
  instruction?: string;
  fact?: string;
  question?: string;
}

export interface EmployerResult {
  type: "employer";
  skill_on: boolean;
  raw_instruction: string;
  understood: string;
  conflicts?: Conflict[];
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
