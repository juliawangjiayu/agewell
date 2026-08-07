import { useState } from "react";
import type { EmployerResult, Task } from "../types";
import { CheckSquare, Square, Clock, AlertTriangle } from "lucide-react";

interface Props {
  result: EmployerResult;
  onConfirmTask?: (index: number, confirmed: boolean) => void;
}

export function EmployerResultCard({ result, onConfirmTask }: Props) {
  const { skill_on, understood, conflicts, tasks, helper_message } = result;
  const [localTasks, setLocalTasks] = useState<Task[]>(
    tasks.map((t) => ({ ...t, confirmed: false }))
  );

  if (!skill_on) {
    return (
      <div className="result-card result-baseline">
        <div className="result-baseline-label">通用助手回应（未载入 skill）</div>
        <p className="result-raw">{helper_message}</p>
      </div>
    );
  }

  const toggle = (idx: number) => {
    setLocalTasks((prev) =>
      prev.map((t, i) =>
        i === idx ? { ...t, confirmed: !t.confirmed } : t
      )
    );
    onConfirmTask?.(idx, !localTasks[idx].confirmed);
  };

  const allConfirmed = localTasks.every((t) => t.confirmed);

  return (
    <div className="result-card result-employer">
      {/* Understood */}
      <div className="result-section">
        <div className="result-section-label">语义理解</div>
        <p className="result-text">{understood}</p>
      </div>

      {/* 指令与用药表冲突 —— 系统当场接住，而不是让女佣照着做 */}
      {conflicts && conflicts.length > 0 && (
        <div className="result-section conflict-section">
          <div className="result-section-label">
            <AlertTriangle size={13} /> 指令与用药表不一致
          </div>
          {conflicts.map((c, i) => (
            <div key={i} className="conflict-item">
              {c.instruction && (
                <div className="conflict-said">雇主说：{c.instruction}</div>
              )}
              {c.fact && <div className="conflict-fact">{c.fact}</div>}
              {c.question && <div className="conflict-q">→ {c.question}</div>}
            </div>
          ))}
        </div>
      )}

      {/* Task list */}
      <div className="result-section">
        <div className="result-section-label">
          任务清单（Rosa 逐项确认）
        </div>
        <ul className="task-list">
          {localTasks.map((task, idx) => (
            <li
              key={idx}
              className={`task-item ${task.confirmed ? "confirmed" : ""}`}
              onClick={() => toggle(idx)}
            >
              <span className="task-check">
                {task.confirmed ? (
                  <CheckSquare size={16} className="check-icon checked" />
                ) : (
                  <Square size={16} className="check-icon" />
                )}
              </span>
              <span className="task-content">
                {task.time && (
                  <span className="task-time">
                    <Clock size={12} /> {task.time}
                  </span>
                )}
                {task.tell_by && (
                  <span className="task-tellby" title="提前量：该什么时候动手">
                    提前 {task.tell_by}
                  </span>
                )}
                <span className="task-item-text">{task.item}</span>
                {task.detail && (
                  <span className="task-detail"> — {task.detail}</span>
                )}
              </span>
            </li>
          ))}
        </ul>
        {allConfirmed && (
          <div className="all-confirmed-banner">
            ✓ Rosa 已确认所有任务
          </div>
        )}
      </div>

      {/* Helper message */}
      {helper_message && (
        <div className="result-section">
          <div className="result-section-label">发给 Rosa 的消息</div>
          <p className="result-text helper-msg">{helper_message}</p>
        </div>
      )}
    </div>
  );
}
