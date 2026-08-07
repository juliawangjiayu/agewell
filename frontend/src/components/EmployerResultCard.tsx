import { useState } from "react";
import type { EmployerResult, Task } from "../types";
import { CheckSquare, Square, Clock } from "lucide-react";

interface Props {
  result: EmployerResult;
  onConfirmTask?: (index: number, confirmed: boolean) => void;
}

export function EmployerResultCard({ result, onConfirmTask }: Props) {
  const { skill_on, understood, tasks, helper_message } = result;
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
