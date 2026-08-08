import type { HelperResult } from "../types";
import { GradeTag } from "./GradeTag";
import {
  Users,
  Stethoscope,
  MessageCircle,
  Ear,
  HelpCircle,
  ClipboardCheck,
} from "lucide-react";

interface Props {
  result: HelperResult;
}

const NOTIFY_LABEL: Record<string, string> = {
  family: "家人",
  doctor: "医生",
};

export function HelperResultCard({ result }: Props) {
  const {
    skill_on,
    restored_text,
    grade,
    notify,
    reason,
    clarifying_questions,
    task_confirmations,
    outputs,
  } = result;

  if (!skill_on) {
    // Baseline mode: 后端把裸模型的回复放在 outputs.helper，不是 outputs.raw。
    // 只读 raw 会导致对比模式下整张卡片空白——而对比模式正是我们的论据。
    return (
      <div className="result-card result-baseline">
        <div className="result-baseline-label">通用助手回应（未载入 skill）</div>
        <p className="result-raw">
          {outputs.raw ?? outputs.helper ?? restored_text}
        </p>
      </div>
    );
  }

  return (
    <div className="result-card result-helper">
      {/* Header row */}
      <div className="result-header">
        <GradeTag grade={grade} />
        {notify?.length > 0 && (
          <span className="notify-chips">
            通知：{notify.map((n) => NOTIFY_LABEL[n] ?? n).join(" + ")}
          </span>
        )}
      </div>

      {/* Restored text */}
      <div className="result-section">
        <div className="result-section-label">语义还原</div>
        <p className="result-text restored">{restored_text}</p>
      </div>

      {/* 任务回执 —— 雇主交代的事，这里被确认落地了 */}
      {task_confirmations && task_confirmations.length > 0 && (
        <div className="result-section taskconfirm-section">
          <div className="result-section-label">
            <ClipboardCheck size={13} /> 任务回执
          </div>
          {task_confirmations.map((t, i) => (
            <p key={i} className="result-text taskconfirm-item">
              {t}
            </p>
          ))}
        </div>
      )}

      {/* Reason */}
      <div className="result-section">
        <div className="result-section-label">为什么</div>
        <p className="result-text reason">{reason}</p>
      </div>

      {/* Clarifying questions — 提问真的会改变分级，所以要显眼 */}
      {clarifying_questions && clarifying_questions.length > 0 && (
        <div className="result-section clarify-section">
          <div className="result-section-label">
            <HelpCircle size={13} /> 需要确认
          </div>
          {clarifying_questions.map((q, i) => (
            <p key={i} className="result-text clarify-q">
              {q}
            </p>
          ))}
        </div>
      )}

      {/* Outputs */}
      <div className="result-outputs">
        {outputs.family && (
          <div className="output-block output-family">
            <div className="output-label">
              <Users size={13} /> 给家人（丽珍）
            </div>
            <p>{outputs.family}</p>
          </div>
        )}
        {outputs.doctor && (
          <div className="output-block output-doctor">
            <div className="output-label">
              <Stethoscope size={13} /> 给医生
            </div>
            <p>{outputs.doctor}</p>
          </div>
        )}
        {outputs.helper && (
          <div className="output-block output-helper">
            <div className="output-label">
              <MessageCircle size={13} /> 给 Rosa
            </div>
            <p>{outputs.helper}</p>
          </div>
        )}
        {outputs.elder && (
          <div className="output-block output-elder">
            <div className="output-label">
              <Ear size={13} /> 给 Ah Ma（语音告知）
            </div>
            <p>{outputs.elder}</p>
          </div>
        )}
      </div>
    </div>
  );
}
