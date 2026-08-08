import type { ApiResult, OnboardForm, Profiles } from "./types";

const BASE = import.meta.env.VITE_API_URL ?? "";

async function req<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...options.headers },
    ...options,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`API ${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  /** Health check */
  healthz: () => req<{ status: string }>("/healthz"),

  /** Onboard a family */
  onboard: (slug: string, body: OnboardForm) =>
    req<{ family_id: number; slug: string }>(`/families/${slug}/onboard`, {
      method: "POST",
      body: JSON.stringify(body),
    }),

  /** Get profiles + recent observations */
  profiles: (slug: string) =>
    req<{ slug: string } & Profiles>(`/families/${slug}/profiles`),

  /** Send text message */
  message: (
    slug: string,
    text: string,
    skill_on: boolean,
    role: "helper" | "employer" | "auto" = "auto",
    /** 上一轮 agent 问的澄清问题；本轮 text 是对它的回答 */
    pending_question?: string | null
  ) =>
    req<ApiResult>(`/families/${slug}/message`, {
      method: "POST",
      body: JSON.stringify({ text, skill_on, role, pending_question }),
    }),

  /** Upload audio file */
  audio: (
    slug: string,
    file: Blob,
    skill_on: boolean,
    role: "helper" | "employer" | "auto" = "auto"
  ) => {
    const form = new FormData();
    form.append("file", file, "recording.webm");
    return fetch(
      `${BASE}/families/${slug}/audio?skill_on=${skill_on}&role=${role}`,
      { method: "POST", body: form }
    ).then(async (res) => {
      if (!res.ok) throw new Error(`API ${res.status}`);
      return res.json() as Promise<ApiResult & { transcript?: string }>;
    });
  },

  /**
   * Reset a family.
   * seedObservations=false → 清空到零历史（演示"四种结局"第一格要孤立的一次）
   */
  reset: (slug: string, seedObservations = true) =>
    req<{ ok: boolean; deleted: number }>(
      `/families/${slug}/reset?seed_observations=${seedObservations}`,
      { method: "POST" }
    ),
};
