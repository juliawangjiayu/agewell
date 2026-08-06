<!--
  Demo 种子数据 = "我们要展示的那个故事"的定稿。
  用途：① 驱动 seed.py 预置一个 Ah Ma 家庭（视频用 + demo link 上的示例家庭）
        ② 评委在 demo link 上也能选这个家庭直接体验，或自己 onboard 新家庭
  说明：`[方括号]` 是需人审核对/替换的真实医学细节；其余可直接用。
  剧本逻辑：预置到 Day4，Day5 的"头晕"和雇主的备餐指令是 demo 里【当场输入】的动作。
-->

# Demo 种子故事：Ah Ma / Rosa / 丽珍

## 一、三张常驻 Profile 卡片（onboard 后生成，一直展示）

### 卡片 A · 雇主 profile（employer_profile）
| 字段 | 值 |
|---|---|
| name | 丽珍 |
| language | 中文 |
| relation | 女儿（Ah Ma 的女儿） |
| work_schedule | 白天在 [CBD] 上班，晚上回家 |
| notes | 家里主要照护决策者；白天不在家，靠 Rosa 贴身照护 |

### 卡片 B · 被照顾老人 profile（elder_profile）
| 字段 | 值 |
|---|---|
| name | [陈亚妹 / Ah Ma] |
| age | [82] |
| conditions | [高血压]、[2 型糖尿病] |
| baseline_notes | 平时三餐正常，能自己走动，晚饭后爱看电视 |

**用药表（medications, JSONB）**：
| 药 | 时点 | 时间 | 备注 |
|---|---|---|---|
| [Amlodipine（氨氯地平）] | 早饭后 | [08:00] | [降压] |
| [Metformin（二甲双胍）] | 早、晚饭后 | [08:00 / 19:00] | [降糖，可能引起肠胃不适] |
| [Losartan（氯沙坦）] | 早饭后 | [08:00] | [降压] |

**复诊（followups, JSONB）**：
- clinic：[XX Polyclinic]
- interval：[每 3 个月]
- next_date：[Day9（本周五）]
- last_med_change_date：**Day3**（把 [Amlodipine 5mg → 10mg]）← 升级判断的关键锚点

### 卡片 C · Caregiver 女佣 profile（caregiver_profile）
| 字段 | 值 |
|---|---|
| name | Rosa |
| home_country | 菲律宾 |
| mother_tongue | Tagalog（常英菲混说，"eat small small"式） |
| care_abilities | 照顾过长辈、会量血压、会做简单中餐 / [菲式]家常菜 |

---

## 二、预置的历史记录（seed 时写入，让 Day5 的升级"有上下文可依"）

**observations 表预置两行**（都 `record`，不惊动任何人——体现"85% 落第一层"）：
| date | raw_text | restored_text | grade |
|---|---|---|---|
| Day1 | "Ah Ma today lunch eat small only" | 午饭进食量减少约 50% | record |
| Day4 | "still no mood to eat, half bowl lang" | 仍进食减少，本周多次 | record |

**并设 elder_profile.followups.last_med_change_date = Day3。**

> 这样一进 demo，上下文库里已经是"食欲下降 2 次 + 3 天前刚调降压药"的状态——Day5 那句头晕一进来，升级判断才有据可依，不是凭空跳红。

---

## 三、Demo 当场输入的剧本节拍（不预置，现场/视频里逐条输入）

### 节拍 1 —— 女佣→雇主 · 分级/升级（故事 A 高光）
**Rosa 语音/文字输入（Tagalog 混说）**：
> "Ma'am, si Ah Ma po, ayaw kumain masyado today, tanghali kalahati lang… tapos sabi niya medyo nahihilo siya."

**系统应产出**：
- restored_text：Ah Ma 今天没什么胃口，午饭只吃了半碗，还说有点头晕
- grade：`escalate` 🔴
- notify：`["doctor", "family"]`
- reason：头晕与 [Day3] 上调降压药 [Amlodipine] 时间关联；食欲下降 + 头晕症状组合
- outputs.family / outputs.doctor / outputs.helper：见 spec 第七节三方文本（family = 家人，此家庭里是女儿丽珍）
- 老人端语音告知："这件事我需要告诉你女儿"

### 节拍 2 —— 雇主→女佣 · 拆解 + 确认闭环（故事 B）
**丽珍输入（中文）**：
> "今晚四个人吃饭，妈妈的药记得饭前吃，[6] 点要炒菜就早点准备。"

**系统应产出**（tasks + Tagalog helper_message + confirmation_items）：
- ☐ 今晚 [4] 人晚饭（[18:30]）
- ☐ Ah Ma [降压药] —— 饭前（约 [17:30]）
- ☐ [17:00] 开始备菜（[18:00] 炒，提前 1 小时）
- Rosa 逐项打勾确认；丽珍端看到的不再是"嗯"，是三项被接住

### 节拍 3 —— 对比模式（可在任一节拍上一键切换）
同一条输入，`skill_on=False`（通用好助手）给一段泛泛回应；`skill_on=True` 给上面全套判断。

### 节拍 4 —— 收尾（可选，视频里带过）
- 每周摘要（语音）："这周你女儿知道了两件事：你胃口不太好，还有说有点头晕。"
- 医生端一页结构化摘要（outputs.doctor 的完整版）

---

## 三·五、三级分级示例剧本（demo 分别展示 record / routine / escalate）

同一个 Ah Ma 家庭，用三句不同的女佣观察，展示系统对**三种严重度**的不同处理——证明"绝大多数静默记录、只在该打断时才打断"是产品主张，不是能力不足。演示前先"重置"到干净种子状态。

### 剧本 A · record（记录，不通知）——占 ~85%，体现防误报
**Rosa 输入（Singlish）**：
> "Ah Ma today lunch eat a bit less lah, but she ok, now watching TV."

**系统产出**：灰色标签 **记录** · 通知：无 · 为什么：单次轻微波动，无持续性、无用药关联。
- outputs.helper（只回女佣）："好的 Rosa，我记下了，先观察就好，不用担心。"
- **家人端/医生端：什么都不弹。** ← demo 里要特意指出："看，它没有打扰任何人。"

### 剧本 B · routine（常规通报，通知家人）——持续性改变
**Rosa 输入（Singlish）**：
> "Ah Ma still no appetite today, half bowl only. This week third time already."
> （上下文：本周已 2 次食欲下降）

**系统产出**：黄色标签 **常规通报** · 通知：家人 · 为什么：本周第 3 次持续性食欲下降，需家人知情但不紧急。
- outputs.family："阿姨这周有三次胃口不太好，不是紧急情况，但想让你知道，今晚回家可以留意一下她吃得怎么样。"
- outputs.helper："好的 Rosa，你观察得很到位，接下来几天继续帮我留意她吃多少。"
- **医生端：不弹**（还没到临床升级）。

### 剧本 C · escalate（即时升级，医生+家人）——即节拍 1 高光
**Rosa 输入（Singlish）**：
> "she got no mood to eat, only eat small small, and she say she feel a bit dizzy."
> （上下文：Day3 刚调降压药）

**系统产出**：红色标签 **即时升级** · 通知：医生 + 家人 · 为什么：头晕与调药时间关联 + 症状组合。
- 三段差异化输出（family / doctor / helper）全出；老人端语音告知（视频）。

> **三张并排**（record 灰 / routine 黄 / escalate 红）是回答"你的分级准不准 / 会不会天天误报"的最佳一屏：同一个人、同类主诉（食欲），系统只在证据够时才升级。

---

## 四、给评委在 demo link 上自由体验的三条路径
1. **选 Ah Ma 家庭** → 直接体验上面 4 个节拍（预置好上下文）
2. **切雇主视角** → 自己发一句含糊指令，看拆解 + 确认
3. **切女佣视角** → 自己发一句观察，看分级；或走一遍 onboard 建一个**新家庭**，看三张 profile 卡片当场生成

> 三视角 + onboard 都可玩，这正是你要的"随意体验"。
