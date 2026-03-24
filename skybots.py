#!/usr/bin/env python3

import os
import sys
import time
import subprocess
import requests
from datetime import datetime
from seleniumbase import SB

T_U = "https://dash.skybots.tech/login"
D_U = "https://dash.skybots.tech/projects"

A = os.environ.get("S_A", "")
P = os.environ.get("S_P", "")
berry_PROXY_NODE = os.environ.get("berry_PROXY_NODE", "")

N_T = os.environ.get("N_T", "")
N_I = os.environ.get("N_I", "")

def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def send_tg_photo(caption, image_path):
    if not N_T or not N_I or not os.path.exists(image_path):
        return
    try:
        url = f"https://api.telegram.org/bot{N_T}/sendPhoto"
        with open(image_path, "rb") as f:
            requests.post(url, data={"chat_id": N_I, "caption": f"[Bot] {now_str()}\n{caption}"}, files={"photo": f}, timeout=30)
        print("TG photo sent")
    except Exception as e:
        print(f"TG send failed: {e}")

E_P_J = """
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

def get_t_c(sb):
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

def os_h_c(x, y):
    try:
        result = subprocess.run(["xdotool", "search", "--onlyvisible", "--class", "chrome"], capture_output=True, text=True)
        w_ids = result.stdout.strip().split('\n')
        if w_ids and w_ids[0]:
            subprocess.run(["xdotool", "windowactivate", w_ids[0]], stderr=subprocess.DEVNULL)
            time.sleep(0.2)
        
        os.system(f"xdotool mousemove {int(x)} {int(y)} click 1")
        print(f"xdotool clicked {x} {y}")
        return True
    except Exception as e:
        print(f"xdotool failed: {e}")
        return False

def main():
    if not A or not P:
        print("Missing credentials")
        sys.exit(1)

    print("Starting SB")
    opts = {
        "uc": True, 
        "test": True, 
        "headless": False, 
        "locale": "en", 
        "chromium_arg": "--disable-dev-shm-usage,--no-sandbox,--start-maximized"
    }
    if berry_PROXY_NODE:
        opts["proxy"] = berry_PROXY_NODE
        print("Using proxy: ***")

    with SB(**opts) as sb:
        sb.set_window_rect(0, 0, 1280, 720)
        
        try:
            print("Visiting URL")
            sb.uc_open_with_reconnect(T_U, reconnect_time=6)
            time.sleep(5)

            if "projects" in sb.get_current_url():
                print("Already logged in")
            else:
                print("Parsing form")
                user_sel = 'input[type="email"], input[name="email"], input[name="username"], input[type="text"]'
                sb.wait_for_element(user_sel, timeout=30)
                
                print("Filling credentials")
                sb.type(user_sel, A)
                sb.type('input[type="password"], input[name="password"]', P)
                
                print("Processing CF")
                time.sleep(3)
                sb.execute_script(E_P_J)
                time.sleep(1)

                for attempt in range(4):
                    is_done = sb.execute_script("var cf = document.querySelector(\"input[name='cf-turnstile-response']\"); return cf && cf.value.length > 20;")
                    if is_done:
                        print("CF passed")
                        break
                    
                    print(f"Verify attempt {attempt + 1}")
                    try:
                        sb.uc_gui_click_captcha()
                        print("Triggered native click")
                        time.sleep(5)
                    except Exception:
                        coords = get_t_c(sb)
                        if coords:
                            os_h_c(coords['x'], coords['y'])
                            print("Waiting 5s for animation")
                            time.sleep(5)
                        else:
                            print("Shield not found, retrying")
                            time.sleep(3)

                print("Submitting login")
                sb.click('button[type="submit"], button:contains("Login")')
                
                print("Waiting for redirect")
                time.sleep(10)
                
                if "projects" not in sb.get_current_url():
                    print("URL unchanged")
                    sb.uc_open_with_reconnect(D_U, reconnect_time=5)
                    time.sleep(5)

            print("Waiting for load")
            sb.sleep(8) 
            
            too_early_sel = "//div[contains(., 'Renewal will be available 3 days before Expiration')]"
            if sb.is_element_visible(too_early_sel):
                print("Early renewal not needed")
                shot_path = "renew_not_needed.png"
                sb.save_screenshot(shot_path)
                send_tg_photo("Early renewal not needed", shot_path)
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
                        print("Found renew button")
                        sb.click(sel)
                        found_btn = True
                        break
                
                if found_btn:
                    print("Waiting 10s")
                    sb.sleep(10)
                    
                    expire_time_text = "Unknown"
                    try:
                        expire_element = sb.wait_for_element('//*[contains(text(), "Expire")]/..', timeout=5)
                        expire_time_text = expire_element.text.replace('\n', ' ').strip()
                        print(f"Time left: {expire_time_text}")
                    except Exception:
                        print("Time left text not found")

                    shot_path = "renew_success.png"
                    sb.save_screenshot(shot_path)
                    
                    tg_msg = f"Renew clicked!\nStatus: {expire_time_text}"
                    send_tg_photo(tg_msg, shot_path)
                else:
                    print("Renew button not found")
                    shot_path = "renew_error.png"
                    sb.save_screenshot(shot_path)
                    send_tg_photo("Renew button not found", shot_path)

        except Exception as e:
            print(f"Error: {e}")
            sb.save_screenshot("error.png")
            send_tg_photo(f"Error: {e}", "error.png")
            sys.exit(1)

if __name__ == "__main__":
    main()
