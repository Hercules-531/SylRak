import {chromium} from 'playwright';
import {readFile,writeFile} from 'node:fs/promises';
import assert from 'node:assert/strict';
const base='http://127.0.0.1:8010';
const browser=await chromium.launch({channel:'chrome',headless:true});
const context=await browser.newContext({viewport:{width:1440,height:900}});
const page=await context.newPage(),errors=[];
page.on('pageerror',e=>errors.push(e.message));
const get=async path=>(await context.request.get(base+'/api/v1'+path)).json();
try{
 const before=await get('/jev/status');
 await page.goto(base+'/appearance');
 await page.locator('.jev-assistant summary').click();
 await page.getByLabel('Jev vehicle description').fill('A white Creta with a black roof, a red door panel and a roof rack');
 await page.getByRole('button',{name:'Search with Jev'}).click();
 await page.getByText('Search complete using saved Jev filters · results below').waitFor();
 assert.equal(await page.getByLabel('Appearance model').inputValue(),'Hyundai Creta');
 await page.locator('.candidate-card').first().waitFor();
 assert.ok((await page.locator('.candidate-card').first().textContent()).includes('DL4CAB6672'));
 await page.screenshot({path:'artifacts/qa/jev-search-1440.png',fullPage:true});
 assert.equal((await get('/jev/status')).requests,before.requests,'Cached demonstration must not spend a new request');
 await page.reload();
 assert.equal((await get('/jev/status')).requests,before.requests,'Reload must not call Jev');
 await page.setViewportSize({width:1366,height:768});
 await page.locator('.jev-assistant summary').click();
 // Test the graceful unavailable state without making any external request.
 await page.route('**/api/v1/jev/describe',r=>r.fulfill({status:503,contentType:'application/json',body:JSON.stringify({detail:'Jev is unavailable. Use the manual filters.'})}));
 await page.getByLabel('Jev vehicle description').fill('A covered blue vehicle');
 await page.getByRole('button',{name:'Search with Jev'}).click();
 await page.getByRole('alert').filter({hasText:'Jev is unavailable'}).waitFor();
 await page.getByRole('button',{name:'White Dzires',exact:true}).click();
 await page.locator('.candidate-card').first().waitFor();
 assert.ok(await page.locator('.candidate-card').count()>=5);
 assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
 assert.deepEqual(errors,[]);
 await writeFile('artifacts/qa/jev-browser-results.json',JSON.stringify({passed:true,checks:['Cached real Jev response populates editable filters','Multicolor candidate found','Reload and repeat consume zero online requests','Unavailable Jev leaves manual search usable','1366px layout and browser errors checked'],errors},null,2));
 console.log('Jev browser workflow passed. No additional online requests.');
}finally{await browser.close()}
