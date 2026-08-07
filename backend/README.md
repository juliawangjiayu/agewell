# AgeWell 照护协同 Backend

FastAPI 后端，部署到 Railway。

## 本地运行（仅看代码跑测试）

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
USE_MOCK=1 pytest -v
```

## Railway 部署

1. 在 Railway 创建 PostgreSQL 服务，Railway 会自动注入 `DATABASE_URL`。
2. 在项目 Variables 里添加：
   - `DEEPSEEK_API_KEY=sk-...`
   - `MERALION_API_KEY=...`
3. `git push` 触发部署，Railway 执行 `Procfile` 里的 `web` 命令。
4. 部署后跑种子数据：
   ```bash
   railway run python -m app.seed
   ```

## 端点速查

| Method | Path | 用途 |
|--------|------|------|
| GET | `/healthz` | 健康检查 |
| POST | `/families/{slug}/onboard` | 创建/更新家庭三张 profile |
| GET | `/families/{slug}/profiles` | 查看家庭上下文 |
| POST | `/families/{slug}/message` | 发送文字消息（helper/employer/auto） |
| POST | `/families/{slug}/audio` | 上传音频 → STT → 同上 |
| GET | `/families/{slug}/observations` | 查看历史观察记录 |

## 对比模式

请求体加 `"skill_on": false` 即切换为无技能基准模式，同一输入可对比两种输出。
