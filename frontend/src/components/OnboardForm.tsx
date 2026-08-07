import { useState } from "react";
import type { OnboardForm } from "../types";

interface Props {
  onSubmit: (form: OnboardForm) => Promise<void>;
  loading: boolean;
}

const DEFAULT_FORM: OnboardForm = {
  employer: {
    name: "丽珍",
    language: "中文",
    relation: "女儿",
    work_schedule: "与 Ah Ma 不同住。工作日各自生活；一般周五晚接 Ah Ma 吃饭，周六、周日一起吃午晚饭。",
    notes: "主要照护决策者，每周只有周五晚到周日在场；工作日老人身边只有 Rosa。",
  },
  elder: {
    name: "Ah Ma",
    age: 82,
    conditions: ["高血压", "2型糖尿病"],
    baseline_notes: "独住 HDB，与 Rosa 同住；平时三餐正常，能自己走动，晚饭后爱看电视。",
    medications: [
      { name: "Amlodipine（氨氯地平）", timing: "早饭后", time: "08:00", notes: "降压" },
      { name: "Metformin（二甲双胍）", timing: "早、晚饭后", time: "08:00 / 19:00", notes: "降糖" },
      { name: "Losartan（氯沙坦）", timing: "早饭后", time: "08:00", notes: "降压" },
    ],
    followups: {
      clinic: "XX Polyclinic",
      interval: "每 3 个月",
      next_date: "本周五",
      last_med_change_date: "本周三（Day3）",
    },
  },
  caregiver: {
    name: "Rosa",
    home_country: "菲律宾",
    mother_tongue: "Tagalog（日常英菲混说）",
    care_abilities: "照顾过长辈、会量血压、会做简单中餐/家常菜",
  },
};

export function OnboardFormPanel({ onSubmit, loading }: Props) {
  const [form, setForm] = useState<OnboardForm>(DEFAULT_FORM);
  const [step, setStep] = useState<"employer" | "elder" | "caregiver" | "done">("employer");

  const setField = (
    profile: keyof OnboardForm,
    field: string,
    value: unknown
  ) => {
    setForm((prev) => ({
      ...prev,
      [profile]: { ...prev[profile], [field]: value },
    }));
  };

  const handleSubmit = async () => {
    await onSubmit(form);
  };

  return (
    <div className="onboard-container">
      <h2 className="onboard-title">建立家庭档案</h2>
      <p className="onboard-subtitle">
        填写三份基础信息，建立判断层所需的家庭上下文库。
      </p>

      {/* Step tabs */}
      <div className="onboard-tabs">
        {(["employer", "elder", "caregiver"] as const).map((s) => (
          <button
            key={s}
            className={`onboard-tab ${step === s ? "active" : ""}`}
            onClick={() => setStep(s)}
          >
            {s === "employer" ? "雇主" : s === "elder" ? "被照顾者" : "照护者（Rosa）"}
          </button>
        ))}
      </div>

      {/* Employer */}
      {step === "employer" && (
        <div className="onboard-section">
          <div className="form-group">
            <label>您的称呼</label>
            <input
              value={form.employer.name}
              onChange={(e) => setField("employer", "name", e.target.value)}
            />
          </div>
          <div className="form-group">
            <label>与老人的关系</label>
            <input
              value={form.employer.relation ?? ""}
              onChange={(e) => setField("employer", "relation", e.target.value)}
            />
          </div>
          <div className="form-group">
            <label>在场规律（您几天能见到老人一次？）</label>
            <textarea
              rows={3}
              value={form.employer.work_schedule ?? ""}
              onChange={(e) =>
                setField("employer", "work_schedule", e.target.value)
              }
            />
          </div>
          <div className="form-group">
            <label>补充说明</label>
            <textarea
              rows={2}
              value={form.employer.notes ?? ""}
              onChange={(e) => setField("employer", "notes", e.target.value)}
            />
          </div>
          <button className="btn-primary" onClick={() => setStep("elder")}>
            下一步 →
          </button>
        </div>
      )}

      {/* Elder */}
      {step === "elder" && (
        <div className="onboard-section">
          <div className="form-row">
            <div className="form-group">
              <label>老人姓名</label>
              <input
                value={form.elder.name}
                onChange={(e) => setField("elder", "name", e.target.value)}
              />
            </div>
            <div className="form-group">
              <label>年龄</label>
              <input
                type="number"
                value={form.elder.age ?? ""}
                onChange={(e) =>
                  setField("elder", "age", Number(e.target.value) || undefined)
                }
              />
            </div>
          </div>
          <div className="form-group">
            <label>慢性病（逗号分隔）</label>
            <input
              value={form.elder.conditions.join("、")}
              onChange={(e) =>
                setField(
                  "elder",
                  "conditions",
                  e.target.value.split(/[,，、]+/).map((s) => s.trim()).filter(Boolean)
                )
              }
            />
          </div>
          <div className="form-group">
            <label>日常状态备注</label>
            <textarea
              rows={2}
              value={form.elder.baseline_notes ?? ""}
              onChange={(e) =>
                setField("elder", "baseline_notes", e.target.value)
              }
            />
          </div>
          <div className="form-group">
            <label>下次复诊</label>
            <input
              value={form.elder.followups.next_date ?? ""}
              onChange={(e) =>
                setField("elder", "followups", {
                  ...form.elder.followups,
                  next_date: e.target.value,
                })
              }
              placeholder="例：本周五 / 2026-08-09"
            />
          </div>
          <div className="form-group">
            <label>最近调药日期（如有）</label>
            <input
              value={form.elder.followups.last_med_change_date ?? ""}
              onChange={(e) =>
                setField("elder", "followups", {
                  ...form.elder.followups,
                  last_med_change_date: e.target.value,
                })
              }
              placeholder="例：本周三"
            />
          </div>
          <div className="onboard-btn-row">
            <button className="btn-secondary" onClick={() => setStep("employer")}>
              ← 返回
            </button>
            <button className="btn-primary" onClick={() => setStep("caregiver")}>
              下一步 →
            </button>
          </div>
        </div>
      )}

      {/* Caregiver */}
      {step === "caregiver" && (
        <div className="onboard-section">
          <p className="onboard-helper-intro">
            帮 Rosa 把这份工作做顺 —— 只需简单聊几句。
          </p>
          <div className="form-group">
            <label>照护者的名字</label>
            <input
              value={form.caregiver.name}
              onChange={(e) => setField("caregiver", "name", e.target.value)}
            />
          </div>
          <div className="form-group">
            <label>来自哪里？</label>
            <input
              value={form.caregiver.home_country ?? ""}
              onChange={(e) =>
                setField("caregiver", "home_country", e.target.value)
              }
            />
          </div>
          <div className="form-group">
            <label>平时说什么语言？</label>
            <input
              value={form.caregiver.mother_tongue ?? ""}
              onChange={(e) =>
                setField("caregiver", "mother_tongue", e.target.value)
              }
            />
          </div>
          <div className="form-group">
            <label>以前照顾过长辈吗？会量血压、帮忙翻身、做家常菜？</label>
            <textarea
              rows={3}
              value={form.caregiver.care_abilities ?? ""}
              onChange={(e) =>
                setField("caregiver", "care_abilities", e.target.value)
              }
              placeholder="例：照顾过长辈、会量血压、会做简单家常菜"
            />
          </div>
          <div className="onboard-btn-row">
            <button className="btn-secondary" onClick={() => setStep("elder")}>
              ← 返回
            </button>
            <button
              className="btn-primary"
              onClick={handleSubmit}
              disabled={loading}
            >
              {loading ? "建立中…" : "建立家庭档案 →"}
            </button>
          </div>
        </div>
      )}

      {/* Quick-fill notice */}
      <div className="onboard-prefill-notice">
        已用 Ah Ma 家庭示例数据预填，可直接提交体验，也可修改为真实信息。
      </div>
    </div>
  );
}
