const assert = require('node:assert/strict');
const path = require('node:path');
const http = require('node:http');
const fs = require('node:fs');
const {chromium, webkit} = require(require.resolve('playwright', {paths:[process.env.GRAF_NODE_MODULES || process.cwd()]}));
const script = path.join(__dirname, '../../src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js');
const shared = '/shared-meetings/20000000-0000-0000-0000-000000000001?workspace_id=20000000-0000-0000-0000-000000000002';
(async () => {
  let nextTarget;
  const server = http.createServer((req,res) => {
    if(req.url.startsWith('/shared-meetings/')) {
      res.writeHead(303,{location:'/login?'+new URLSearchParams({next:nextTarget})});return res.end();
    }
        res.setHeader('content-type','text/html');
    res.end('<main class="auth-page"><form class="auth-form"><input name="next" type="hidden"></form><a id="oauth">Provider</a><a id="back">Back</a><a id="signup">Signup</a><a id="verify">Verify</a><a id="resend">Resend</a><a id="foreign">Foreign</a><a id="plain" href="/privacy">Privacy</a></main>');
  });
  await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
  const origin='http://127.0.0.1:'+server.address().port;
  const browser = await (process.env.GRAF_BROWSER === 'webkit' ? webkit : chromium).launch();
  try {
    for (const [fragment, next, expected] of [
      ['#recording?position_ms=15000', shared, shared+'#recording?position_ms=15000'],
      ['#recording?position_ms=0', shared, shared+'#recording?position_ms=0'],
      ['#recording?position_ms=86400000', shared, shared+'#recording?position_ms=86400000'],
      ['#outcomes', shared, shared+'#outcomes'],
      ['#recording', shared, shared+'#recording'],
      ['#recording?position_ms=86400001', shared, shared],
      ['#recording?position_ms=-1', shared, shared],
      ['#recording?position_ms=15&next=https://evil.test', shared, shared],
      ['#outcomes', shared+'#recording?position_ms=1000', shared+'#recording?position_ms=1000'],
      ['#recording?position_ms=15000', '/meetings', '/meetings'],
      ['#outcomes', 'https://evil.test'+shared, 'https://evil.test'+shared],
      ['#outcomes', '//evil.test'+shared, '//evil.test'+shared],
      ['#outcomes', 'http://[', 'http://['],
      ['#outcomes', '/shared-meetings/not-a-uuid', '/shared-meetings/not-a-uuid'],
    ]) {
      const page = await browser.newPage({reducedMotion:'reduce'});
      const errors=[];page.on('pageerror',e=>errors.push(e.message));
      nextTarget=next;
      await page.goto(origin+shared+fragment);
      assert.equal(new URL(page.url()).hash,fragment,'The real browser must inherit the fragment through the login redirect');
      await page.locator('input[name=next]').evaluate((el,value)=>{el.value=value;},next);
      for(const [id,href] of [['oauth','/login/yandex/start'],['back','/login'],['signup','/sign-up'],['verify','/login/email/verify'],['resend','/login/email/resend'],['foreign','https://evil.test/login']]) {
        await page.locator('#'+id).evaluate((el,args)=>{el.href=args.href+'?'+new URLSearchParams({next:args.next});},{href,next});
      }
      await page.addScriptTag({path:script});
      assert.equal(await page.locator('input[name=next]').inputValue(),expected);
      for(const id of ['oauth','back','signup','verify','resend']) assert.equal(new URL(await page.locator('#'+id).getAttribute('href'),origin).searchParams.get('next'),expected);
      assert.equal(new URL(await page.locator('#foreign').getAttribute('href')).searchParams.get('next'),next);
      assert.equal(await page.locator('#plain').getAttribute('href'),'/privacy');
      assert.deepEqual(errors,[]);await page.close();
    }
    console.log('Addressed shared login: inherited context, email/OAuth/back, bounds and same-origin14 PASS');
  } finally {await browser.close();await new Promise(resolve=>server.close(resolve));}
})().catch(error=>{console.error(error);process.exitCode=1;});
