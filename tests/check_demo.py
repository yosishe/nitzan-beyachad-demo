"""Smoke test the exact export: vertical profiles and resident-to-resident arrows."""
import argparse
from pathlib import Path
import hashlib
import json
from playwright.sync_api import sync_playwright

parser=argparse.ArgumentParser()
parser.add_argument('--url',default='http://127.0.0.1:8000')
parser.add_argument('--engine',choices=['chromium','webkit'],default='chromium')
parser.add_argument('--browser-channel')
parser.add_argument('--executable')
args=parser.parse_args()
root=Path(__file__).resolve().parents[1]
for asset in json.loads((root/'SOURCE.json').read_text())['files']:
 assert hashlib.sha256((root/asset['path']).read_bytes()).hexdigest()==asset['sha256'],asset['path']

with sync_playwright() as w:
 options={}
 if args.browser_channel:options['channel']=args.browser_channel
 if args.executable:options['executable_path']=args.executable
 browser=getattr(w,args.engine).launch(**options)
 p=browser.new_page(viewport={'width':390,'height':844})
 p.set_default_timeout(10000)
 errors=[];failed=[]
 p.on('pageerror',lambda e:errors.append(str(e)))
 p.on('requestfailed',lambda r:failed.append(r.url))
 def start(route='profiles'):
  p.goto('about:blank');response=p.goto(args.url.rstrip('/')+'/#'+route)
  assert response.status==200
  p.evaluate('document.fonts.ready')
 for width,height in ((390,844),(320,693)):
  p.set_viewport_size({'width':width,'height':height});start()
  first=p.evaluate('browseId');requests=p.evaluate('db.requests.length')
  assert p.locator('.scroll-person-prev').is_disabled()
  assert p.locator('.scroll-story').evaluate('e=>e.scrollHeight>e.clientHeight')
  p.locator('.scroll-story').evaluate('e=>e.scrollTop=350')
  assert p.evaluate('browseId')==first
  p.locator('.scroll-person-next').click();assert p.evaluate('browseId')!=first
  p.locator('.scroll-person-prev').click();assert p.evaluate('browseId')==first
  assert p.evaluate('db.requests.length')==requests
  p.locator('.scroll-photo [data-act=expandProfilePhoto]').nth(1).click()
  assert p.locator('.photo-viewer').is_visible()
  assert p.locator('.photo-viewer img').evaluate('e=>e.currentSrc||e.src')==p.locator('.scroll-photo>img').nth(1).evaluate('e=>e.currentSrc||e.src')
  p.keyboard.press('Escape');assert not p.locator('#dialog').is_visible()
  p.locator('[data-act=likeProfile]').click();assert 'לייק בלי הודעה' in p.locator('#dialog').inner_text();p.keyboard.press('Escape')
  p.locator('[data-act=ask]').click();assert 'הודעה' in p.locator('#dialog').inner_text();p.keyboard.press('Escape')
  assert p.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
 start('requests');p.locator('[data-act=senderProfile]').first.click()
 assert p.locator('.scroll-deck').count()==1
 p.locator('[data-act=backToRequest]').click();assert p.evaluate("page==='requests'")
 start('chats');p.evaluate("openChat('ron')");p.locator('#msg').fill('טיוטה לבדיקה')
 p.locator('[data-act=viewChatProfile]').click();p.locator('[data-act=backToChat]').click()
 assert p.locator('#msg').input_value()=='טיוטה לבדיקה'
 for route,role in [('worker-mobile','worker'),('admin-mobile','admin')]:
  start(route);assert p.evaluate('role')==role and p.locator('#screen').inner_text().strip()
 assert not errors,errors
 assert not failed,failed
 browser.close()
print('PASS:',args.engine,'assets, profile arrows, scrolling, photos, requests, chat drafts and staff roles')
