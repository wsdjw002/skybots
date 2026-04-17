## ⚙️ ACLClouds 环境变量配置 (GitHub Secrets)

为了让 ACLClouds 自动续订脚本正常运行并保护您的隐私信息，请在 GitHub 仓库中配置以下环境变量。

进入仓库的 **Settings** -> **Secrets and variables** -> **Actions**，点击 **New repository secret** 依次添加以下变量：

| 变量名 (Name) | 必填 | 说明 (Secret) |
| :--- | :---: | :--- |
| `DISCORD_TOKEN` | ✅ | **Discord 登录 Token**<br>脚本使用该变量注入 Discord 登录态并完成 OAuth 登录。 |
| `TG_BOT_TOKEN`    | ✅ | **Telegram Bot Token**<br>用于发送续期结果和截图。向 [@BotFather](https://t.me/BotFather) 申请机器人获取。<br>*(示例: `123456789:ABCdefGhIJKlmNoPQRstuVWXyz`)* |
| `TG_CHAT_ID`      | ✅ | **Telegram Chat ID**<br>接收通知的账号或群组 ID。可向 [@userinfobot](https://t.me/userinfobot) 发送消息获取。<br>*(示例: `123456789`)* |
| `REPO_TOKEN`      | ✅ | **GitHub 个人访问令牌 (PAT)**<br>核心权限：由于脚本具备“智能修改下一次运行时间”的黑科技功能，需要此 Token 才能将修改后的 `yml` 文件推送到仓库。<br>**[获取方法]** 访问 GitHub 设置 -> Developer settings -> Personal access tokens (classic) -> Generate new token。**必须勾选 `repo` 和 `workflow` 两个权限**。 |
| `GOST_PROXY`      | 选填 | **代理节点链接 (防封锁)**<br>如果不填，脚本将使用 GitHub 默认网络直连。如果遇到频繁的网络屏蔽，可填入您的代理节点。<br>*(示例: `socks5://127.0.0.1:1080`)* |

> **💡 提示：** > 所有的 Secret 变量在保存后都会被完全加密隐藏，即使是仓库所有者也无法再次查看明文，请放心填写。

---

### ⚠️ 免责声明

当前脚本目标站点：

* 登录页：`https://dash.aclclouds.com/auth/login`
* 项目页：`https://dash.aclclouds.com/projects`
* 登录方式：Discord OAuth

* 本项目属于个人自动化工具，仅供技术学习与交流参考。
* 使用自动化脚本可能存在被平台判定为违规并导致**账号封禁**的风险。请合理控制执行频率，因使用本项目造成的任何直接或间接损失（包括但不限于账号被封、数据丢失等），需由使用者自行承担。
* 请务必保护好您的个人隐私，将凭证正确填写在 GitHub Secrets 中。本项目不保证长期有效性，亦不对因第三方平台更新导致的失效负责。
