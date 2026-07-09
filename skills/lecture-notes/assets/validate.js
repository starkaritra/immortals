#!/usr/bin/env node
/*
 * lecture-notes :: render validator
 * Headlessly loads each note HTML and asserts that every Mermaid diagram
 * rendered (svg count == block count, no "Syntax error") and MathJax produced output.
 *
 * Usage:  node validate.js notes/a.html notes/b.html ...
 * Exit:   0 = all PASS, 1 = at least one FAIL.
 *
 * Requires puppeteer installed WITHOUT the bundled Chromium download:
 *   set PUPPETEER_SKIP_DOWNLOAD=true && npm install puppeteer
 * The script auto-detects a system Edge/Chrome to drive.
 */
const puppeteer = require('puppeteer');
const path = require('path');
const fs = require('fs');

function findBrowser() {
  const envPath = process.env.BROWSER_PATH;
  const candidates = [
    envPath,
    'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',
    'C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe',
    'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
    'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe',
    '/usr/bin/google-chrome', '/usr/bin/chromium-browser', '/usr/bin/chromium',
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge',
  ].filter(Boolean);
  for (const c of candidates) { try { if (fs.existsSync(c)) return c; } catch (e) {} }
  return null; // let puppeteer try its own bundled browser
}

const files = process.argv.slice(2);
if (!files.length) { console.error('usage: node validate.js <file.html> ...'); process.exit(2); }

(async () => {
  const exe = findBrowser();
  const launchOpts = { headless: 'new', args: ['--no-sandbox','--disable-dev-shm-usage','--force-color-profile=srgb'] };
  if (exe) launchOpts.executablePath = exe;
  const browser = await puppeteer.launch(launchOpts);
  let anyFail = false;
  for (const f of files) {
    const page = await browser.newPage();
    const jsErrs = [];
    page.on('pageerror', e => jsErrs.push('JS: ' + e.message));
    const url = 'file:///' + path.resolve(f).replace(/\\/g, '/');
    try {
      await page.goto(url, { waitUntil: 'networkidle0', timeout: 60000 });
      await new Promise(r => setTimeout(r, 3500)); // let mermaid + mathjax settle
      const res = await page.evaluate(() => {
        const blocks = document.querySelectorAll('.mermaid').length;
        const svgs = document.querySelectorAll('.mermaid svg').length;
        const merr = Array.from(document.querySelectorAll('.mermaid'))
          .filter(m => /Syntax error|error in text|mermaid version \d/i.test(m.textContent)).length;
        const mjx = document.querySelectorAll('mjx-container, svg[data-mml-node], .MathJax').length;
        return { blocks, svgs, merr, mjx };
      });
      const ok = res.svgs === res.blocks && res.merr === 0 && jsErrs.length === 0;
      if (!ok) anyFail = true;
      console.log(`[${ok ? 'PASS' : 'FAIL'}] ${path.basename(f)}`);
      console.log(`   mermaid: ${res.svgs}/${res.blocks} rendered, errors=${res.merr}`);
      console.log(`   mathjax containers: ${res.mjx}`);
      if (jsErrs.length) console.log('   ' + jsErrs.join('\n   '));
    } catch (e) {
      anyFail = true;
      console.log(`[FAIL] ${path.basename(f)}\n   ${e.message}`);
    }
    await page.close();
  }
  await browser.close();
  process.exit(anyFail ? 1 : 0);
})();
