import React from "react";
import type { ElderProfile, Profiles } from "../types";
import { User, Heart, Utensils } from "lucide-react";

interface Props {
  profiles: Profiles;
}

function Card({
  icon,
  title,
  accent,
  children,
}: {
  icon: React.ReactNode;
  title: string;
  accent: string;
  children: React.ReactNode;
}) {
  return (
    <div className={`profile-card ${accent}`}>
      <div className="profile-card-header">
        <span className="profile-card-icon">{icon}</span>
        <span className="profile-card-title">{title}</span>
      </div>
      <div className="profile-card-body">{children}</div>
    </div>
  );
}

function Row({ label, value }: { label: string; value?: string | null }) {
  if (!value) return null;
  return (
    <div className="profile-row">
      <span className="profile-label">{label}</span>
      <span className="profile-value">{value}</span>
    </div>
  );
}

/**
 * 「上次调药」是整个升级判断的锚点，卡片上必须看得见。
 * 后端把它放在 elder 顶层（旧版本曾放在 followups 里），两处都读一下。
 */
function medChangeLabel(elder: ElderProfile): string {
  const c = elder.last_med_change;
  if (c?.drug) {
    const delta = c.from && c.to ? ` ${c.from}→${c.to}` : "";
    return `${c.date ?? ""} ${c.drug}${delta}`.trim();
  }
  return elder.last_med_change_date ?? elder.followups?.last_med_change_date ?? "";
}

export function ProfileCards({ profiles }: Props) {
  const { employer, elder, caregiver } = profiles;

  return (
    <div className="profile-cards-container">
      {employer && (
        <Card icon={<User size={16} />} title="雇主" accent="accent-employer">
          <Row label="姓名" value={employer.name} />
          <Row label="关系" value={employer.relation} />
          <Row label="语言" value={employer.language} />
          {employer.work_schedule && (
            <div className="profile-note">{employer.work_schedule}</div>
          )}
          {employer.notes && (
            <div className="profile-note muted">{employer.notes}</div>
          )}
        </Card>
      )}

      {elder && (
        <Card icon={<Heart size={16} />} title="被照顾者" accent="accent-elder">
          <Row label="姓名" value={elder.name} />
          <Row label="年龄" value={elder.age ? `${elder.age} 岁` : undefined} />
          {elder.conditions?.length > 0 && (
            <div className="profile-row">
              <span className="profile-label">慢病</span>
              <span className="profile-value">
                {elder.conditions.join("、")}
              </span>
            </div>
          )}
          {elder.medications?.length > 0 && (
            <div className="profile-meds">
              <div className="profile-label">用药</div>
              {elder.medications.map((m, i) => (
                <div key={i} className="med-row">
                  <span className="med-name">{m.drug ?? m.name}</span>
                  <span className="med-timing">{m.timing} {m.time}</span>
                </div>
              ))}
            </div>
          )}
          {(elder.followups?.next_date || medChangeLabel(elder)) && (
            <div className="profile-note">
              {elder.followups?.next_date && <>复诊：{elder.followups.next_date}</>}
              {medChangeLabel(elder) && (
                <span className="med-change">
                  {elder.followups?.next_date ? " · " : ""}
                  上次调药：{medChangeLabel(elder)}
                </span>
              )}
            </div>
          )}
          {elder.baseline_notes && (
            <div className="profile-note muted">{elder.baseline_notes}</div>
          )}
        </Card>
      )}

      {caregiver && (
        <Card
          icon={<Utensils size={16} />}
          title="照护者"
          accent="accent-caregiver"
        >
          <Row label="姓名" value={caregiver.name} />
          <Row label="来自" value={caregiver.home_country} />
          <Row label="母语" value={caregiver.mother_tongue} />
          {caregiver.care_abilities && (
            <div className="profile-note">{caregiver.care_abilities}</div>
          )}
        </Card>
      )}
    </div>
  );
}
