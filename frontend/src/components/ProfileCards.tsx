import React from "react";
import type { Profiles } from "../types";
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
                  <span className="med-name">{m.name}</span>
                  <span className="med-timing">{m.timing} {m.time}</span>
                </div>
              ))}
            </div>
          )}
          {elder.followups?.next_date && (
            <div className="profile-note">
              复诊：{elder.followups.next_date}
              {elder.followups.last_med_change_date && (
                <span className="med-change">
                  {" "}· 上次调药：{elder.followups.last_med_change_date}
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
