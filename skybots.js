// skybots.js - 终极修复版 (对付 CF 盾精准点击)
const { chromium } = require('playwright-extra'); 
const stealth = require('puppeteer-extra-plugin-stealth')(); 
chromium.use(stealth); 

const fs = require('fs');
const path = require('path');
const https = require('https');

// ================= 配置区 =================
const TARGET_URL = 'https://dash.skybots.tech/login';
const DASHBOARD_URL = 'https://dash.skybots.tech/projects'; 
const STATE_FILE = path.join(__dirname, 'auth_state.json');

const ACCOUNT = process.env.SKYBOTS_ACCOUNT || '';
const PASSWORD = process.env.SKYBOTS_PASSWORD || '';
const PROXY_SERVER = process.env.PROXY_URL || '';

const TG_TOKEN = process.env.TG_BOT_TOKEN || '';
const TG_CHAT_ID = process.env.TG_CHAT_ID || '';

// ================= 辅助函数 =================
function nowStr() {
    return new Date().toLocaleString('zh-CN', {
        timeZone: 'Asia/Tokyo',
        hour12: false,
        year: 'numeric', month: '2-digit', day: '2-digit',
        hour: '2-digit', minute: '2-digit', second: '2-digit',
    }).replace(/\//g, '-');
}

function sendTGPhoto(caption, imagePath) {
    return new Promise((resolve) => {
        if (!TG_TOKEN || !TG_CHAT_ID || !fs.existsSync(imagePath)) {
            console.log('⚠️ TG配置未完成或图片不存在，跳过发送图片。');
            return resolve();
        }

        const boundary = '----PlaywrightBoundary' + Math.random().toString(16).slice(2);
        const fileName = path.basename(imagePath);
        const fileContent = fs.readFileSync(imagePath);
        const finalCaption = `[🤖 Skybots] ${nowStr()}\n${caption}`;

        const postData = Buffer.concat([
            Buffer.from(`--${boundary}\r\nContent-Disposition: form-data; name="chat_id"\r\n\r\n${TG_CHAT_ID}\r\n`),
            Buffer.from(`--${boundary}\r\nContent-Disposition: form-data; name="caption"\r\n\r\n${finalCaption}\r\n`),
            Buffer.from(`--${boundary}\r\nContent-Disposition: form-data; name="photo"; filename="${fileName}"\r\nContent-Type: image/png\r\n\r\n`),
            fileContent,
            Buffer.from(`\r\n--${boundary}--\r\n`)
        ]);

        const options = {
            hostname: 'api.telegram.org',
            port: 443,
            path: `/bot${TG_TOKEN}/sendPhoto`,
            method: 'POST',
            headers: {
                'Content-Type': `multipart/form-data; boundary=${boundary}`,
                'Content-Length': postData.length,
            },
            timeout: 20000 
        };

        const req = https.request(options, (res) => {
            if (res.statusCode === 200) console.log('📨 TG 图片推送成功！');
            else console.log(`⚠️ TG 推送失败: HTTP ${res.statusCode}`);
            resolve();
        });

        req.on('error', (e) => {
            console.log(`❌ TG 推送异常: ${e.message}`);
            resolve(); 
        });
        req.on('timeout', () => {
            console.log('⏰ TG 推送超时，跳过。');
            req.destroy();
            resolve();
        });
        req.write(postData);
        req.end();
    });
}

// ================= 主逻辑 =================
async function main() {
    let proxyConfig = PROXY_SERVER ? { server: PROXY_SERVER } : undefined;
    
    console.log('🔧 启动带隐身插件的浏览器...');
    const browser = await chromium.launch({
        headless: false, 
        proxy: proxyConfig,
        args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-blink-features=AutomationControlled']
    });

    let contextOptions = {
        viewport: { width: 1280, height: 720 },
        userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36' 
    };
    
    if (fs.existsSync(STATE_FILE)) {
        console.log('📂 发现历史会话文件，加载状态...');
        contextOptions.storageState = STATE_FILE;
    }

    const context = await browser.newContext(contextOptions);
    const page = await context.newPage();
    page.setDefaultTimeout(60000); 

    try {
        console.log(`🌐 访问目标网页: ${TARGET_URL}`);
        await page.goto(TARGET_URL, { waitUntil: 'load' });
        await page.waitForTimeout(5000); 
        
        if (page.url().includes('projects')) {
            console.log('✅ 会话有效，免密登录成功，直接进入 Projects 页面！');
        } else {
            console.log('🛡️ 正在解析登录页面...');
            const accountInput = page.locator('input[type="email"], input[name="email"], input[name="username"], input[type="text"]').first();
            await accountInput.waitFor({ state: 'visible', timeout: 30000 });
            console.log('✅ 登录表单已加载！');

            if (!ACCOUNT || !PASSWORD) throw new Error('❌ 未配置 SKYBOTS secrets');

            console.log('✏️ 填写账号密码...');
            await accountInput.fill(ACCOUNT);
            await page.locator('input[type="password"], input[name="password"]').first().fill(PASSWORD);
            
            // 👈 终极 CF 盾爆破逻辑：无视名字，只看尺寸，精确点击左侧
            console.log('🛡️ 寻找并尝试点击 Cloudflare 验证框...');
            await page.waitForTimeout(4000); // 等盾彻底渲染

            let cfClicked = false;
            try {
                // 获取页面上所有的 iframe
                const iframes = page.locator('iframe');
                const iframeCount = await iframes.count();
                console.log(`🔍 页面上共发现了 ${iframeCount} 个 iframe`);

                for (let i = 0; i < iframeCount; i++) {
                    const frame = iframes.nth(i);
                    const box = await frame.boundingBox();
                    
                    // CF 盾通常是一个长方形，宽度大于 250，高度大约 65
                    if (box && box.width > 200 && box.height > 40) {
                        console.log(`👆 锁定疑似 CF 验证盾 (宽:${box.width}, 高:${box.height})`);
                        
                        // 【核心玄学】点方块！不要点中心！
                        // 盾的打钩框固定在左侧。我们往左偏移，点在 x坐标 + 30 像素的位置
                        const targetX = box.x + 30;
                        const targetY = box.y + (box.height / 2);
                        
                        // 模拟人类滑动鼠标并点击
                        await page.mouse.move(targetX, targetY, { steps: 10 });
                        await page.waitForTimeout(500);
                        await page.mouse.click(targetX, targetY);
                        
                        cfClicked = true;
                        console.log('⏳ 已精确点击盾的最左侧，等待验证动画 (8秒)...');
                        await page.waitForTimeout(8000); 
                        break; // 点中一个就跳出循环
                    }
                }

                if (!cfClicked) {
                    console.log('⚠️ 没找到符合尺寸的盾，直接盲交试试...');
                }
            } catch (e) {
                console.log('⚠️ CF 处理模块报错: ' + e.message);
            }

            console.log('📤 提交登录请求...');
            await page.locator('button[type="submit"], button:has-text("Se connecter"), button:has-text("Login")').first().click();

            console.log('⏳ 等待页面跳转确认登录成功...');
            await page.waitForURL(/projects/, { timeout: 20000 });
            console.log(`✅ 登录成功！当前页面: ${page.url()}`);
            
            console.log('💾 保存最新会话状态...');
            await context.storageState({ path: STATE_FILE });
        }

        // ==========================================
        // 👇 核心业务逻辑 (Projects 页面检测续期)
        // ==========================================
        console.log('🚀 开始执行续期检测逻辑...');
        await page.waitForLoadState('networkidle'); 
        await page.waitForTimeout(3000); 

        const renewBtn = page.locator('button:has-text("Renew"), a:has-text("Renew")').first();

        if (await renewBtn.isVisible()) {
            console.log('🔘 找到 "Renew" 续期按键，点击续期...');
            await renewBtn.click();
            console.log('✅ 按钮已点击，等待 10 秒后截图结果...');
            await page.waitForTimeout(10000);
            
            const shotPath = 'renew_success.png';
            await page.screenshot({ path: shotPath, fullPage: true });
            let capStr = '🎉 续期按钮已找到并点击！今日续期完成，请查看结果截图。';
            if (cfClicked) capStr += '\n(🛡️ 成功突破 Cloudflare 盾)';
            await sendTGPhoto(capStr, shotPath);
            console.log('🎉 续期流程处理完毕，已发送图片通知。');

        } else {
            console.log('⏰ 未找到 "Renew" 续期按键，今日可能无需续期。');
            const shotPath = 'renew_not_needed.png';
            await page.screenshot({ path: shotPath, fullPage: true });
            let capStr = '⏰ 今日暂无需续期 (未找到 Renew 按键)。';
            if (cfClicked) capStr += '\n(🛡️ 成功突破 Cloudflare 盾)';
            await sendTGPhoto(capStr, shotPath);
            console.log('⏰ 已发送暂无需续期通知。');
        }

    } catch (error) {
        console.error(`❌ 脚本执行异常: ${error.message}`);
        const errPath = 'skybots_error.png';
        await page.screenshot({ path: errPath, fullPage: true });
        await sendTGPhoto(`❌ 脚本运行出错了: ${error.message}`, errPath);
        throw error; 
    } finally {
        await context.close();
        await browser.close();
    }
}

main().catch(() => process.exit(1));
