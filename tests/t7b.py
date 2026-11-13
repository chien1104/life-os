from playwright.sync_api import sync_playwright
import json, datetime
from pathlib import Path
HERE=Path(__file__).resolve().parent; OUT=HERE/'out'; OUT.mkdir(exist_ok=True)
URL=''+__import__('pathlib').Path(__file__).resolve().parents[1].joinpath('index.html').as_uri()+''
R=[]
def ok(n,c,extra=""): R.append(("PASS" if c else "FAIL")+"  "+n+(("  ["+str(extra)+"]") if (not c and extra!="") else ""))
TZ=datetime.timezone(datetime.timedelta(hours=8))
T0=datetime.datetime(2026,11,13,9,0,tzinfo=TZ)
with sync_playwright() as p:
    b=p.chromium.launch()
    # ---------- 沒有 Claude 的環境（下載的檔案） ----------
    c0=b.new_context(viewport={'width':390,'height':844},timezone_id='Asia/Taipei'); p0=c0.new_page(); e0=[]; p0.on('pageerror',lambda e:e0.append(str(e)))
    p0.goto(URL); p0.wait_for_timeout(400)
    ok("新朋友第一次打開：顯示使用說明", p0.locator('#sheet.show').count()==1 and "歡迎使用" in p0.inner_text('#sheet'))
    p0.click('#sheet [data-act=close]'); p0.wait_for_timeout(1200); p0.reload(); p0.wait_for_timeout(400)
    ok("關掉後重新打開，不會再跳出", p0.locator('#sheet.show').count()==0)
    p0.click('[data-tab=collect]'); ok("下載的檔案版本：沒有 AI 按鈕", p0.locator('#btnAIOrganize').count()==0)
    p0.click('#btnSettings'); ok("設定顯示 AI 這裡無法使用、雲端未開啟", "這裡無法使用" in p0.inner_text('#sheet') and "未開啟" in p0.inner_text('#sheet'))
    ok("下載版本沒有錯誤", not e0, e0); c0.close()
    # ---------- Claude 環境（模擬） ----------
    ctx=b.new_context(viewport={'width':390,'height':844},device_scale_factor=2,timezone_id='Asia/Taipei')
    ctx.add_init_script(path=''+str(__import__('pathlib').Path(__file__).with_name('mock.js'))+'')
    pg=ctx.new_page(); errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)))
    pg.clock.install(time=T0)
    pg.goto(URL); pg.wait_for_timeout(300); pg.clock.run_for(2000)
    if pg.locator('#sheet.show').count(): pg.click('#sheet [data-act=close]')
    st=lambda: pg.evaluate("JSON.parse(localStorage.getItem('lifebox_v1'))")
    cloud=lambda: pg.evaluate("JSON.parse(JSON.stringify(window.__store))")
    # 首頁合併
    tabs=[x.inner_text().strip().split("\n")[0] for x in pg.locator('#tabbar button').all()]
    ok("底部導覽 5 個，沒有「成長」", tabs==["今日","收集","待辦","安排","星光秘境"], tabs)
    ok("首頁同時有今天的內容與成長入口", pg.locator('.row[data-ghub]').count()==10 and "今天的待辦" in pg.inner_text('#app') and "成長與生活管理" in pg.inner_text('#app'))
    pg.click('.row[data-ghub=habit]'); ok("進入子頁面時，底部「今日」維持亮起", pg.locator('#tabbar button.on').inner_text().startswith("今日"))
    pg.click('.back[data-ghub=""]'); ok("「返回今日」回到首頁", pg.locator('.row[data-ghub]').count()==10)
    pg.screenshot(path=str(OUT/'ai_home.png'),full_page=True)
    # 雲端：第一次開啟就上傳
    c=cloud(); meta=c.get('data/users/user1/lifeos_meta')
    ok("雲端同步：第一次開啟建立私人雲端資料（data/users/<id>/）", meta is not None and all(k.startswith('data/users/user1/') for k in c))
    # AI 整理
    pg.evaluate("""window.__aiJson=(input)=>({items:[
      {text:'明天交提案給客戶',cat:'工作',pri:'高',scheduledDate:'2026-11-14',dueDate:'2026-11-14',mins:60},
      {text:'拍早晨 Reels',cat:'奇怪分類',pri:'超高',scheduledDate:'2020-01-01',dueDate:'不是日期',mins:7}]})""")
    pg.click('[data-tab=collect]'); pg.fill('#captureInput','明天要交提案給客戶，然後想拍早晨 reels'); pg.wait_for_timeout(500)
    n0=len(st()['todos']); pg.click('#btnAIOrganize'); pg.wait_for_timeout(300)
    s=st(); res=s['results']
    ok("AI 整理：產生 2 件預覽（標示 AI）", len(res)==2 and all(r.get('ai') for r in res) and pg.locator('.tag.ai').count()==2)
    ok("AI 整理：還沒確認前沒有建立任務", len(s['todos'])==n0)
    bad=[r for r in res if r['text']=='拍早晨 Reels'][0]
    ok("AI 回傳不合理的值會被修正（分類→規則判斷、優先→中、過去日期→今天、錯誤截止日→空、時間→改用規則判斷）", bad['cat']=="內容創作" and bad['pri']=="中" and bad['scheduledDate']=="2026-11-13" and bad['dueDate'] is None and bad['mins']==60, bad)
    ok("AI 收到的指令包含今天日期與語氣規則", "2026-11-13" in pg.evaluate("__aiCalls[0]") and "溫柔" in pg.evaluate("__aiCalls[0]"))
    pg.click('#btnAddAll'); ok("確認後才建立 2 件任務", len(st()['todos'])==n0+2)
    # AI 拆解
    pg.evaluate("""window.__aiJson=()=>({steps:[{title:'整理素材',mins:30},{title:'寫腳本大綱',mins:15},{title:'拍攝',mins:60}]})""")
    pg.click('[data-tab=todo]'); pg.locator('button.txt',has_text='明天交提案').first.click() if pg.locator('button.txt',has_text='明天交提案').count() else None
    pg.click('[data-dv=tomorrow]'); pg.locator('button.txt').first.click()
    pg.click('[data-aisplit]'); pg.wait_for_selector('[data-step]')
    pg.locator('[data-step="2"]').uncheck(); n1=len(st()['todos'])
    ok("AI 拆解：先預覽步驟，尚未建立", len(st()['todos'])==n1 and pg.locator('[data-step]').count()==3)
    pg.click('[data-aistepsave]')
    new=[t for t in st()['todos'] if t['title'] in ("整理素材","寫腳本大綱","拍攝")]
    ok("只建立勾選的 2 個步驟，沿用原任務分類與日期", len(new)==2 and all(t['category']=="工作" and t['scheduledDate']=="2026-11-14" for t in new))
    # AI 早晨建議（不改資料）
    pg.click('[data-tab=plan]'); plans=len(st()['plans']); pg.click('#btnAIPlan'); pg.wait_for_timeout(200)
    ok("AI 早晨建議顯示在卡片上，沒有改動資料", pg.locator('[data-aikey=plan]').count()==1 and len(st()['plans'])==plans)
    ok("早晨建議送出今天的待辦與心情", "今天的待辦" in pg.evaluate("__aiCalls[__aiCalls.length-1]") and "心情" in pg.evaluate("__aiCalls[__aiCalls.length-1]"))
    pg.screenshot(path=str(OUT/'ai_plan.png'),full_page=True)
    # AI 回顧：存進回顧要按按鈕
    pg.click('[data-tab=home]'); pg.click('.row[data-ghub=review]'); pg.fill('#rHappy','提案順利'); pg.click('#gSaveReview')
    pg.evaluate("window.__aiText='今天你很努力，提案完成了。沒做完的明天再來就好。'"); pg.click('#btnAIReview'); pg.wait_for_timeout(200)
    ok("AI 回顧顯示，但尚未寫入", "aiNote" not in st()['reviews'][0])
    pg.click('#btnAIReviewSave'); ok("按「存進今日回顧」才寫入", st()['reviews'][0].get('aiNote','').startswith("今天你很努力"))
    # AI 報告、財務
    pg.click('.back[data-ghub=""]'); pg.click('.row[data-ghub=report]'); pg.click('#btnAIReport'); pg.wait_for_timeout(200)
    ok("AI 週報分析", pg.locator('.aicard').count()==1)
    pg.click('.back[data-ghub=""]'); pg.click('.row[data-ghub=fin]'); pg.click('.seg [data-v=acc]'); pg.fill('#faName','現金'); pg.click('#fAddAcc')
    pg.click('.seg [data-v=tx]'); pg.click('#fNewTx'); pg.fill('#txAmt','350'); pg.click('[data-pact=txSave]'); pg.click('.seg [data-v=overview]')
    pg.click('#btnAIFin'); pg.wait_for_timeout(200); ok("AI 財務分析（有記帳時才出現）", pg.locator('[data-aikey^=fin-]').count()==1)
    # AI 習慣降難度：只填入欄位
    pg.click('.back[data-ghub=""]'); pg.click('.row[data-ghub=habit]'); pg.fill('#hTitle','閱讀'); pg.fill('#hTarget','每天 30 分鐘'); pg.click('#gAddHabit')
    hid=st()['habits'][0]['id']; pg.evaluate(f"Sheet.easier('{hid}')")
    pg.evaluate("""window.__aiJson=()=>({target:'睡前讀一頁就好',why:'先讓書回到生活裡'})"""); pg.click('[data-aieasy]'); pg.wait_for_timeout(200)
    ok("AI 建議填入欄位，習慣目標仍未改", pg.input_value('#eaTarget')=="睡前讀一頁就好" and st()['habits'][0]['target']=="每天 30 分鐘")
    pg.click('[data-gact=easierSave]'); ok("確認後才改", st()['habits'][0]['target']=="睡前讀一頁就好")
    # 個人資料開關
    pg.click('.back[data-ghub=""]'); pg.click('.row[data-ghub=profile]'); pg.fill('#pKey','喜歡的飲料'); pg.fill('#pVal','無糖烏龍'); pg.click('#gAddProfile')
    pg.click('[data-tab=plan]'); pg.click('#btnAIPlan'); pg.wait_for_timeout(200)
    ok("預設會把個人資料庫給 AI 參考", "無糖烏龍" in pg.evaluate("__aiCalls[__aiCalls.length-1]"))
    pg.click('#btnSettings'); pg.locator('#aiProfile').uncheck(); pg.click('[data-act=close]')
    pg.evaluate("window.__aiText='換一個回覆'"); pg.click('#btnAIPlan'); pg.wait_for_timeout(200)
    ok("關掉後，AI 不會收到個人資料", "無糖烏龍" not in pg.evaluate("__aiCalls[__aiCalls.length-1]"))
    # AI 搜尋
    pg.click('#btnSearch'); pg.fill('#gSearch','我上次說要交給客戶的東西')
    pg.evaluate("""window.__aiJson=()=>({start:null,end:null,module:'task',keywords:['提案']})"""); pg.click('#btnAISearch'); pg.wait_for_timeout(200)
    ok("AI 搜尋：理解成條件後用本機資料搜尋", "AI 理解為" in pg.inner_text('#searchRes') and "明天交提案給客戶" in pg.inner_text('#searchRes'))
    pg.click('#sheet', position={'x':5,'y':5})
    # 錯誤處理
    pg.evaluate("window.__aiFail={code:'rate_limited',message:'x'}"); pg.click('[data-tab=plan]'); pg.click('#btnAIPlan'); pg.wait_for_timeout(200)
    ok("AI 太頻繁：顯示提醒、按鈕保留", pg.locator('#btnAIPlan').count()==1 and "頻繁" in pg.inner_text('#toast'))
    pg.evaluate("window.__aiFail={code:'not_granted',message:'x'}"); pg.click('#btnAIPlan'); pg.wait_for_timeout(200)
    ok("不允許 AI：所有 AI 按鈕隱藏，其他功能照常", pg.locator('#btnAIPlan').count()==0 and pg.locator('#btnPlan').count()==1)
    # 雲端同步：變更會上傳
    pg.clock.run_for(3000); pg.wait_for_timeout(300)
    c=cloud(); m=c['data/users/user1/lifeos_meta']
    remote=json.loads("".join(c[f"data/users/user1/lifeos_{m['v']}_{i}"]['s'] for i in range(m['n'])))
    ok("變更會自動上傳到雲端（待辦、習慣、記帳都在）", len(remote['todos'])==len(st()['todos']) and len(remote['habits'])==1 and len(remote['fin']['tx'])==1)
    ok("雲端只保留最新一版（舊版分段已刪除）", len([k for k in c if '/lifeos_' in k and k!='data/users/user1/lifeos_meta'])==m['n'])
    seed=json.dumps(c)
    # 另一台裝置：空的瀏覽器 → 從雲端載入
    ctx2=b.new_context(viewport={'width':390,'height':844},timezone_id='Asia/Taipei'); ctx2.add_init_script(script=f"sessionStorage.setItem('MOCK_CLOUD_SEED',{json.dumps(seed)});"); ctx2.add_init_script(path=''+str(__import__('pathlib').Path(__file__).with_name('mock.js'))+'')
    p2=ctx2.new_page(); e2=[]; p2.on('pageerror',lambda e:e2.append(str(e))); p2.clock.install(time=T0+datetime.timedelta(minutes=30))
    p2.goto(URL); p2.wait_for_timeout(600)
    s2=json.loads(p2.evaluate("localStorage.getItem('lifebox_v1')"))
    ok("另一台裝置：自動載入雲端資料", len(s2['todos'])==len(st()['todos']) and len(s2['habits'])==1)
    # 衝突：裝置 2 新增後上傳；裝置 1（還沒重新整理）再修改 → 不覆蓋，先備份再載入
    p2.click('[data-tab=todo]'); p2.click('#fab'); p2.fill('#qTitle','手機上新增的事'); p2.click('[data-act=quickSave]'); p2.clock.run_for(3000); p2.wait_for_timeout(300)
    c2=p2.evaluate("JSON.parse(JSON.stringify(window.__store))")
    pg.evaluate("s=>{ for(const k of Object.keys(window.__store)) delete window.__store[k]; Object.assign(window.__store, JSON.parse(s)); }", json.dumps(c2))
    pg.click('[data-tab=todo]'); pg.click('#fab'); pg.fill('#qTitle','電腦上新增的事'); pg.click('[data-act=quickSave]'); pg.clock.run_for(3000); pg.wait_for_timeout(400)
    titles=[t['title'] for t in st()['todos']]
    bk=pg.evaluate("JSON.parse(localStorage.getItem('lifebox_v1_backups')||'[]').map(b=>b.reason)")
    ok("衝突時不會用舊資料覆蓋雲端：載入另一台的新資料", "手機上新增的事" in titles, titles)
    ok("衝突時這台的資料先自動備份（可從設定還原）", any("其他裝置" in r for r in bk), bk)
    pg.click('#btnSettings'); pg.click('[data-act=export]'); pg.wait_for_timeout(400)
    sv=pg.evaluate("window.__saved")
    ok("在 Claude 裡匯出備份：改用 Claude 的下載確認（.json）", len(sv)==1 and sv[0]['filename'].endswith('.json') and sv[0]['size']>100, sv)
    # ---------- 朋友用分享連結打開（只有檢視權限，雲端寫入被拒） ----------
    ctx3=b.new_context(viewport={'width':390,'height':844},timezone_id='Asia/Taipei'); ctx3.add_init_script(path=''+str(__import__('pathlib').Path(__file__).with_name('mock.js'))+'')
    ctx3.add_init_script(script="""(()=>{ const u=window.claude.use; window.claude={use:async n=>{ if(n==='db') return {collection:()=>({doc:()=>({get:async()=>({exists:false,data:()=>undefined}), set:async()=>{ throw {code:'invalid_argument',message:'denied'}; }, delete:async()=>{}})})}; return u(n); }}; })();""")
    p3=ctx3.new_page(); e3=[]; p3.on('pageerror',lambda e:e3.append(str(e))); p3.clock.install(time=T0)
    p3.goto(URL); p3.wait_for_timeout(500); p3.clock.run_for(2000)
    ok("朋友第一次打開也看到使用說明", "歡迎使用" in p3.inner_text('#sheet')); p3.click('#sheet [data-act=close]')
    p3.click('[data-tab=collect]'); ok("朋友可以使用 AI 按鈕", p3.locator('#btnAIOrganize').count()==1)
    p3.click('[data-tab=todo]'); p3.click('#fab'); p3.fill('#qTitle','朋友的第一件事'); p3.click('[data-act=quickSave]'); p3.clock.run_for(3000); p3.wait_for_timeout(300)
    ok("沒有雲端權限時，資料照樣存在本機", "朋友的第一件事" in p3.evaluate("localStorage.getItem('lifebox_v1')"))
    p3.click('#btnSettings'); st3=p3.inner_text('#sheet')
    ok("設定顯示「只存本機」而不是「同步失敗」", "只存本機" in st3 and "同步失敗" not in st3 and "記得先匯出備份檔" in st3); p3.click('#sheet [data-act=close]')
    p3.click('[data-tab=home]')
    ok("首頁提醒匯出備份", "建議匯出一份備份檔" in p3.inner_text('#app'))
    p3.locator('[data-opensettings]').click(); p3.click('[data-act=export]'); p3.wait_for_timeout(400); p3.click('#sheet [data-act=close]')
    p3.click('[data-tab=todo]'); p3.click('[data-tab=home]')
    ok("匯出後提醒消失（14 天後才會再提醒）", "建議匯出一份備份檔" not in p3.inner_text('#app'))
    ok("朋友模式沒有 JavaScript 錯誤", not e3, e3)
    ok("沒有 JavaScript 錯誤", not errs and not e2, errs+e2)
print("\n".join(R)); print(sum(r.startswith("PASS") for r in R),"/",len(R))
