const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

async function captureScreenshots() {
  const screenshotsDir = path.join(__dirname, '..', 'docs', 'screenshots');
  if (!fs.existsSync(screenshotsDir)) {
    fs.mkdirSync(screenshotsDir, { recursive: true });
  }

  console.log('Launching headless Chromium browser...');
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    deviceScaleFactor: 2, // Retina resolution for crisp screenshots
  });
  const page = await context.newPage();

  console.log('Navigating to http://localhost...');
  await page.goto('http://localhost', { waitUntil: 'networkidle' });
  await page.waitForTimeout(2000);

  // 1. Market Overview
  console.log('Capturing 01_market_overview.png...');
  await page.screenshot({
    path: path.join(screenshotsDir, '01_market_overview.png'),
    fullPage: false,
  });

  // 2. Parity Radar
  console.log('Navigating to Parity Radar...');
  await page.click('button:has-text("Parity Radar")');
  await page.waitForTimeout(1500);
  console.log('Capturing 02_parity_radar.png...');
  await page.screenshot({
    path: path.join(screenshotsDir, '02_parity_radar.png'),
    fullPage: false,
  });

  // 3. Signals (with Cost Autopsy opened)
  console.log('Navigating to Relative-Value Signals...');
  await page.click('button:has-text("Relative-Value Signals")');
  await page.waitForTimeout(1500);
  // Expand first Cost Autopsy drawer
  const autopsyBtn = await page.$('button:has-text("Inspect Cost Autopsy")');
  if (autopsyBtn) {
    await autopsyBtn.click();
    await page.waitForTimeout(1000);
  }
  console.log('Capturing 03_signals_cost_autopsy.png...');
  await page.screenshot({
    path: path.join(screenshotsDir, '03_signals_cost_autopsy.png'),
    fullPage: false,
  });

  // 4. Backtest Engine
  console.log('Navigating to Backtest Engine...');
  await page.click('button:has-text("Backtest Engine")');
  await page.waitForTimeout(1500);
  console.log('Capturing 04_backtest_engine.png...');
  await page.screenshot({
    path: path.join(screenshotsDir, '04_backtest_engine.png'),
    fullPage: false,
  });

  // 5. Contract Lifecycle
  console.log('Navigating to Contract Lifecycle...');
  await page.click('button:has-text("Contract Lifecycle")');
  await page.waitForTimeout(1500);
  console.log('Capturing 05_contract_lifecycle.png...');
  await page.screenshot({
    path: path.join(screenshotsDir, '05_contract_lifecycle.png'),
    fullPage: false,
  });

  // 6. System & Data Health
  console.log('Navigating to System & Data Health...');
  await page.click('button:has-text("System & Data Health")');
  await page.waitForTimeout(1500);
  console.log('Capturing 06_system_status.png...');
  await page.screenshot({
    path: path.join(screenshotsDir, '06_system_status.png'),
    fullPage: false,
  });

  await browser.close();
  console.log('All 6 screenshots captured successfully in docs/screenshots/!');
}

captureScreenshots().catch((err) => {
  console.error('Screenshot capture failed:', err);
  process.exit(1);
});
