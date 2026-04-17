#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import sys
from datetime import datetime
from pathlib import Path

import requests
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

LOGIN_URL = "https://dash.aclclouds.com/auth/login"
PROJECTS_URL = "https://dash.aclclouds.com/projects"
NEXT_TIME_FILE = Path("next_time.txt")

DISCORD_ACCOUNT = os.environ.get("DISCORD_ACCOUNT", "").strip()
DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN", "").strip()
PROXY = os.environ.get("PROXY_URL", "").strip()

TG_TOKEN = os.environ.get("TG_BOT_TOKEN", "").strip()
TG_CHAT_ID = os.environ.get("TG_CHAT_ID", "").strip()


def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def require_credentials():
    if DISCORD_TOKEN:
        return
    if not DISCORD_ACCOUNT or "," not in DISCORD_ACCOUNT:
        print("❌ 缺少 Discord 登录信息，请设置 DISCORD_TOKEN 或 DISCORD_ACCOUNT=email,password")
        sys.exit(1)


def get_discord_email_password():
    email, password = (DISCORD_ACCOUNT.split(",", 1) + [""])[:2]
    return email.strip(), password.strip()


def send_tg_photo(caption, image_path):
    if not TG_TOKEN or not TG_CHAT_ID or not os.path.exists(image_path):
        return
    try:
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendPhoto"
        with open(image_path, "rb") as file_handle:
            requests.post(
                url,
                data={
                    "chat_id": TG_CHAT_ID,
                    "caption": f"[🤖 ACLClouds] {now_str()}\n{caption}",
                },
                files={"photo": file_handle},
                timeout=30,
            )
        print("📨 TG 图片推送成功！")
    except Exception as exc:
        print(f"⚠️ TG 推送失败: {exc}")


def save_next_time(text):
    NEXT_TIME_FILE.write_text(text, encoding="utf-8")
    print("📝 已将时间写入 next_time.txt，准备供工作流调整时间使用")


def inject_discord_token(page, token):
    print("🔑 准备注入 Discord Token 免密登录...")
    page.goto("https://discord.com/login", wait_until="domcontentloaded")
    page.evaluate(
        """
        (token) => {
            const iframe = document.createElement('iframe');
            document.body.appendChild(iframe);
            iframe.contentWindow.localStorage.token = `"${token}"`;
        }
        """,
        token,
    )
    page.wait_for_timeout(1500)
    print("✅ Token 注入完成")


def click_first_visible(page, selectors, timeout=5000):
    for selector in selectors:
        locator = page.locator(selector).first
        try:
            locator.wait_for(state="visible", timeout=timeout)
            locator.click()
            return selector
        except Exception:
            continue
    return None


def handle_discord_login(page):
    email, password = get_discord_email_password()
    if not email or not password:
        print("❌ DISCORD_ACCOUNT 格式错误，应为 email,password")
        sys.exit(1)

    print("⏳ 等待跳转 Discord 登录页...")
    page.wait_for_url(re.compile(r"discord\.com/login"), timeout=60000)

    print("✏️ 填写 Discord 账号密码...")
    page.locator('input[name="email"]').fill(email)
    page.locator('input[name="password"]').fill(password)

    print("📤 提交 Discord 登录请求...")
    page.locator('button[type="submit"]').click()
    page.wait_for_timeout(2500)

    if re.search(r"discord\.com/login", page.url):
        error_text = "账密错误或触发了 2FA / 验证码"
        for selector in [
            '[class*="errorMessage"]',
            '[aria-live="polite"]',
        ]:
            try:
                error_text = page.locator(selector).first.inner_text(timeout=2000).strip()
                break
            except Exception:
                continue
        raise RuntimeError(f"Discord 登录失败: {error_text}")


def handle_discord_oauth(page):
    print("⏳ 等待 Discord OAuth 授权...")
    try:
        page.wait_for_url(re.compile(r"discord\.com/oauth2/authorize"), timeout=10000)
    except PlaywrightTimeoutError:
        print(f"✅ 未进入显式授权页，当前 URL: {page.url}")
        return

    print("🔍 进入 OAuth 授权页，处理中...")
    page.wait_for_timeout(2000)

    for attempt in range(5):
        if "discord.com" not in page.url:
            print("✅ 已离开 Discord 授权页")
            return

        locator = page.locator('button:visible').filter(has_text=re.compile(r"Scroll|Authorize|授权|Continue|继续", re.I)).first
        try:
            button_text = locator.inner_text(timeout=3000).strip()
        except Exception:
            button_text = ""

        if not button_text:
            try:
                page.wait_for_url(lambda url: "discord.com" not in url, timeout=10000)
                print("✅ 已自动跳回业务站")
                return
            except PlaywrightTimeoutError:
                continue

        print(f"🔘 OAuth 按钮: {button_text}")
        if re.search(r"scroll|滚动", button_text, re.I):
            page.evaluate(
                """
                () => {
                    const node = document.querySelector('[class*="scroller"]')
                        || document.querySelector('[class*="content"]');
                    if (node) {
                        node.scrollTop = node.scrollHeight;
                    }
                    window.scrollTo(0, document.body.scrollHeight);
                }
                """
            )
            page.wait_for_timeout(1200)

        locator.click()
        page.wait_for_timeout(2000)

    print(f"⚠️ OAuth 授权页处理结束，当前 URL: {page.url}")


def login_to_aclclouds(page):
    if DISCORD_TOKEN:
        inject_discord_token(page, DISCORD_TOKEN)

    print(f"🌐 打开 ACLClouds 登录页: {LOGIN_URL}")
    page.goto(LOGIN_URL, wait_until="domcontentloaded")
    page.wait_for_timeout(2000)

    clicked = click_first_visible(
        page,
        [
            'button:has-text("Discord")',
            'a:has-text("Discord")',
            '[role="button"]:has-text("Discord")',
            'text=Discord',
        ],
        timeout=4000,
    )
    if not clicked:
        raise RuntimeError("未找到 Discord 登录入口")
    print(f"📤 已点击 Discord 登录入口: {clicked}")

    if not DISCORD_TOKEN:
        handle_discord_login(page)

    handle_discord_oauth(page)

    try:
        page.wait_for_url(re.compile(r"dash\.aclclouds\.com"), timeout=30000)
    except PlaywrightTimeoutError:
        pass

    if "dash.aclclouds.com" not in page.url:
        raise RuntimeError(f"未返回 ACLClouds，当前 URL: {page.url}")

    print(f"✅ ACLClouds 登录成功，当前页面: {page.url}")
    if "/projects" not in page.url:
        page.goto(PROJECTS_URL, wait_until="domcontentloaded")


def extract_expire_text(page):
    candidate_selectors = [
        'xpath=//*[contains(text(), "Expire")]/..',
        'xpath=//*[contains(text(), "Expiration")]/..',
        'text=/Expire|Expiration|Expires|到期/i',
        'text=/Remaining|剩余/i',
    ]

    for selector in candidate_selectors:
        try:
            text = page.locator(selector).first.inner_text(timeout=5000).strip().replace("\n", " ")
            if text:
                print(f"⏱️ 当前抓取到的剩余时间: {text}")
                save_next_time(text)
                return text
        except Exception:
            continue

    print("⚠️ 无法在页面上找到剩余时间文本，将不写入文件。")
    return "未知"


def renew_if_possible(page):
    too_early_patterns = [
        r"Renewal will be available 3 days before Expiration",
        r"Renewal will be available.*before Expiration",
    ]
    page_text = page.locator("body").inner_text(timeout=5000)
    for pattern in too_early_patterns:
        if re.search(pattern, page_text, re.I):
            print("⏰ 检测到'续期将于到期前 3 天提供'提示，暂无需续订。")
            return "not_needed"

    renew_selectors = [
        'button:has-text("Renew")',
        'button:has-text("Renouveler")',
        'a:has-text("Renew")',
        'a:has-text("Renouveler")',
        'xpath=//button[contains(., "Renew")]',
        'xpath=//button[contains(., "Renouveler")]',
        'xpath=//*[contains(text(), "Renew")]',
        'xpath=//*[contains(text(), "Renouveler")]',
    ]
    selector = click_first_visible(page, renew_selectors, timeout=2500)
    if selector:
        print(f"🔘 找到续订按键并点击: {selector}")
        page.wait_for_timeout(8000)
        return "renewed"

    print("❌ 未检测到续订按键。")
    return "missing"


def main():
    require_credentials()

    browser_args = ["--disable-dev-shm-usage", "--no-sandbox"]
    launch_kwargs = {
        "headless": True,
        "args": browser_args,
    }
    if PROXY:
        launch_kwargs["proxy"] = {"server": PROXY}
        print(f"🛡️ 使用代理: {PROXY}")

    print("🔧 启动 Playwright Chromium 浏览器...")
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(**launch_kwargs)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()
        page.set_default_timeout(30000)

        try:
            login_to_aclclouds(page)
            print("🚀 等待项目页数据加载...")
            page.goto(PROJECTS_URL, wait_until="domcontentloaded")
            page.wait_for_timeout(5000)

            expire_time_text = extract_expire_text(page)
            renew_result = renew_if_possible(page)

            if renew_result == "not_needed":
                screenshot = "renew_not_needed.png"
                page.screenshot(path=screenshot, full_page=True)
                send_tg_photo(f"⏰ 暂无需续订。\n⏱️ 当前状态: {expire_time_text}", screenshot)
            elif renew_result == "renewed":
                expire_time_text = extract_expire_text(page)
                screenshot = "renew_success.png"
                page.screenshot(path=screenshot, full_page=True)
                send_tg_photo(f"🎉 已执行续订。\n⏱️ 当前面板显示状态: {expire_time_text}", screenshot)
            else:
                screenshot = "renew_error.png"
                page.screenshot(path=screenshot, full_page=True)
                send_tg_photo("❌ 未检测到续订按键 (也未找到暂不可续订提示)。", screenshot)
                sys.exit(1)
        except Exception as exc:
            print(f"❌ 运行报错: {exc}")
            screenshot = "error.png"
            try:
                page.screenshot(path=screenshot, full_page=True)
                send_tg_photo(f"❌ 脚本运行异常: {exc}", screenshot)
            finally:
                browser.close()
            sys.exit(1)

        browser.close()


if __name__ == "__main__":
    main()
