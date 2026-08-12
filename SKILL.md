---
name: sales-chat-quality
description: Automate quality checks for Chinese pre-sales customer-service chats in a logged-in browser backend. Use when Codex needs to open the chat system, filter 售前消息查询, inspect 详情 dialogs, capture evidence screenshots, calculate response latency, assess reply quality, and produce a traceable PowerPoint report from JSON evidence.
---

# 售前聊天质检

## Overview

连接用户主动开启的 Chrome 远程调试会话，按后台界面流程筛选售前会话并保存原始证据。对每条客服回复计算响应时延，结合评价规则形成可追溯的中文质检结论；最终使用 Presentations skill 生成 PPTX。

## 安全边界与前置条件

- 不读取或保存账号密码、Cookie 或本地 Chrome 配置。
- 仅连接用户明确以 `--remote-debugging-port=9222` 启动的 Chrome；当前普通 Chrome 未暴露端口时，先提示用户用新窗口启动并在该窗口登录后台。
- 不修改后台数据，不发送消息；只执行查询、打开详情和截图。
- 只在用户指定的输出目录写入证据和报告，默认使用桌面 `售前聊天质检_<时间戳>`。

## 快速开始

1. 关闭需要保持的普通 Chrome 窗口，启动带调试端口的新窗口（Windows PowerShell）：
   ```powershell
   & "$env:ProgramFiles\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="$env:TEMP\codex-sales-chat-profile"
   ```
   在新窗口登录后台，然后保持窗口打开。
2. 采集会话：
   ```powershell
   node scripts\collect_chat.mjs --cdp-url http://127.0.0.1:9222 --max-conversations 20 --output "$env:USERPROFILE\Desktop\售前聊天质检"
   ```
3. 对生成的 `conversations.json` 使用 `scripts\score_chats.py --slow-threshold 10` 计算时延基线并生成 `evaluation_prompt.txt`。默认超过 10 秒标记“回复慢”，10 秒以内标记“正常”。将该提示词和截图/JSON交给 Codex，逐条完成语义质量评价。
4. 使用 Presentations skill 读取 JSON、截图和评价结果，生成 PPTX。每个会话至少包含：会话标识、原始截图、逐条客服回复、上一条用户消息、响应秒数、质量结论、证据定位和改进建议。

## MCP 接入（可选）

解压后可把 `scripts/mcp_server.py` 注册为本地 stdio MCP server。示例配置（将路径替换为解压后的绝对路径）：

```json
{
  "mcpServers": {
    "sales-chat-quality": {
      "command": "python",
      "args": ["C:/path/to/sales-chat-quality/scripts/mcp_server.py"]
    }
  }
}
```

注册后可调用 `collect_sales_chats` 和 `score_sales_chats`；语义评价仍由 Codex 根据返回的 JSON、截图和评价提示词完成。

## 采集流程

优先使用 DOM 文本和角色定位，视觉截图只作为审计证据。采集器会：定位“聊天系统”→“售前消息查询”；确认类型为“售前”；点击“搜索”；逐页点击“详情”；等待“消息记录查询”弹窗；保存弹窗截图和完整文本；解析“买家/售前”标签及时间戳；最后关闭弹窗并继续下一行。

如果页面文案或结构发生变化，不要猜测并执行危险操作；先保存当前页面截图和文本，报告定位失败原因，再调整 `scripts/collect_chat.mjs` 中的候选选择器。

## 评价与报告规则

- 响应速度：按“用户消息 → 下一条客服消息”配对；小于等于 30 秒为优秀，31–60 秒为良好，61–180 秒为需关注，大于 180 秒为不合格。无法配对时标记“缺少可计算时间”。
- 回复质量：至少检查需求理解、信息准确、价格/费用说明、下一步引导、语气与合规、是否遗漏问题。每项给出通过/不通过/无法判断，并引用原句。
- 不把启发式分数当成最终语义判断；最终结论必须能够回链到截图或 JSON 中的消息序号。
- 对手机号、IP 等敏感字段在对外分享版本中脱敏；内部追溯版本可保留原始截图，但应限制访问。

详细评分维度见 [references/evaluation-rubric.md](references/evaluation-rubric.md)。

## 失败处理

- 无法连接 CDP：提示重新启动 Chrome，不要求用户提供密码。
- 找不到菜单、筛选器或详情：停止点击，保存 `page-debug.png` 与 `page-debug.txt`。
- 弹窗内容为空或分页加载失败：保留会话元数据并标记 `status=partial`，不要伪造评价。
- 页面需要人工确认时暂停并向用户说明当前页面，不自动提交任何表单。

## 资源

- `scripts/collect_chat.mjs`：Playwright CDP 采集器。
- `scripts/score_chats.py`：解析时间戳、计算响应时延并生成评价提示词。
- `scripts/mcp_server.py`：stdio MCP server，提供 `collect_sales_chats` 与 `score_sales_chats` 工具。
- `references/evaluation-rubric.md`：质检维度与报告字段约定。
