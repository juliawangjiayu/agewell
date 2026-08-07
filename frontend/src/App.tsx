import { useState, useEffect, useRef, useCallback } from "react";
import { clsx } from "clsx";
import { RefreshCw, ToggleLeft, ToggleRight, Send } from "lucide-react";
import type {
  ChatMessage,
  Profiles,
  Role,
  ApiResult,
  OnboardForm,
} from "./types";
import { api } from "./api";
import { ProfileCards } from "./components/ProfileCards";
import { ChatMessageBubble } from "./components/ChatMessage";
import { VoiceButton } from "./components/VoiceButton";
import { OnboardFormPanel } from "./components/OnboardForm";

// ─── Seed family slug ─────────────────────────────────────────────────────────
const SEED_SLUG = "ah-ma";

// ─── Helper: unique id ────────────────────────────────────────────────────────
let _id = 0;
const uid = () => String(++_id);

export default function App() {
  // ── State ──────────────────────────────────────────────────────────────────
  const [slug] = useState<string>(SEED_SLUG);
  const [profiles, setProfiles] = useState<Profiles>({});
  const [hasFamily, setHasFamily] = useState(false);
  const [showOnboard, setShowOnboard] = useState(false);

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [role, setRole] = useState<Role>("helper");
  const [skillOn, setSkillOn] = useState(true);
  const [loading, setLoading] = useState(false);
  const [onboarding, setOnboarding] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const bottomRef = useRef<HTMLDivElement>(null);

  // ── Load profiles on mount ─────────────────────────────────────────────────
  const loadProfiles = useCallback(async (s: string) => {
    try {
      const data = await api.profiles(s);
      setProfiles(data);
      setHasFamily(true);
      setShowOnboard(false);
    } catch {
      setHasFamily(false);
      setShowOnboard(true);
    }
  }, []);

  useEffect(() => {
    loadProfiles(slug);
  }, [slug, loadProfiles]);

  // ── Auto-scroll ────────────────────────────────────────────────────────────
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // ── Onboard submit ─────────────────────────────────────────────────────────
  const handleOnboard = async (form: OnboardForm) => {
    setOnboarding(true);
    setError(null);
    try {
      await api.onboard(slug, form);
      await loadProfiles(slug);
      // Add welcome message
      setMessages([
        {
          id: uid(),
          role: "bot",
          content: `家庭档案已建立 ✓  欢迎，${form.employer.name}。\n切换身份（雇主 / 照护者），开始发言或语音输入。`,
          timestamp: new Date(),
        },
      ]);
    } catch (e) {
      setError(e instanceof Error ? e.message : "建立档案失败");
    } finally {
      setOnboarding(false);
    }
  };

  // ── Send text message ──────────────────────────────────────────────────────
  const handleSend = async () => {
    const text = input.trim();
    if (!text || loading) return;
    setInput("");
    setError(null);

    // Add user message
    const userMsg: ChatMessage = {
      id: uid(),
      role,
      content: text,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setLoading(true);

    try {
      const result: ApiResult = await api.message(slug, text, skillOn, role);
      const botMsg = buildBotMessage(result, role);
      setMessages((prev) => [...prev, botMsg]);
    } catch (e) {
      setError(e instanceof Error ? e.message : "发送失败");
    } finally {
      setLoading(false);
    }
  };

  // ── Send audio ─────────────────────────────────────────────────────────────
  const handleAudio = async (blob: Blob) => {
    if (loading) return;
    setError(null);

    const userMsg: ChatMessage = {
      id: uid(),
      role,
      content: "（语音录制中…）",
      timestamp: new Date(),
      isVoice: true,
    };
    setMessages((prev) => [...prev, userMsg]);
    setLoading(true);

    try {
      const result = await api.audio(slug, blob, skillOn, role);
      const transcript = result.transcript ?? "";

      // Update user message with transcript
      setMessages((prev) =>
        prev.map((m) =>
          m.id === userMsg.id
            ? { ...m, content: transcript || "（语音）", transcript }
            : m
        )
      );

      const botMsg = buildBotMessage(result, role);
      setMessages((prev) => [...prev, botMsg]);
    } catch (e) {
      setError(e instanceof Error ? e.message : "语音处理失败");
      setMessages((prev) => prev.filter((m) => m.id !== userMsg.id));
    } finally {
      setLoading(false);
    }
  };

  // ── Reset ──────────────────────────────────────────────────────────────────
  const handleReset = async () => {
    if (!confirm("重置会把示例家庭恢复到种子状态（清除本次产生的观察记录）。确认？"))
      return;
    setError(null);
    try {
      await api.reset(slug);
      await loadProfiles(slug);
      setMessages([
        {
          id: uid(),
          role: "bot",
          content: "已重置到种子状态 ✓ — Ah Ma 家庭上下文已恢复。",
          timestamp: new Date(),
        },
      ]);
    } catch (e) {
      setError(e instanceof Error ? e.message : "重置失败");
    }
  };

  // ── Keyboard send ──────────────────────────────────────────────────────────
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // ── Render ─────────────────────────────────────────────────────────────────
  return (
    <div className="app-root">
      {/* ── Top bar ── */}
      <header className="topbar">
        <div className="topbar-left">
          <span className="logo">AgeWell 照护协同</span>
          <span className="topbar-tagline">判断层 Demo</span>
        </div>

        <div className="topbar-center">
          {/* Skill toggle */}
          <button
            className={clsx("skill-toggle", skillOn ? "skill-on" : "skill-off")}
            onClick={() => setSkillOn((v) => !v)}
            title={skillOn ? "点击关闭 skill（切换到通用助手）" : "点击载入 skill"}
          >
            {skillOn ? (
              <>
                <ToggleRight size={18} /> 载入 skill
              </>
            ) : (
              <>
                <ToggleLeft size={18} /> 通用助手（对比模式）
              </>
            )}
          </button>
        </div>

        <div className="topbar-right">
          {/* Role switcher */}
          <div className="role-switcher">
            <button
              className={clsx("role-btn", role === "helper" && "active")}
              onClick={() => setRole("helper")}
            >
              Rosa（照护者）
            </button>
            <button
              className={clsx("role-btn", role === "employer" && "active")}
              onClick={() => setRole("employer")}
            >
              丽珍（雇主）
            </button>
          </div>

          {/* Reset */}
          {hasFamily && (
            <button className="reset-btn" onClick={handleReset} title="重置到种子状态">
              <RefreshCw size={15} /> 重置
            </button>
          )}

          {/* Onboard another family */}
          <button
            className="btn-ghost"
            onClick={() => setShowOnboard((v) => !v)}
          >
            {showOnboard ? "返回群聊" : "新建家庭"}
          </button>
        </div>
      </header>

      {/* ── Main layout ── */}
      <div className="main-layout">
        {/* Left: profile cards */}
        <aside className="sidebar">
          {hasFamily && <ProfileCards profiles={profiles} />}
          {!hasFamily && !showOnboard && (
            <div className="sidebar-empty">暂无家庭档案</div>
          )}
        </aside>

        {/* Center: chat or onboard */}
        <main className="chat-area">
          {showOnboard ? (
            <OnboardFormPanel onSubmit={handleOnboard} loading={onboarding} />
          ) : (
            <>
              {/* Skill badge */}
              {!skillOn && (
                <div className="compare-banner">
                  ⚡ 对比模式：通用助手（未载入 skill）— 同一条输入，看输出差异
                </div>
              )}

              {/* Messages */}
              <div className="messages-list">
                {messages.length === 0 && (
                  <div className="messages-empty">
                    <p>以 Rosa（照护者）或丽珍（雇主）身份发言</p>
                    <p className="hint">
                      示例 Rosa 输入：「Ma'am, Ah Ma today no mood to eat, lunch eat small small only half bowl… and she say she feel a bit dizzy.」
                    </p>
                    <p className="hint">
                      示例丽珍输入：「今晚我们四个人过来吃饭，妈妈的药记得饭前吃，6点要炒菜就早点准备。」
                    </p>
                  </div>
                )}
                {messages.map((m) => (
                  <ChatMessageBubble key={m.id} message={m} />
                ))}
                {loading && (
                  <div className="msg-loading">
                    <span className="loading-dot" />
                    <span className="loading-dot" />
                    <span className="loading-dot" />
                  </div>
                )}
                <div ref={bottomRef} />
              </div>

              {/* Error */}
              {error && <div className="error-banner">{error}</div>}

              {/* Input bar */}
              <div className="input-bar">
                <div className={clsx("input-role-indicator", `indicator-${role}`)}>
                  {role === "helper" ? "Rosa" : "丽珍"}
                </div>
                <textarea
                  className="input-textarea"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder={
                    role === "helper"
                      ? "Rosa 用 English / Singlish 描述观察…"
                      : "丽珍用中文发指令…"
                  }
                  rows={2}
                  disabled={loading || !hasFamily}
                />
                <VoiceButton
                  onAudioReady={handleAudio}
                  disabled={loading || !hasFamily}
                />
                <button
                  className="send-btn"
                  onClick={handleSend}
                  disabled={loading || !input.trim() || !hasFamily}
                >
                  <Send size={18} />
                </button>
              </div>

              {!hasFamily && (
                <div className="no-family-hint">
                  先点「新建家庭」或等待加载示例家庭…
                </div>
              )}
            </>
          )}
        </main>
      </div>
    </div>
  );
}

// ─── Helper: turn API result into a bot chat message ─────────────────────────
function buildBotMessage(result: ApiResult, _senderRole: Role): ChatMessage {
  let content = "";

  if (result.type === "helper") {
    if (!result.skill_on) {
      content = `[通用助手] ${result.outputs?.helper ?? result.restored_text ?? ""}`;
    } else {
      const gradeLabel =
        result.grade === "escalate"
          ? "🔴 即时升级"
          : result.grade === "routine"
          ? "🟡 常规通报"
          : "⚪ 记录";
      content = `${gradeLabel}：${result.reason}`;
    }
  } else {
    if (!result.skill_on) {
      content = `[通用助手] ${result.helper_message}`;
    } else {
      content = `已拆解为 ${result.tasks?.length ?? 0} 项任务，等待 Rosa 逐项确认。`;
    }
  }

  return {
    id: uid(),
    role: "bot",
    content,
    timestamp: new Date(),
    result,
  };
}
