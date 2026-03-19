// skybots.js
const { chromium } = require('playwright-extra'); // 👈 换成 extra 版本
const stealth = require('puppeteer-extra-plugin-stealth')(); // 👈 引入隐身插件
chromium.use(stealth); // 👈 挂载隐身插件

const fs = require('fs');
const path = require('path');

const TARGET_URL = 'https://dash.skybots.tech/login';
const DASHBOARD_URL = 'https://dash.skybots.tech/dashboard'; // 需确认实际后台 URL
const STATE_FILE = path.join(__dirname, 'auth_state.json');

const ACCOUNT = process.env.SKYBOTS_ACCOUNT || '';
const PASSWORD = process.env.SKYBOTS_PASSWORD || '';
const PROXY_SERVER = process.env.PROXY_URL || '';

async function main() {
    let proxyConfig = PROXY_SERVER ? { server: PROXY_SERVER } : undefined;
    
    console.log('🔧 启动带隐身插件的浏览器...');
    const browser = await chromium.launch({
        headless: false, // 👈 【关键】必须关闭无头模式，配合 xvfb 骗过 CF
        proxy: proxyConfig,
        args: [
            '--no-sandbox', 
            '--disable-setuid-sandbox',
            '--disable-blink-features=AutomationControlled' // 👈 进一步抹除自动化特征
        ]
    });

    let contextOptions = {
        viewport: { width: 1280, height: 720 },
        userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36' // 伪装成正常的 Windows Chrome
    };
    
    if (fs.existsSync(STATE_FILE)) {
        console.log('📂 发现历史会话文件，尝试免密加载...');
        contextOptions.storageState = STATE_FILE;
    }

    const context = await browser.newContext(contextOptions);
    const page = await context.newPage();
    page.setDefaultTimeout(45000); // CF 盾可能需要转好几秒，增加超时时间

    try {
        console.log(`🌐 访问目标网页: ${TARGET_URL}`);
        await page.goto(TARGET_URL, { waitUntil: 'domcontentloaded' });

        // 1. 判断是否已经免密登录
        await page.waitForTimeout(5000); // 稍微等一下页面重定向
        if (page.url().includes('dashboard') || page.url().includes('client')) {
            console.log('✅ 会话有效，已自动免密登录！');
        } else {
            console.log('🛡️ 等待突破 Cloudflare 盾...');
            
            // 👈 【关键】等待账号输入框出现，这意味着 CF 盾已经通过了！
            // CF 验证时，真正的登录表单是被隐藏的或者根本没加载
            const emailInput = page.locator('input[type="email"]');
            await emailInput.waitFor({ state: 'visible', timeout: 60000 });
            console.log('✅ CF盾穿透成功，登录表单已加载！');

            if (!ACCOUNT || !PASSWORD) throw new Error('❌ 未配置 SKYBOTS_ACCOUNT 或 PASSWORD');

            console.log('✏️ 填写账号密码...');
            await emailInput.fill(ACCOUNT);
            await page.locator('input[type="password"]').fill(PASSWORD);
            await page.locator('button[type="submit"]').click();

            console.log('⏳ 等待页面跳转确认登录成功...');
            await page.waitForURL(/dashboard|client/, { timeout: 20000 });
            console.log('✅ 登录成功！');
            
            console.log('💾 保存最新会话状态到本地...');
            await context.storageState({ path: STATE_FILE });
        }

        // ==========================================
        // 👇 2. 你的点击续期逻辑写在这里
        // ==========================================
        console.log('🚀 开始执行核心业务逻辑...');
        
        console.log('🎉 Skybots 脚本全部执行完毕！');

    } catch (error) {
        console.error(`❌ 脚本执行异常: ${error.message}`);
        await page.screenshot({ path: 'skybots_error.png', fullPage: true });
        throw error;
    } finally {
        await context.close();
        await browser.close();
    }
}

main().catch(() => process.exit(1));
