import os
import sys
import time
import subprocess
import requests
from datetime import datetime
from seleniumbase import SB

TARGET_URL = "https://dash.skybots.tech/login"
DASHBOARD_URL = "https://dash.skybots.tech/projects"

ACCOUNT = os.environ.get("SKYBOTS_ACCOUNT", "")
PASSWORD = os.environ.get("SKYBOTS_PASSWORD", "")
PROXY = os.environ.get("PROXY_URL", "")

TG_TOKEN = os.environ.get("TG_BOT_TOKEN", "")
TG_CHAT_ID = os.environ.get("TG_CHAT_ID", "")

def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def send_tg_photo(caption, image_path):
    if not TG_TOKEN or not TG_CHAT_ID or not os.path.exists(image_path):
        return
    try:
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendPhoto"
        with open(image_path, "rb") as f:
            requests.post(url, data={"chat_id": TG_CHAT_ID, "caption": f"[Bot] {now_str()}\n{caption}"}, files={"photo": f}, timeout=30)
        print("TG push success")
    except Exception as e:
        print(f"TG push failed: {e}")

EXPAND_POPUP_JS = """
(function() {
    var iframes = document.querySelectorAll('iframe');
    iframes.forEach(function(iframe) {
        if (iframe.src && (iframe.src.includes('challenges.cloudflare.com') || iframe.src.includes('turnstile'))) {
            iframe.style.width = '300px';
            iframe.style.height = '65px';
            iframe.style.minWidth = '300px';
            iframe.style.visibility = 'visible';
            iframe.style.opacity = '1';
        }
    });
})();
"""

def get_turnstile_coords(sb):
    return sb.execute_script("""
        var iframes = document.querySelectorAll('iframe');
        for (var i = 0; i < iframes.length; i++) {
            var src = iframes[i].src || '';
            if (src.includes('cloudflare') || src.includes('turnstile')) {
                var rect = iframes[i].getBoundingClientRect();
                if (rect.width > 0 && rect.height > 0) {
                    var screenX = window.screenX || 0;
                    var screenY = window.screenY || 0;
                    var outerHeight = window.outerHeight;
                    var innerHeight = window.innerHeight;
                    var chromeBarHeight = outerHeight - innerHeight;
                    
                    var abs_x = Math.round(rect.x + 30) + screenX;
                    var abs_y = Math.round(rect.y + rect.height / 2) + screenY + chromeBarHeight;
                    
                    return {x: abs_x, y: abs_y};
                }
            }
        }
        return null;
    """)

def os_hardware_click(x, y):
    try:
        result = subprocess.run(["xdotool", "search", "--onlyvisible", "--class", "chrome"], capture_output=True, text=True)
        w_ids = result.stdout.strip().split('\n')
        if w_ids and w_ids[0]:
            subprocess.run(["xdotool", "windowactivate", w_ids[0]], stderr=subprocess.DEVNULL)
            time.sleep(0.2)
        
        os.system(f"xdotool mousemove {int(x)} {int(y)} click 1")
        print(f"xdotool click ({x}, {y})")
        return True
    except Exception as e:
        print(f"xdotool failed: {e}")
        return False

def main():
    if not ACCOUNT or not PASSWORD:
        print("Missing credentials")
        sys.exit(1)

    print("Starting SB...")
    opts = {
        "uc": True, 
        "test": True, 
        "headless": False, 
        "locale": "en",
        "chromium_arg": "--disable-dev-shm-usage,--no-sandbox,--start-maximized"
    }
    if PROXY:
        opts["proxy"] = PROXY
        print("Using proxy")

    with SB(**opts) as sb:
        sb.set_window_rect(0, 0, 1280, 720)
        
        try:
            print("Accessing URL")
            sb.uc_open_with_reconnect(TARGET_URL, reconnect_time=6)
            time.sleep(5)

            if "projects" in sb.get_current_url():
                print("Already logged in.")
            else:
                print("Parsing login...")
                user_sel = 'input[type="email"], input[name="email"], input[name="username"], input[type="text"]'
                sb.wait_for_element(user_sel, timeout=30)
                
                print("Entering credentials...")
                sb.type(user_sel, ACCOUNT)
                sb.type('input[type="password"], input[name="password"]', PASSWORD)
                
                print("Handling CF...")
                time.sleep(3)
                sb.execute_script(EXPAND_POPUP_JS)
                time.sleep(1)

                for attempt in range(4):
                    is_done = sb.execute_script("var cf = document.querySelector(\"input[name='cf-turnstile-response']\"); return cf && cf.value.length > 20;")
                    if is_done:
                        print("CF passed.")
                        break
                    
                    print(f"Verify attempt {attempt + 1}...")
                    try:
                        sb.uc_gui_click_captcha()
                        print("Waiting 5s...")
                        time.sleep(5)
                    except Exception as e:
                        coords = get_turnstile_coords(sb)
                        if coords:
                            os_hardware_click(coords['x'], coords['y'])
                            print("Waiting 5s...")
                            time.sleep(5)
                        else:
                            print("Retrying...")
                            time.sleep(3)

                print("Submitting...")
                sb.click('button[type="submit"], button:contains("Login")')
                
                print("Waiting 10s...")
                time.sleep(10)
                
                if "projects" not in sb.get_current_url():
                    print("Directly accessing dashboard...")
                    sb.uc_open_with_reconnect(DASHBOARD_URL, reconnect_time=5)
                    time.sleep(5)

            print("Searching for renew button...")
            sb.sleep(8) 
            
            too_early_sel = "//div[contains(., 'Renewal will be available 3 days before Expiration')]"
            if sb.is_element_visible(too_early_sel):
                print("Renewal not needed yet.")
                shot_path = "renew_not_needed.png"
                sb.save_screenshot(shot_path)
                send_tg_photo("Renewal not needed yet.", shot_path)
            else:
                renew_selectors = [
                    'button:contains("Renew")', 
                    'button:contains("Renouveler")',
                    'a:contains("Renew")',
                    'a:contains("Renouveler")',
                    '//button[contains(., "Renew")]',
                    '//button[contains(., "Renouveler")]',
                    '//*[contains(text(), "Renew")]',
                    '//*[contains(text(), "Renouveler")]'
                ]
                found_btn = False
                
                for sel in renew_selectors:
                    if sb.is_element_visible(sel):
                        print(f"Found button with {sel}")
                        sb.click(sel)
                        found_btn = True
                        break
                
                if found_btn:
                    print("Waiting 10s for renewal...")
                    sb.sleep(10)
                    
                    expire_time_text = "Unknown"
                    try:
                        expire_element = sb.wait_for_element('//*[contains(text(), "Expire")]/..', timeout=5)
                        expire_time_text = expire_element.text.replace('\n', ' ').strip()
                        print(f"Time remaining: {expire_time_text}")
                    except Exception as e:
                        print("Could not find remaining time.")

                    shot_path = "renew_success.png"
                    sb.save_screenshot(shot_path)
                    
                    tg_msg = f"Renew clicked!\nStatus: {expire_time_text}"
                    send_tg_photo(tg_msg, shot_path)
                else:
                    print("Renew button not found.")
                    shot_path = "renew_error.png"
                    sb.save_screenshot(shot_path)
                    send_tg_photo("Renew button not found.", shot_path)

        except Exception as e:
            print(f"Error: {e}")
            sb.save_screenshot("error.png")
            send_tg_photo(f"Error: {e}", "error.png")
            sys.exit(1)

if __name__ == "__main__":
    main()
