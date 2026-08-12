#!/usr/bin/env node
import fs from 'node:fs/promises';
import path from 'node:path';
import process from 'node:process';

function arg(name, fallback = undefined) {
  const i = process.argv.indexOf(`--${name}`);
  return i >= 0 ? process.argv[i + 1] : fallback;
}

const cdpUrl = arg('cdp-url', 'http://127.0.0.1:9222');
const output = path.resolve(arg('output', path.join(process.env.USERPROFILE || '.', 'Desktop', `售前聊天质检_${Date.now()}`)));
const maxConversations = Number(arg('max-conversations', '20'));
const maxPages = Number(arg('max-pages', '1'));

await fs.mkdir(output, { recursive: true });
let chromium;
try {
  ({ chromium } = await import('playwright')); // supplied by the user's Node environment
} catch (error) {
  console.error('未找到 Playwright。请先在运行目录执行: npm install playwright');
  process.exit(2);
}

let browser;
try {
  browser = await chromium.connectOverCDP(cdpUrl);
} catch (error) {
  console.error(`无法连接 Chrome CDP ${cdpUrl}。请用 --remote-debugging-port=9222 启动 Chrome 并登录后台。`);
  process.exit(3);
}

const contexts = browser.contexts();
const pages = contexts.flatMap(context => context.pages());
if (!pages.length) throw new Error('CDP 已连接，但没有可用页面。');
let page = pages.find(p => /售前消息查询|聊天系统/.test(p.url())) || pages[0];
const pause = ms => new Promise(resolve => setTimeout(resolve, ms));
const visibleText = async () => (await page.locator('body').innerText()).replace(/\u00a0/g, ' ');

async function clickText(text, options = {}) {
  const exact = options.exact ?? true;
  const candidates = [
    page.getByRole('button', { name: text, exact }),
    page.getByRole('link', { name: text, exact }),
    page.getByText(text, { exact }),
  ];
  for (const locator of candidates) {
    if (await locator.count() && await locator.first().isVisible().catch(() => false)) {
      await locator.first().click();
      return true;
    }
  }
  return false;
}

async function ensureQueryPage() {
  if (/售前消息查询/.test(await visibleText())) return;
  await clickText('聊天系统', { exact: false });
  await pause(300);
  if (!await clickText('售前消息查询', { exact: true })) {
    throw new Error('找不到“售前消息查询”菜单。');
  }
  await pause(500);
}

async function ensureSalesType() {
  const input = page.locator('input[placeholder="请选择类型"]');
  if (!await input.count()) throw new Error('找不到“类型”下拉框。');
  if ((await input.inputValue().catch(() => '')).trim() === '售前') return;
  await page.keyboard.press('Escape');
  await input.click();
  const option = page.locator('.el-select-dropdown__item:visible').filter({ hasText: /^售前$/ }).first();
  await option.waitFor({ state: 'visible', timeout: 3000 }).catch(() => {});
  if (!await option.count() || !await option.isVisible().catch(() => false)) throw new Error('类型下拉框中找不到“售前”选项。');
  await option.click();
  await pause(150);
}

function parseMessages(text) {
  const lines = text.split(/\r?\n/).map(s => s.trim()).filter(Boolean);
  const messages = [];
  for (let i = 0; i < lines.length; i += 1) {
    if (!/^(买家|售前)$/.test(lines[i])) continue;
    const roleLabel = lines[i];
    let end = i + 1;
    while (end < lines.length && !/^(买家|售前)$/.test(lines[end])) end += 1;
    const block = lines.slice(i + 1, end);
    const timestamp = block.find(line => /^\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}$/.test(line)) || '';
    const sourceIndex = block.findIndex(line => /^来源:/.test(line));
    const textStart = sourceIndex >= 0 ? sourceIndex + 1 : block.findIndex(line => /^\d{4}-\d{2}-\d{2}/.test(line)) + 1;
    const content = block.slice(Math.max(textStart, 0)).filter(line => !/^IP:/.test(line)).join('\n');
    messages.push({ role: roleLabel === '售前' ? 'agent' : 'buyer', timestamp, text: content });
    i = end - 1;
  }
  return messages;
}

async function saveDebug(prefix) {
  await page.screenshot({ path: path.join(output, `${prefix}-page-debug.png`), fullPage: true });
  await fs.writeFile(path.join(output, `${prefix}-page-debug.txt`), await visibleText(), 'utf8');
}

await ensureQueryPage();
await ensureSalesType();
const search = page.getByRole('button', { name: '搜索', exact: true });
if (!await search.count()) throw new Error('找不到“搜索”按钮。');
await search.click();
await page.locator('.el-loading-mask:visible').waitFor({ state: 'hidden', timeout: 15000 }).catch(() => {});
await pause(500);

const conversations = [];
let processed = 0;
for (let pageNo = 1; pageNo <= maxPages && processed < maxConversations; pageNo += 1) {
  const details = page.getByRole('button', { name: '详情', exact: true });
  const count = await details.count();
  if (!count) {
    await saveDebug(`page-${pageNo}`);
    break;
  }
  for (let row = 0; row < count && processed < maxConversations; row += 1) {
    const buttons = page.getByRole('button', { name: '详情', exact: true });
    await buttons.nth(row).click();
    await pause(350);
    const dialog = page.locator('[role="dialog"]:visible, .el-dialog:visible, .ant-modal:visible').first();
    if (!await dialog.count()) {
      await saveDebug(`conversation-${processed + 1}`);
      conversations.push({ index: processed + 1, status: 'partial', messages: [], error: '找不到消息记录查询弹窗' });
      continue;
    }
    await dialog.locator('.el-loading-mask:visible').waitFor({ state: 'hidden', timeout: 15000 }).catch(() => {});
    await dialog.getByText(/买家|售前/).first().waitFor({ state: 'visible', timeout: 15000 }).catch(() => {});
    await pause(250);
    const rawText = await dialog.innerText();
    const index = processed + 1;
    const screenshot = path.join(output, `conversation-${String(index).padStart(4, '0')}.png`);
    await dialog.screenshot({ path: screenshot });
    const meta = await page.locator('tbody tr').nth(row).innerText().catch(() => '');
    const messages = parseMessages(rawText);
    conversations.push({ index, status: messages.length ? 'ok' : 'partial', source_row: meta, screenshot, raw_text: rawText, messages, error: messages.length ? undefined : '详情弹窗未解析到买家或售前消息' });
    await clickText('关闭', { exact: true }) || await dialog.locator('[aria-label="Close"], .el-dialog__headerbtn, .ant-modal-close').first().click().catch(() => {});
    await pause(200);
    processed += 1;
  }
  if (pageNo === maxPages || processed >= maxConversations) break;
  const next = page.getByRole('button', { name: /下一页/ }).first();
  if (!await next.count() || await next.isDisabled().catch(() => true)) break;
  await next.click();
  await pause(600);
}

await fs.writeFile(path.join(output, 'conversations.json'), JSON.stringify({ collected_at: new Date().toISOString(), source: 'sales-chat-quality', conversations }, null, 2), 'utf8');
console.log(`已采集 ${conversations.length} 个会话，输出目录: ${output}`);
await browser.close();
