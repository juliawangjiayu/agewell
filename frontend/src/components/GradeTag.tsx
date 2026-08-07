import type { Grade } from "../types";

const GRADE_CONFIG: Record<
  Grade,
  { label: string; className: string; emoji: string }
> = {
  record: {
    label: "记录",
    className: "grade-record",
    emoji: "⚪",
  },
  routine: {
    label: "常规通报",
    className: "grade-routine",
    emoji: "🟡",
  },
  escalate: {
    label: "即时升级",
    className: "grade-escalate",
    emoji: "🔴",
  },
};

export function GradeTag({ grade }: { grade: Grade }) {
  const cfg = GRADE_CONFIG[grade] ?? GRADE_CONFIG.record;
  return (
    <span className={`grade-tag ${cfg.className}`}>
      {cfg.emoji} {cfg.label}
    </span>
  );
}
