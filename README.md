## ⭐ Star 星星走起 动动发财手点点 ⭐


---

> 自动登录 ACLClouds 控制台，进入项目页执行续订，并自动同步下次运行时间

---

## ⚠️ 注意事项

- 当前站点登录方式为 `Discord OAuth`
- 脚本使用 `DISCORD_TOKEN` 注入 Discord 登录态，不再使用账号密码登录
- 续订逻辑：检测到期时间、判断是否到达可续订窗口、点击 `Renew`
- `REPO_TOKEN` 需要具备 `repo` 和 `workflow` 权限，脚本运行后会自动更新 workflow 的下一次 cron 时间
- `GOST_PROXY` 为可选项，如果 GitHub Actions 直连访问不稳定，可以开启代理

---

## 🔐 Secrets 配置

| Secret 名称 | 必需 | 说明 |
|-------------|------|------|
| `DISCORD_TOKEN` | ✅ | Discord 登录 Token，用于注入登录态并完成 OAuth 登录 |
| `REPO_TOKEN` | ✅ | GitHub PAT，用于自动更新 workflow 定时任务 |
| `TG_BOT_TOKEN` | ❌ | Telegram Bot Token，不配置则跳过通知 |
| `TG_CHAT_ID` | ❌ | Telegram Chat ID，不配置则跳过通知 |
| `GOST_PROXY` | ❌ | 可选代理地址，例如 `socks5://127.0.0.1:1080` |

---

# 🚀 完整操作指南 - 分步骤详解

---

## 第一步：Fork 仓库

```text
1. 打开原仓库页面
2. 点击右上角 "Fork" 按钮
3. 点击 "Create fork"
4. 等待跳转到你的仓库副本
```

---

## 第二步：创建 Telegram Bot（选填）

### 2.1 创建 Bot

```text
1. Telegram 搜索 @BotFather
2. 发送 /newbot
3. 输入名称: ACLClouds Alert
4. 输入用户名: aclclouds_xxx_bot（需唯一）
5. 保存获得的 Token: 123456789:ABCxxxxxx...
```

### 2.2 获取 Chat ID

```text
1. 找到刚创建的 Bot，发送: hello
2. 浏览器访问: https://api.telegram.org/bot<你的Token>/getUpdates
3. 找到 "chat":{"id":123456789}
4. 保存这个数字: 123456789
```

---

## 第三步：获取 Discord Token

> 当前项目只使用 `DISCORD_TOKEN`，不再使用 Discord 账号密码

```text
1. 用浏览器登录 Discord
2. 打开 Discord 网页版 → F12 → Network → 任意请求 → Headers → authorization
3. 保存该 Token，后面填入 GitHub Secrets
```

说明：

- Token 失效后需要重新获取
- 建议使用自己的常用 Discord 号，避免频繁切换登录环境
- 请勿泄露 Token，该信息具有账号访问能力

---

## 第四步：配置 GitHub Secrets

### 4.1 进入 Secrets 页面

```text
你的仓库 -> Settings -> Secrets and variables -> Actions
```

### 4.2 添加 GitHub PAT

```text
1. 打开: https://github.com/settings/tokens
2. Generate new token (classic)
3. Note: ACLClouds
4. Expiration: No expiration
5. 勾选: repo, workflow
6. Generate token -> 复制 Token
7. 回到仓库 Secrets 添加:
   Name: REPO_TOKEN
   Secret: ghp_xxxxxxxxxxxx
```

### 4.3 添加其他 Secrets

点击 `New repository secret` 依次添加：

| Name | Secret（填入的值） |
|------|-------------------|
| `DISCORD_TOKEN` | 第三步获取的 Discord Token |
| `TG_BOT_TOKEN` | 第二步的 Bot Token，不需要通知可不填 |
| `TG_CHAT_ID` | 第二步的 Chat ID，不需要通知可不填 |
| `REPO_TOKEN` | 第四步 4.2 生成的 GitHub PAT |
| `GOST_PROXY` | 可选代理地址，不用代理可不填 |

### 4.4 确认完成

```text
至少应有 2 个 Secrets:
✅ DISCORD_TOKEN
✅ REPO_TOKEN

可选:
☑ TG_BOT_TOKEN
☑ TG_CHAT_ID
☑ GOST_PROXY
```

---

## 第五步：启用 Actions 并运行

### 5.1 启用 Actions

```text
1. 点击仓库顶部 "Actions"
2. 点击 "I understand my workflows, go ahead and enable them"
```

### 5.2 手动运行测试

```text
1. 左侧点击 "ACLClouds Auto Renew"
2. 点击 "Run workflow"
3. 点击绿色 "Run workflow" 按钮
```

### 5.3 查看运行日志

```text
点击新出现的运行记录 -> 查看实时日志
```

---

## 第六步：脚本执行逻辑

```text
1. 打开 Discord 登录页并注入 DISCORD_TOKEN
2. 跳转到 ACLClouds 登录页
3. 点击 Discord 登录入口
4. 处理 Discord OAuth 授权页
5. 返回 ACLClouds 项目页
6. 抓取页面上的到期时间文本
7. 检测是否出现“到期前 3 天才允许续订”的提示
8. 如果可以续订，则点击 Renew
9. 截图并推送 Telegram（如果已配置 TG）
10. 写入 next_time.txt 并自动更新 workflow 下次执行时间
```

---

## ✅ 完成检查

```text
✅ Fork 完成
✅ Discord Token 已准备
✅ Secrets 已添加
✅ Actions 已启用
✅ 首次运行成功

可选:
☑ Telegram Bot 创建完成
```

## 🎉 配置完成！

---

## 📊 流程图

```text
┌─────────────────────────────────────────────────────────┐
│  1. 打开 Discord 登录页并注入 Token                      │
│         ↓                                               │
│  2. 打开 ACLClouds 登录页                                │
│         ↓                                               │
│  3. 点击 "Discord" 登录按钮                             │
│         ↓                                               │
│  4. Discord OAuth 授权                                   │
│         ↓                                               │
│  5. 返回 ACLClouds 项目页                                 │
│         ↓                                               │
│  6. 提取到期时间 / 剩余时间                               │
│         ↓                                               │
│  7. 判断是否已到续订窗口                                  │
│         ├── 未到时间 -> 截图通知                          │
│         └── 已到时间 -> 点击 Renew                        │
│         ↓                                               │
│  8. 写入 next_time.txt                                    │
│         ↓                                               │
│  9. 自动修改 workflow cron                                │
└─────────────────────────────────────────────────────────┘
```

---

## 📁 文件结构

```text
.
├── .github/
│   └── workflows/
│       └── aclclouds.yml      # GitHub Actions 配置
├── aclclouds.py               # ACLClouds 自动续订脚本
└── README.md
```

---

## 🐛 常见问题

### Q: Discord 登录失败怎么办？
A: 先检查 `DISCORD_TOKEN` 是否有效。如果 Token 已失效，需要重新获取并更新到 GitHub Secrets。

### Q: 没找到续订按钮怎么办？
A: 先看 Telegram 推送截图（如果已配置 TG）或 Actions 日志，确认页面文案是否变化。当前续订逻辑仍按旧规则匹配 `Expire` 和 `Renew`。

### Q: 为什么没有更新下一次执行时间？
A: 检查 `next_time.txt` 是否成功写入，以及页面上的剩余时间文案是否仍符合当前解析规则。

### Q: 代理如何启用？
A: 在 Secrets 中添加 `GOST_PROXY`，格式例如 `socks5://127.0.0.1:1080`。workflow 会自动启动 gost 并注入 `PROXY_URL`。

### Q: REPO_TOKEN 需要什么权限？
A: 需要 `repo` 和 `workflow` 权限，否则 workflow 文件无法被自动提交更新。

---

## 📄 License

MIT License

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

⭐ 如果对你有帮助，请点个 Star 支持一下！

---

## ⚠️ 免责声明

* 本项目属于个人自动化工具，仅供技术学习与交流参考。
* 使用自动化脚本可能存在被平台判定为违规并导致**账号封禁**的风险。请合理控制执行频率，因使用本项目造成的任何直接或间接损失（包括但不限于账号被封、数据丢失等），需由使用者自行承担。
* 请务必保护好您的个人隐私，将凭证正确填写在 GitHub Secrets 中。本项目不保证长期有效性，亦不对因第三方平台更新导致的失效负责。
