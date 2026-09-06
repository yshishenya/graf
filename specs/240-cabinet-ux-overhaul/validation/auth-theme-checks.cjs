const {chromium,webkit}=require('playwright');const fs=require('node:fs');
const base=process.env.GRAF_QA_BASE_URL || 'http://127.0.0.1:8879';
if(new URL(base).hostname!=='127.0.0.1')throw Error('synthetic loopback only');
(async()=>{for(const [engine,bt] of [['chrome',chromium],['webkit',webkit]]){const b=await bt.launch(engine==='chrome'?{channel:'chrome'}:{});const p=await b.newPage({reducedMotion:'reduce'});let count=0;
for(const width of [320,390,768,1024,1440])for(const scheme of ['light','dark'])for(const path of ['/qa/referral/active','/qa/referral/unavailable','/qa/referral/invalid','/qa/auth/login','/qa/auth/signup-email','/qa/auth/code']){
 await p.setViewportSize({width,height:812});await p.emulateMedia({colorScheme:scheme});await p.goto(base+path);
 await p.waitForFunction(()=>[...document.querySelectorAll('.auth-form > :not(input[type="hidden"])')].every(e=>Number(getComputedStyle(e).opacity)===1));
 const r=await p.evaluate(()=>{const panel=document.querySelector('.auth-panel')?.getBoundingClientRect();const legal=document.querySelector('.auth-legal')?.getBoundingClientRect();return {w:document.documentElement.scrollWidth,iw:innerWidth,overlap:panel&&legal&&panel.bottom>legal.top};});if(r.w>width+1||r.overlap)throw Error(JSON.stringify({engine,width,scheme,path,r}));count++;
 if(width===390&&scheme==='light'&&engine==='chrome'){fs.mkdirSync('.dev/release/screenshots',{recursive:true});await p.screenshot({path:'.dev/release/screenshots/final-'+path.split('/').pop()+'.png',fullPage:true});}
}
for(const theme of ['light','dark','system']){
 await p.goto(base+'/meetings?theme='+theme);const colors=[];for(const scheme of ['light','dark','light']){await p.emulateMedia({colorScheme:scheme});await p.evaluate(()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r))));colors.push(await p.evaluate(()=>getComputedStyle(document.body).backgroundColor));}
 if(theme==='system'?colors[0]===colors[1]||colors[0]!==colors[2]:new Set(colors).size!==1)throw Error('dynamic theme '+JSON.stringify({theme,colors}));count++;
}console.log(engine,count,'PASS');await b.close();}})().catch(e=>{console.error(e);process.exit(1)});
