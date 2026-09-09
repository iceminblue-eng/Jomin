const path='/tmp/claude-0/-home-user-Jomin/642bf304-874b-5bc9-ac13-1449b17918c6/scratchpad';
const TITLES={1:'관리자론 1 — 기준과 진단',2:'관리자론 2 — 권한과 운영',3:'관리자론 3 — 확장과 양성'};
(async () => {
  const pw = require(path+'/node_modules/playwright');
  const browser = await pw.chromium.launch({executablePath:'/opt/pw-browsers/chromium-1194/chrome-linux/chrome',
    args:['--no-sandbox','--font-render-hinting=none']});
  for (const v of [1,2,3]) {
    const page = await browser.newPage();
    await page.goto('file:///home/user/Jomin/build/'+v+'권/인쇄.html',{waitUntil:'load',timeout:180000});
    await page.evaluate(() => document.fonts.ready);
    await page.pdf({path:'/home/user/Jomin/build/'+v+'권/관리자론-'+v+'.pdf',
      format:'A4', printBackground:true,
      margin:{top:'22mm',bottom:'20mm',left:'20mm',right:'20mm'},
      displayHeaderFooter:true,
      headerTemplate:'<div style="font-size:7pt;color:#999;width:100%;text-align:right;padding-right:20mm;font-family:sans-serif">'+TITLES[v]+'</div>',
      footerTemplate:'<div style="font-size:8pt;color:#999;width:100%;text-align:center;font-family:sans-serif"><span class="pageNumber"></span></div>'});
    await page.close();
    console.log('  '+v+'권 PDF 완료');
  }
  await browser.close();
})().catch(e=>{console.error('ERR', e.message); process.exit(1);});
