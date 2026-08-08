import type { ChatMessage as ChatMessageType } from "../types";
import { HelperResultCard } from "./HelperResultCard";
import { EmployerResultCard } from "./EmployerResultCard";
import { Mic } from "lucide-react";
import { clsx } from "clsx";

interface Props {
  message: ChatMessageType;
}

const ROLE_LABEL: Record<string, string> = {
  helper: "Rosa",
  employer: "Rachel",
  bot: "Bot",
};

const ROLE_CLASS: Record<string, string> = {
  helper: "bubble-helper",
  employer: "bubble-employer",
  bot: "bubble-bot",
};

export function ChatMessageBubble({ message }: Props) {
  const { role, content, timestamp, result, isVoice, transcript } = message;
  const label = ROLE_LABEL[role] ?? role;
  const bubbleCls = ROLE_CLASS[role] ?? "bubble-bot";

  return (
    <div className={clsx("chat-message", `msg-${role}`)}>
      <div className="msg-meta">
        <span className={clsx("msg-avatar", `avatar-${role}`)}>{label[0]}</span>
        <span className="msg-name">{label}</span>
        <span className="msg-time">
          {timestamp.toLocaleTimeString("zh-CN", {
            hour: "2-digit",
            minute: "2-digit",
          })}
        </span>
      </div>

      <div className={clsx("msg-bubble", bubbleCls)}>
        {isVoice && (
          <span className="voice-badge">
            <Mic size={12} /> 语音
          </span>
        )}
        {transcript && transcript !== content && (
          <div className="transcript-text">
            <span className="transcript-label">原话：</span>{transcript}
          </div>
        )}
        <p className="bubble-text">{content}</p>
      </div>

      {/* Structured result */}
      {result && (
        <div className="msg-result">
          {result.type === "helper" && <HelperResultCard result={result} />}
          {result.type === "employer" && <EmployerResultCard result={result} />}
        </div>
      )}
    </div>
  );
}
