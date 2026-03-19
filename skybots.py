#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import time
import subprocess
import requests
from datetime import datetime
from seleniumbase import SB

# ================= 配置区 =================
TARGET_URL = "https://dash.skybots.tech/login"
DASHBOARD_URL = "https://dash.skybots.tech/projects"

ACCOUNT = os.environ.get("SKYBOTS_ACCOUNT", "")
PASSWORD = os.environ.get("SKYBOTS_PASSWORD", "")
PROXY = os.environ.get("PROXY_URL", "")

TG_TOKEN = os.environ.get("TG_BOT_TOKEN", "")
TG_CHAT_ID = os.environ.get("TG_CHAT_ID", "")

# ================= 辅助函数 =================
def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def send_tg_photo(caption, image_path):
    if not TG_TOKEN or not TG_CHAT_ID or not os.path.exists(image_path):
        return
    try:
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendPhoto"
        with open(image_path, "rb") as f:
            requests.post(url, data={"chat_id": TG_CHAT_ID, "caption": f"[🤖 Skybots] {now_str()}\n{caption}"}, files={"photo": f}, timeout=30)
        print("📨 TG 图片推送成功！")
    except Exception as e:
        print(f"⚠️ TG 推送失败: {e}")

# 强制暴露隐藏的 CF 盾并解开所有 overflow 遮罩
EXPAND_POPUP_JS = """
(function() {
    var turnstileInput = document.querySelector('input[name="cf-turnstile-response"]');
    if (turnstileInput) {
        var el = turnstileInput;
        for (var i = 0; i < 20; i++) {
            el = el.parentElement;
            if (!el) break;
            var style = window.getComputedStyle(el);
            if (style.overflow === 'hidden' || style.overflowX === 'hidden' || style.overflowY === 'hidden') {
                el.style.overflow = 'visible';
            }
            el.style.minWidth = 'max-content';
        }
    }
    var iframes = document.querySelectorAll('iframe');
    iframes.forEach(function(iframe) {
        iframe.style.visibility = 'visible';
        iframe.style.opacity = '1';
    });
})();
"""

# 获取盾的绝对屏幕坐标 (多重判定，顺藤摸瓜)
def get_turnstile_coords(sb):
    return sb.execute_script("""
        var getC = function(rect) {
            var chromeBarHeight = window.outerHeight - window.innerHeight;
            return {
                x: Math.round(rect.x + 30) + (window.screenX || 0),
                y: Math.round(rect.y + rect.height / 2) + (window.screenY || 0) + chromeBarHeight
            };
        };
        
        // 策略1: 找经典 iframe
        var iframes = document.querySelectorAll('iframe');
        for (var i = 0; i < iframes.length; i++) {
            var src = iframes[i].src || '';
            if (src.includes('cloudflare') || src.includes('turnstile') || src.includes('challenges')) {
                var rect = iframes[i].getBoundingClientRect();
                if (rect.width > 30 && rect.height > 20) return getC(rect);
            }
        }
        
        // 策略2: 从隐藏的底层表单往上层容器找 (最稳妥)
        var input = document.querySelector('input[name="cf-turnstile-response"]');
        if (input) {
            var container = input.parentElement;
            for (var j = 0; j < 5; j++) {
                if (!container) break;
                var rect = container.getBoundingClientRect();
                if (rect.width > 80 && rect.height > 20) return getC(rect);
                container = container.parentElement;
            }
        }
        return null;
    """)

# 使用 Linux 底层工具进行物理点击
def os_hardware_click(x, y):
    try:
        result = subprocess.run(["xdotool", "search", "--onlyvisible", "--class", "chrome"], capture_output=True, text=True)
        w_ids = result.stdout.strip().split('\n')
        if w_ids and w_ids[0]:
            subprocess.run(["xdotool", "windowactivate", w_ids[0]], stderr=subprocess.DEVNULL)
            time.sleep(0.2)
        
        os.system(f"xdotool mousemove {int(x)} {int(y)} click 1")
        print(f"👆 已使用 xdotool 物理点击屏幕坐标 ({x}, {y})")
        return True
    except Exception as e:
        print(f"⚠️ xdotool 点击失败: {e}")
        return False

# ================= 主逻辑 =================
def main():
    if not ACCOUNT or not PASSWORD:
        print("❌ 缺少账号或密码环境变量")
        sys.exit(1)

    print("🔧 启动 SeleniumBase UC 模式浏览器...")
    opts = {
        "uc": True, 
        "test": True, 
        "headless": False, 
        "chromium_arg": "--disable-dev-shm-usage,--no-sandbox,--start-maximized"
    }
    if PROXY:
        opts["proxy"] = PROXY
        print(f"🛡️ 使用代理: {PROXY}")

    with SB(**opts) as sb:
        # 强制设置一个固定窗口大小，防止 xvfb 坐标偏移
        sb.set_window_rect(0, 0, 1280, 720)
        
        try:
            print(f"🌐 访问目标网页: {TARGET_URL}")
            sb.uc_open_with_reconnect(TARGET_URL, reconnect_time=6)
            time.sleep(5)

            if "projects" in sb.get_current_url():
                print("✅ 似乎已经处于登录状态！")
            else:
                print("🛡️ 正在解析登录表单...")
                user_sel = 'input[type="email"], input[name="email"], input[name="username"], input[type="text"]'
                sb.wait_for_element(user_sel, timeout=30)
                
                print("✏️ 填写账号密码...")
                sb.type(user_sel, ACCOUNT)
                sb.type('input[type="password"], input[name="password"]', PASSWORD)
                
                print("🛡️ 开始处理 Cloudflare 验证框...")
                time.sleep(3)
                sb.execute_script(EXPAND_POPUP_JS)
                time.sleep(1)

                # 尝试突破 CF 盾
                for attempt in range(4):
                    is_done = sb.execute_script("var cf = document.querySelector(\"input[name='cf-turnstile-response']\"); return cf && cf.value.length > 20;")
                    if is_done:
                        print("✅ CF 盾底层验证已通过！")
                        break
                    
                    print(f"🖱️ 尝试验证 (第 {attempt + 1} 次)...")
                    try:
                        # 方案 A：使用 SeleniumBase 原生专杀工具
                        sb.uc_gui_click_captcha()
                        print("⏳ 触发原生点击过盾，等待动画 (5秒)...")
                        time.sleep(5)
                    except Exception as e:
                        print(f"⚠️ 原生点击未触发: {e}")
                        # 方案 B：使用获取坐标的底层硬件点击
                        coords = get_turnstile_coords(sb)
                        if coords:
                            os_hardware_click(coords['x'], coords['y'])
                            print("⏳ 等待盾验证动画 (5秒)...")
                            time.sleep(5)
                        else:
                            print("⚠️ 仍未找到盾的位置，等待重试...")
                            time.sleep(3)

                print("📤 提交登录...")
                sb.click('button[type="submit"], button:contains("Se connecter"), button:contains("Login")')
                
                print("⏳ 等待页面跳转...")
                time.sleep(10)
                
                if "projects" not in sb.get_current_url():
                    print("⚠️ URL 未变化，尝试直接访问 Dashboard...")
                    sb.uc_open_with_reconnect(DASHBOARD_URL, reconnect_time=5)
                    time.sleep(5)

            print("🚀 查找续期按键...")
            sb.sleep(3)
            
            renew_selectors = ['button:contains("Renew")', 'a:contains("Renew")']
            found_btn = False
            
            for sel in renew_selectors:
                if sb.is_element_visible(sel):
                    print("🔘 找到续期按键，点击续期...")
                    sb.click(sel)
                    found_btn = True
                    break
            
            if found_btn:
                print("⏳ 等待续期处理 (10秒)...")
                sb.sleep(10)
                shot_path = "renew_success.png"
                sb.save_screenshot(shot_path)
                send_tg_photo("🎉 续期按钮已找到并点击！(突破 Cloudflare 盾)", shot_path)
            else:
                print("⏰ 未找到续期按键。")
                shot_path = "renew_not_needed.png"
                sb.save_screenshot(shot_path)
                send_tg_photo("⏰ 今日暂无需续期 (未找到 Renew 按键)。", shot_path)

        except Exception as e:
            print(f"❌ 运行报错: {e}")
            sb.save_screenshot("error.png")
            send_tg_photo(f"❌ 脚本运行异常: {e}", "error.png")
            sys.exit(1)

if __name__ == "__main__":
    main()
