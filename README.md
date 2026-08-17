# SalesChatQuality - 客服聊天质检自动化 Skill

用于解决售前客服会话依赖人工逐条抽检、回复时延计算效率低、质检结论缺少原文证据的问题。完成真实客服会话端到端闭环验证后，项目已交付前同事并在实际客服质检工作中使用，将会话筛选、详情读取、回复时延计算、语义质检、证据整理和报告输出中的大量步骤自动化，显著减少人工质检介入。

> 当前版本仍是小规模初版 MVP，不代表已形成大规模企业级批量生产系统。首轮以 `1` 条真实会话验证采集、解析、计时、评价、证据和报告链路能够闭环；该数字仅是技术验证细节，不是项目使用范围。公开仓库已脱敏，不包含后台域名、账号、客户数据或真实截图。

[在线案例与验证证据](http://101.43.56.2:8898/sales-chat-quality/) · [个人作品集](http://101.43.56.2:8898/)

## 解决方案

```text
已登录 Chrome
      │  CDP / read-only
      ▼
collect_chat.mjs ──► conversations.json + screenshots
      │
      ▼
score_chats.py ────► response_seconds + rule result
      │
      ▼
LLM + rubric ──────► evidence-linked quality review
      │
      ▼
traceable report ──► JSON / PPTX
```

- **浏览器自动化负责采集**：进入售前查询、打开详情、等待加载、截图并解析角色/时间/正文。
- **确定性代码负责时间计算**：阈值可配置，异常时间戳不会被当作正常结果。
- **LLM 负责语义评价**：检查需求理解、准确性、费用说明、下一步引导、语气与问题覆盖，并要求引用原句。
- **MCP 负责工具化接入**：以 stdio 暴露采集和评分入口，供 Codex 或其他 MCP 客户端编排。

## 30 秒验证评分逻辑

无需登录任何后台即可运行脱敏样例：

```powershell
python scripts/score_chats.py examples/conversations.sample.json --output examples/scored.sample.json --slow-threshold 10
```

示例包含两次响应：`13` 秒会被标记为“回复慢”，`10` 秒被标记为“正常”。运行后还会生成 `examples/evaluation_prompt.txt`，用于约束 LLM 的证据化评价。

运行测试：

```powershell
python -m unittest discover -s tests -v
```

## 使用真实后台采集

安装依赖：

```powershell
npm install
python -m pip install -r requirements.txt
```

用隔离用户目录启动 Chrome，并在该窗口自行登录后台：

```powershell
& "$env:ProgramFiles\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="$env:TEMP\codex-sales-chat-profile"
```

采集只读证据：

```powershell
node scripts/collect_chat.mjs --cdp-url http://127.0.0.1:9222 --max-conversations 20 --output "$env:USERPROFILE\Desktop\售前聊天质检"
```

采集器针对一个真实后台的页面结构开发。迁移到其他系统时，需要根据菜单文案、DOM、分页和详情弹窗做局部适配；它不宣称零修改兼容所有客服后台。

## MCP 接入

```json
{
  "mcpServers": {
    "sales-chat-quality": {
      "command": "python",
      "args": ["C:/path/to/SalesChatQuality/scripts/mcp_server.py"]
    }
  }
}
```

工具：

- `collect_sales_chats`：连接已登录的 Chrome CDP 会话并输出截图和结构化 JSON。
- `score_sales_chats`：计算响应时间，返回评分文件、评价提示词和异常数量。

## 仓库结构

```text
SalesChatQuality/
├── SKILL.md                         # Codex Skill 工作流与安全边界
├── agents/openai.yaml               # Skill UI 元数据
├── references/evaluation-rubric.md  # 语义质检口径
├── scripts/collect_chat.mjs         # Playwright/CDP 采集器
├── scripts/score_chats.py           # 确定性响应时间计算
├── scripts/mcp_server.py            # stdio MCP Server
├── examples/                        # 脱敏输入样例
└── tests/                            # 评分边界测试
```

## 实际使用与 MVP 验证结果

- 初版 MVP 已交付前同事并在实际客服质检工作中使用，将会话读取、计时、语义质检、证据整理与报告输出中的大量步骤自动化。
- 受首版交付时间限制，先选取 `1` 条真实会话完成端到端回归；该数字只用于说明技术链路验证，不代表使用范围。
- 该会话解析出 `3` 条买家消息和 `4` 条售前消息；初版规则得到 `13` 秒慢回复和 `10` 秒正常回复，阈值可按业务 SOP 调整。
- 当前使用规模较小，不将项目外推为批量覆盖、大规模企业级生产系统或生产级准确率。
- 公开仓库不提供真实截图或客户数据。运行时生成的 JSON、截图与报告默认被 `.gitignore` 排除。

## 后续迭代

- 增加批量会话采集、定时调度、失败重试与断点续跑。
- 将质检 SOP、阈值和评价维度版本化，支持按业务线动态配置。
- 建立人工复核样本集，持续评估规则与 LLM 评价的一致性和准确率。
- 补充后台 DOM 适配层、异常监控和报告看板，降低页面变化带来的维护成本。

## 安全边界

- 不读取或保存密码、Cookie、浏览器配置或验证码。
- 只执行查询、打开详情和截图，不发送消息或修改后台数据。
- 页面结构变化时停止操作并保存调试证据，不猜测点击。
- 对外分享前必须移除后台域名、手机号、IP、账号和客服真实姓名。

完整操作流程与失败处理见 [SKILL.md](SKILL.md)，评价维度见 [references/evaluation-rubric.md](references/evaluation-rubric.md)。
