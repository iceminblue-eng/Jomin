const path='/tmp/claude-0/-home-user-Jomin/642bf304-874b-5bc9-ac13-1449b17918c6/scratchpad';
(async () => {
  let pw;
  try { pw = require(path+'/node_modules/playwright'); }
  catch(e) { pw = require('playwright'); }
  const browser = await pw.chromium.launch({executablePath:'/opt/pw-browsers/chromium-1194/chrome-linux/chrome', args:['--no-sandbox','--font-render-hinting=none']});
  const page = await browser.newPage();
  await page.goto('file:///home/user/Jomin/build/관리자론-헤어살롱편-인쇄.html',
                  {waitUntil:'load', timeout:180000});
  await page.evaluate(() => document.fonts.ready);
  await page.pdf({path:'/home/user/Jomin/build/관리자론-헤어살롱편.pdf',
                  format:'A4', printBackground:true,
                  margin:{top:'22mm',bottom:'20mm',left:'20mm',right:'20mm'},
                  displayHeaderFooter:true,
                  headerTemplate:'<div style="font-size:7pt;color:#999;width:100%;text-align:right;padding-right:20mm;font-family:sans-serif">관리자론 — 헤어살롱 편</div>',
                  footerTemplate:'<div style="font-size:8pt;color:#999;width:100%;text-align:center;font-family:sans-serif"><span class="pageNumber"></span></div>'});
  await browser.close();
  console.log('pdf done');
})().catch(e=>{console.error('ERR', e.message); process.exit(1);});
