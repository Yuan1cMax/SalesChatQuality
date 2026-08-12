# SalesChatQuality

一个面向中文售前客服会话的可追溯质检原型：使用 Playwright/CDP 只读采集后台会话与截图，用 Python 确定性计算响应时长，再由 LLM 基于原始消息完成语义质量评价。

> 项目来自实际客服抽检需求。Skill 已交付前同事在实际工作场景中使用；当前公开仓库是经过脱敏的最小 MVP，不包含后台域名、账号、客户数据或真实截图。

[在线案例与验证证据](http://101.43.56.2:8898/sales-chat-quality/) · [个人作品集](http://101.43.56.2:8898/)

## 关键设计

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

## 已验证事实与边界

- 真实后台完成过 `1` 条会话端到端回归，解析出 `3` 条买家消息和 `4` 条售前消息。
- 初版规则得到 `13` 秒慢回复和 `10` 秒正常回复；阈值可按业务 SOP 调整。
- Skill 已由前同事在实际工作场景中使用，当前仍定位为可验证的最小 MVP。
- 生产使用不等于通用产品化：批量调度、动态 SOP、长期准确率评测和所有后台适配仍是后续工作。
- 公开仓库不提供真实截图或客户数据。运行时生成的 JSON、截图与报告默认被 `.gitignore` 排除。

## 安全边界

- 不读取或保存密码、Cookie、浏览器配置或验证码。
- 只执行查询、打开详情和截图，不发送消息或修改后台数据。
- 页面结构变化时停止操作并保存调试证据，不猜测点击。
- 对外分享前必须移除后台域名、手机号、IP、账号和客服真实姓名。

完整操作流程与失败处理见 [SKILL.md](SKILL.md)，评价维度见 [references/evaluation-rubric.md](references/evaluation-rubric.md)。

