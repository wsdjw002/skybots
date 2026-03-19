// skybots.js
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const TARGET_URL = 'https://dash.skybots.tech/login';
const DASHBOARD_URL = 'https://dash.skybots.tech/dashboard'; // 👈 替换为登录成功后的实际 URL 路径
const STATE_FILE = path.join(__dirname, 'auth_state.json');

const ACCOUNT = process.env.SKYBOTS_ACCOUNT || '';
const PASSWORD = process.env.SKYBOTS_PASSWORD || '';
const PROXY_SERVER = process.env.PROXY_URL || '';

async function main() {
    let proxyConfig = PROXY_SERVER ? { server: PROXY_SERVER } : undefined;
    
    console.log('🔧 启动浏览器...');
    const browser = await chromium.launch({
        headless: true, // 调试阶段可以在本地改成 false 看看网页长啥样
        proxy: proxyConfig,
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    });

    let contextOptions = {};
    if (fs.existsSync(STATE_FILE)) {
        console.log('📂 发现历史会话文件，尝试免密加载...');
        contextOptions.storageState = STATE_FILE;
    }

    const context = await browser.newContext(contextOptions);
    const page = await context.newPage();
    page.setDefaultTimeout(30000);

    try {
        console.log(`🌐 访问目标网页: ${TARGET_URL}`);
        await page.goto(TARGET_URL, { waitUntil: 'domcontentloaded' });
        await page.waitForTimeout(3000);

        // 1. 判断是否已经处于登录状态 (可能是 Cookie 生效直接跳仪表盘了)
        // 这里的 include 逻辑请根据实际情况微调
        if (page.url().includes('dashboard') || page.url().includes('client')) {
            console.log('✅ 会话有效，已自动免密登录！');
        } else {
            console.log('⚠️ 需要登录，执行常规账号密码流程...');
            
            if (!ACCOUNT || !PASSWORD) throw new Error('❌ 未配置 SKYBOTS_ACCOUNT 或 PASSWORD');

            // 👇 ---- 注意：以下选择器需要你根据真实网页进行替换 ---- 👇
            await page.fill('input[type="email"]', ACCOUNT);       // 账号输入框
            await page.fill('input[type="password"]', PASSWORD);   // 密码输入框
            await page.click('button[type="submit"]');             // 登录按钮
            // 👆 -------------------------------------------------------- 👆

            console.log('⏳ 等待页面跳转确认登录成功...');
            // 等待 URL 发生变化，证明进入了后台
            await page.waitForURL(/dashboard|client/, { timeout: 15000 });
            console.log('✅ 登录成功！');
            
            // 登录成功后，立刻将 Cookie 和 LocalStorage 固化保存
            console.log('💾 保存最新会话状态到本地...');
            await context.storageState({ path: STATE_FILE });
        }

        // ==========================================
        // 👇 2. 在这里补充你登录后需要点击的“续期/保活”逻辑
        // ==========================================
        console.log('🚀 开始执行保活/续期逻辑...');
        // await page.click('button:has-text("Renew")');
        // ...
        
        console.log('🎉 Skybots 脚本全部执行完毕！');

    } catch (error) {
        console.error(`❌ 脚本执行异常: ${error.message}`);
        // 报错时立刻截图，方便在 Actions 里定位是卡在了验证码还是元素没找到
        await page.screenshot({ path: 'skybots_error.png', fullPage: true });
        throw error;
    } finally {
        await context.close();
        await browser.close();
    }
}

main().catch(() => process.exit(1));
