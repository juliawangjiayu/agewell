# 判断层 skill 文件

**这个目录是 skill 的唯一真相。** `orchestrator.py` 在 import 时从这里读取：

```python
_SKILLS_DIR = pathlib.Path(__file__).parent / "skills"
```

- `helper_skill.md` —— 女佣端：观察 → 分级 → 四段差异化输出
- `employer_skill.md` —— 雇主端：含糊指令 → 冲突核对 → 带时间点的任务

改这里就是改线上行为，**改完需要重新部署才生效**。

> 原先 `docs/skills-draft/` 下有一份草稿副本，已删除——
> 两份 prompt 各自演进会导致「改了草稿但线上没变」的困惑。
> 需要起草新版本时，在本目录开分支改，不要另起副本。
