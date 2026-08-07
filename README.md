# AgeWell — 家庭照护协同助手

一个面向新加坡家庭照护场景的 Web 应用。女佣通过语音或文字上报对老人的观察，雇主通过文字下达照护指令；AI 负责判断分级、差异化输出，并将信息同步给家人和医生。

---

## 技术栈

| 层 | 技术 |
|---|---|
| 前端 | React + TypeScript + Vite |
| 后端 | FastAPI + psycopg3 |
| 数据库 | PostgreSQL |
| 部署 | Railway（后端 + DB）+ Vercel（前端）|
| LLM | DeepSeek API |
| STT | MERaLiON API（语音转文字）|

---

## 环境变量

### 后端（Railway Variables 或本地 `backend/.env`）

| 变量名 | 说明 |
|---|---|
| `DATABASE_URL` | PostgreSQL 连接串，格式：`postgresql://user:pass@host:port/dbname` |
| `DEEPSEEK_API_KEY` | DeepSeek API 密钥，用于 LLM 推理 |
| `MERALION_API_KEY` | MERaLiON API 密钥，用于语音转文字（STT）|

> 变量名须全大写，拼写须与上表完全一致。

### 前端（Vercel Environment Variables）

| 变量名 | 说明 |
|---|---|
| `VITE_API_URL` | 后端公网地址，例如 `https://agewell-production.up.railway.app`（末尾不加 `/`，须含 `https://`）|

---

## Skill 模式说明

每次发送消息时，界面右上角可切换 **载入 Skill / 通用助手** 两种模式。

### 载入 Skill（默认）

- **女佣端（Helper Skill）**：AI 对观察内容进行结构化判断——
  - 跨语言语义还原（Singlish / Taglish → 临床可用表述）
  - 三级分级：`record`（仅记录）/ `routine`（常规通报）/ `escalate`（即时升级）
  - 差异化输出：家人消息（口语、有行动建议）、医生消息（结构化、带时间线）、女佣回复（减负确认）
  - 分级依据上下文，结合近期观察历史和用药调整时间

- **雇主端（Employer Skill）**：AI 对指令进行拆解——
  - 把含糊的一句话拆成带时间节点的可执行任务列表
  - 自动补出必要前置动作（如提前买菜）
  - 用英语/Singlish 生成给女佣的逐项确认消息

### 通用助手（Skill 关闭）

- 不执行结构化判断或任务拆解
- 直接将家庭上下文（老人信息、用药表、近期观察）传给 LLM，由 LLM 给出简洁建议
- 适合临时问答或评估基线表现

---

## 本地开发

```bash
# 后端
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # 填入真实环境变量
uvicorn app.main:app --reload

# 前端（另开终端）
cd frontend
npm install
npm run dev
```

前端 dev 模式下已配置 proxy，`/families` 和 `/healthz` 请求自动转发到 `localhost:8000`，无需手动设置 `VITE_API_URL`。

---

## 部署

- **后端**：推送到 `main` 分支后，Railway 通过 `backend/railway.json` 自动部署；启动时自动执行 `apply_schema()` 和 `seed(skip_if_exists=True)`。
- **前端**：Vercel 监听 `main` 分支自动部署；确保 `VITE_API_URL` 已在 Vercel 项目设置中配置。
