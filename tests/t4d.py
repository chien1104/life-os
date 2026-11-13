from playwright.sync_api import sync_playwright
import os, json, datetime
from pathlib import Path
HERE=Path(__file__).resolve().parent; OUT=HERE/'out'; OUT.mkdir(exist_ok=True)
URL='file://'+os.path.abspath('/home/claude/生活整理工具箱.html')
R=[]
def ok(n,c,extra=""): R.append(("PASS" if c else "FAIL")+"  "+n+(("  ["+str(extra)+"]") if (extra!="" and not c) else ""))
# 固定「今天」= 2026-11-13（星期五）台北時間 10:00
T0=datetime.datetime(2026,11,13,10,0,0,tzinfo=datetime.timezone(datetime.timedelta(hours=8)))
old={"todos":[
  {"id":"a1","text":"舊的提案任務","cat":"工作","pri":"高","mins":60,"done":False,"created":1},
  {"id":"a2","text":"舊的 IG 腳本","cat":"內容創作","pri":"中","mins":30,"done":True,"created":2,"doneAt":1763000000000},
  {"id":"a3","text":"舊的低優先","cat":"生活","pri":"低","mins":30,"done":False,"created":3}],
 "results":[{"id":"r0","text":"舊的整理結果","cat":"學習","pri":"低","mins":30}],
 "plans":[{"id":"p0","date":"2026-11-12","energy":3,"mood":"平穩","hours":4,"tip":"舊提醒","blocks":[{"type":"task","id":"a1","text":"舊的提案任務","cat":"工作","start":540,"mins":60}],"later":[]}],
 "cards":[{"date":"2026-11-12","idx":5}],"draft":"舊草稿"}
with sync_playwright() as p:
    b=p.chromium.launch()
    ctx=b.new_context(viewport={'width':390,'height':844},device_scale_factor=2,timezone_id='Asia/Taipei',accept_downloads=True)
    pg=ctx.new_page(); errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)))
    pg.clock.install(time=T0)
    # 先寫入舊資料再開 App（模擬舊版使用者）
    pg.goto('about:blank'); pg.goto(URL.replace('生活整理工具箱.html','')) if False else None
    pg.goto(URL); pg.evaluate("d=>{localStorage.clear();localStorage.setItem('lifebox_v1',JSON.stringify(d))}", old); pg.wait_for_timeout(800); pg.reload(); pg.wait_for_timeout(300)
    st=lambda: pg.evaluate("JSON.parse(localStorage.getItem('lifebox_v1'))")
    bks=lambda: pg.evaluate("JSON.parse(localStorage.getItem('lifebox_v1_backups')||'[]')")
    s=st(); t={x['id']:x for x in s['todos']}
    # ---- 資料安全 ----
    ok("舊資料完整讀取（3 件待辦、1 整理、1 建議、1 抽卡、草稿）", len(s['todos'])==3 and len(s['results'])==1 and len(s['plans'])==1 and len(s['cards'])==1 and s['draft']=="舊草稿")
    ups=lambda: [b for b in bks() if '升級' in b['reason']]
    ok("升級前自動備份原始資料", len(ups())==1 and json.loads(ups()[0]['data'])==old)
    ok("資料版本標記為 5", s.get('schemaVersion')==5)
    ok("舊欄位保留（text/cat/pri/done/created）", all(k in t['a1'] for k in ['text','cat','pri','done','created']))
    ok("新欄位補齊（title/category/priority/scheduledDate/dueDate/createdAt/status/sortOrder/rolloverCount/rolloverHistory/updatedAt）", all(k in t['a1'] for k in ['title','category','priority','scheduledDate','dueDate','createdAt','completedAt','status','sortOrder','rolloverCount','rolloverHistory','updatedAt','description']))
    ok("舊任務安排在今天、建立時間不變", t['a1']['scheduledDate']=="2026-11-13" and t['a1']['createdAt']==1)
    ok("初始排序沿用舊畫面順序（未完成高→低，完成在後）", t['a1']['sortOrder']<t['a3']['sortOrder']<t['a2']['sortOrder'])
    pg.reload(); ok("重新整理不會再備份一次（升級備份 1 份、每日備份最多 1 份）", len(ups())==1 and len([b for b in bks() if '每日' in b['reason']])<=1)
    # ---- 首頁 ----
    ok("首頁只顯示今天的待辦（2 件）", pg.locator('#app .item').count()==2)
    pg.screenshot(path=str(OUT/'home.png'),full_page=True)
    # ---- 大量新增（規則判斷＋預覽確認） ----
    pg.click('[data-tab=collect]')
    ok("舊草稿仍在收集頁", pg.input_value('#captureInput')=="舊草稿")
    pg.fill('#captureInput','明天買生活用品、下週二剪影片、月底繳信用卡、找時間整理房間\n11/20前交提案')
    pg.wait_for_timeout(500); n_before=len(st()['todos'])
    pg.click('#btnOrganize')
    s=st(); res={r['text']:r for r in s['results']}
    ok("拆成 5 件 + 舊的 1 件預覽", len(s['results'])==6, len(s['results']))
    ok("「明天」→ 11/14", res.get('明天買生活用品',{}).get('scheduledDate')=="2026-11-14", res.get('明天買生活用品'))
    ok("「下週二」→ 11/17", res.get('下週二剪影片',{}).get('scheduledDate')=="2026-11-17")
    ok("「月底繳」→ 安排與截止都是 11/30", res.get('月底繳信用卡',{}).get('scheduledDate')=="2026-11-30" and res.get('月底繳信用卡',{}).get('dueDate')=="2026-11-30")
    ok("「找時間」判斷不出日期 → 預設今天", res.get('找時間整理房間',{}).get('scheduledDate')=="2026-11-13")
    ok("「11/20前」→ 今天開始、截止 11/20", res.get('11/20前交提案',{}).get('scheduledDate')=="2026-11-13" and res.get('11/20前交提案',{}).get('dueDate')=="2026-11-20")
    ok("預覽階段尚未寫入待辦", len(s['todos'])==n_before)
    pg.locator('input[data-f=scheduledDate]').nth(0).fill('2026-11-15'); pg.locator('input[data-f=scheduledDate]').nth(0).dispatch_event('change')
    ok("預覽中可修改日期", any(r['scheduledDate']=="2026-11-15" for r in st()['results']))
    pg.screenshot(path=str(OUT/'preview.png'),full_page=True)
    pg.click('#btnAddAll')
    s=st()
    ok("確認後建立 6 件，總共 9 件", len(s['todos'])==9 and len(s['results'])==0)
    maxold=max(x['sortOrder'] for x in s['todos'] if x['id'] in ('a1','a2','a3'))
    ok("新任務排在原本任務之後（底部）", all(x['sortOrder']>maxold for x in s['todos'] if x['id'] not in ('a1','a2','a3')))
    ok("沒有重複 id", len({x['id'] for x in s['todos']})==len(s['todos']))
    # ---- 日期分類 ----
    def cnt(v): pg.click(f'[data-dv={v}]'); return pg.locator('#app .list > .item').count()
    c={v:cnt(v) for v in ['today','tomorrow','week','month','future','overdue','done']}
    ok("今天 4 件（舊2＋找時間＋11/20前）", c['today']==4, c)
    ok("明天 1 件", c['tomorrow']==1, c)
    ok("本週（11/15～11/15）1 件：改成 11/15 的那件", c['week']==1, c)
    ok("本月（11/16～11/30）2 件：下週二、月底", c['month']==2, c)
    ok("已完成 1 件", c['done']==1, c)
    pg.click('[data-dv=today]'); pg.screenshot(path=str(OUT/'todo_today.png'),full_page=True)
    # ---- 拖曳排序 ----
    titles=lambda: [x.inner_text() for x in pg.locator('#app .list > .item button.txt').all()]
    before=titles()
    others_before={x['id']:x['sortOrder'] for x in st()['todos'] if not (x['status']=='open' and x['scheduledDate']<='2026-11-13')}
    h=pg.locator('#app .list > .item .handle').nth(3).bounding_box(); tgt=pg.locator('#app .list > .item').nth(0).bounding_box()
    pg.mouse.move(h['x']+h['width']/2,h['y']+h['height']/2); pg.mouse.down()
    pg.mouse.move(h['x']+5,tgt['y']+5,steps=12); pg.mouse.up()
    after=titles()
    ok("拖曳：第 4 件移到第 1 件", after[0]==before[3] and after[1:]==before[:3], (before,after))
    pg.reload(); pg.click('[data-tab=todo]')
    ok("重新整理後順序仍保留", titles()==after)
    ob={x['id']:x['sortOrder'] for x in st()['todos'] if x['id'] in others_before}; ok("拖曳沒有改到其他日期的任務順序", ob==others_before and len(others_before)>=4, (others_before,ob))
    # ---- 新增不影響既有順序 ----
    pg.click('#btnNewInView'); pg.fill('#qTitle','單筆新增測試'); pg.click('[data-act=quickSave]')
    ok("單筆新增出現在今天清單最底部，原有順序不變", titles()[:-1]==after and titles()[-1]=="單筆新增測試")
    # ---- 編輯日期（手動，不記入順延） ----
    pg.locator('button.txt',has_text='單筆新增測試').click()
    pg.fill('#eDate','2026-11-14'); pg.fill('#eDue','2026-11-12'); pg.screenshot(path=str(OUT/'edit.png')); pg.click('[data-act=editSave]')
    tk=[x for x in st()['todos'] if x['title']=="單筆新增測試"][0]
    ok("手動改日期：安排日期更新、順延歷史不變、建立時間不變", tk['scheduledDate']=="2026-11-14" and tk['rolloverCount']==0 and tk['rolloverHistory']==[] and tk['createdAt']<=tk['updatedAt'])
    # ---- 跨日自動順延 ----
    def gotoDay(dt):
        pg.clock.set_system_time(dt); pg.clock.run_for(61000)
    open_today=[x['id'] for x in st()['todos'] if x['status']=='open' and x['scheduledDate']=="2026-11-13"]
    # 完成其中一件，確認完成後不再順延
    done_id=open_today[0]; pg.click('[data-dv=today]'); pg.locator(f"[data-chk=\"{done_id}\"]").click()
    gotoDay(datetime.datetime(2026,11,14,0,1,tzinfo=T0.tzinfo))
    s=st(); t={x['id']:x for x in s['todos']}
    moved=[i for i in open_today if i!=done_id]
    ok("跨日 00:01：未完成的移到 11/14、順延 1 天", all(t[i]['scheduledDate']=="2026-11-14" and t[i]['rolloverCount']==1 for i in moved), [(t[i]['title'],t[i]['scheduledDate'],t[i]['rolloverCount']) for i in moved])
    ok("已完成的不順延", t[done_id]['scheduledDate']=="2026-11-13" and t[done_id]['rolloverCount']==0)
    ok("順延沒有產生新任務（數量不變、id 不變）", len(s['todos'])==10 and all(i in t for i in moved))
    ok("順延歷史有記錄 11/13→11/14", all(t[i]['rolloverHistory'][-1]['from']=="2026-11-13" and t[i]['rolloverHistory'][-1]['to']=="2026-11-14" for i in moved))
    ok("建立時間沒被改", t['a1']['createdAt']==1 if 'a1' in moved else True)
    pg.reload(); pg.clock.run_for(61000); pg.reload()
    s2={x['id']:x for x in st()['todos']}
    ok("同一天重新整理多次，不會重複順延", all(s2[i]['rolloverCount']==1 for i in moved))
    # 逾期：11/20 截止的任務 → 跳到 11/22
    gotoDay(datetime.datetime(2026,11,22,9,0,tzinfo=T0.tzinfo))
    s=st(); t={x['id']:x for x in s['todos']}
    due=[x for x in s['todos'] if x['title']=="11/20前交提案"][0]
    ok("離開好幾天再回來：一次補順延（11/14→11/22 共 8 天，累計 9 天）", due['scheduledDate']=="2026-11-22" and due['rolloverCount']==9, (due['scheduledDate'],due['rolloverCount']))
    ok("超過截止日：原截止日 11/20 不變", due['dueDate']=="2026-11-20")
    pg.click('[data-tab=todo]'); pg.click('[data-dv=overdue]')
    ok("逾期分頁出現該任務，顯示「已逾期」", pg.locator('#app .list > .item', has_text='11/20前交提案').count()==1 and pg.locator('.tag.over').count()>=1)
    pg.screenshot(path=str(OUT/'overdue.png'),full_page=True)
    pg.click('[data-tab=home]')
    ok("首頁也顯示逾期標記", pg.locator('#app .tag.over').count()>=1)
    pg.screenshot(path=str(OUT/'home2.png'),full_page=True)
    # ---- 今日建議（無時間區塊） ----
    pg.click('[data-tab=plan]'); pg.click('[data-e="2"]'); pg.click('[data-m="疲累"]'); pg.click('#btnPlan')
    import re
    txt=pg.inner_text('#app')
    ok("今日建議沒有任何時間區塊（HH:MM）", not re.search(r'\d{1,2}:\d{2}\s*[–-]',txt))
    pl=[x for x in st()['plans'] if x['date']=="2026-11-22"][0]
    today_ids={x['id'] for x in st()['todos'] if x['status']=='open' and x['scheduledDate']=="2026-11-22"}
    ok("建議只從今天的待辦挑選，並已儲存", len(pl['picks'])>0 and set(pl['picks'])<=today_ids)
    pg.screenshot(path=str(OUT/'plan.png'),full_page=True)
    pg.click('.seg [data-v=past]'); pg.locator('[data-hist]').first.click()
    ok("舊版有時間區塊的紀錄仍可查看（不顯示時間）", "舊的提案任務" in pg.inner_text('#app') or "舊提醒" in pg.inner_text('#app'))
    # ---- 匯出／匯入 ----
    pg.click('#btnSettings')
    with pg.expect_download() as dl: pg.click('[data-act=export]')
    path=dl.value.path(); exp=json.load(open(path,encoding='utf-8'))
    ok("匯出備份檔內容完整", len(exp['data']['todos'])==len(st()['todos']) and exp['schemaVersion']==5, dl.value.suggested_filename)
    pg.screenshot(path=str(OUT/'settings.png'))
    n=len(st()['todos'])
    pg.set_input_files('#importFile',path); pg.wait_for_selector('[data-opt]'); pg.click('[data-opt="0"]')
    ok("匯入同一份並選「合併」：不重複", len(st()['todos'])==n)
    # 刪一件再取代
    first=st()['todos'][0]['id']; pg.evaluate("id=>{}",first)
    pg.click('[data-tab=todo]'); pg.click('[data-dv=today]'); pg.locator('#app .list > .item .del').first.click()
    ok("刪除後少一件", len(st()['todos'])==n-1)
    nb=len(bks())
    pg.click('#btnSettings'); pg.set_input_files('#importFile',path); pg.wait_for_selector('[data-opt]'); pg.click('[data-opt="1"]')
    ok("匯入「取代」：還原成備份內容，且先自動備份目前資料", len(st()['todos'])==n and len(bks())==min(8,nb+1))
    # 還原本機備份（取代前那份 = n-1 件）
    pg.click('#btnSettings'); pg.locator('[data-act=restore]').first.click(); pg.click('[data-opt="0"]')
    ok("從本機備份還原", len(st()['todos'])==n-1)
    # 壞檔案
    open(str(OUT/'bad.json'),'w').write('not json')
    pg.click('#btnSettings'); pg.set_input_files('#importFile',str(OUT/'bad.json')); pg.wait_for_selector('[data-opt]')
    ok("錯誤檔案不會動到資料", len(st()['todos'])==n-1 and "無法匯入" in pg.inner_text('#sheet')); pg.click('[data-opt="0"]')
    # ---- UI 檢查 ----
    for tb in ['home','collect','todo','plan','card']:
        pg.click(f'[data-tab={tb}]')
        ow=pg.evaluate("document.documentElement.scrollWidth-window.innerWidth")
        ok(f"{tb} 頁沒有左右溢出", ow<=0, ow)
    pg.click('[data-tab=todo]'); pg.click('[data-dv=today]'); pg.evaluate("window.scrollTo(0,document.body.scrollHeight)")
    last=pg.locator('#app .card').last.bounding_box(); fab=pg.locator('#fab').bounding_box()
    ok("捲到底內容不被「記一下」遮住", last['y']+last['height']<=fab['y'])
    ok("沒有 JavaScript 錯誤", not errs, errs)
    d=b.new_page(viewport={'width':1280,'height':800}); d.goto(URL); d.screenshot(path=str(OUT/'desk.png'))
print("\n".join(R)); print(sum(r.startswith("PASS") for r in R),"/",len(R))
