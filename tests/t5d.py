from playwright.sync_api import sync_playwright
import os, json, datetime
from pathlib import Path
HERE=Path(__file__).resolve().parent; OUT=HERE/'out'; OUT.mkdir(exist_ok=True)
URL=''+__import__('pathlib').Path(__file__).resolve().parents[1].joinpath('index.html').as_uri()+''
R=[]
def ok(n,c,extra=""): R.append(("PASS" if c else "FAIL")+"  "+n+(("  ["+str(extra)+"]") if (not c and extra!="") else ""))
TZ=datetime.timezone(datetime.timedelta(hours=8))
T0=datetime.datetime(2026,11,13,20,0,tzinfo=TZ)
# 第一階段（版本 2）格式的資料
v2={"schemaVersion":2,"todos":[{"id":"t1","title":"剪影片","text":"剪影片","category":"內容創作","cat":"內容創作","priority":"高","pri":"高","scheduledDate":"2026-11-13","dueDate":None,"createdAt":1,"created":1,"completedAt":None,"status":"open","done":False,"sortOrder":1,"rolloverCount":0,"rolloverHistory":[],"updatedAt":1,"mins":60,"description":""},
  {"id":"t2","title":"回覆客戶","text":"回覆客戶","category":"工作","cat":"工作","priority":"中","pri":"中","scheduledDate":"2026-11-13","dueDate":None,"createdAt":2,"created":2,"completedAt":None,"status":"open","done":False,"sortOrder":2,"rolloverCount":0,"rolloverHistory":[],"updatedAt":2,"mins":30,"description":""}],
  "results":[],"plans":[],"cards":[],"draft":"","lastRolloverDate":"2026-11-13"}
with sync_playwright() as p:
    b=p.chromium.launch()
    ctx=b.new_context(viewport={'width':390,'height':844},device_scale_factor=2,timezone_id='Asia/Taipei',accept_downloads=True)
    pg=ctx.new_page(); errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)))
    pg.clock.install(time=T0)
    pg.goto(URL); pg.evaluate("d=>{localStorage.clear();localStorage.setItem('lifebox_v1',JSON.stringify(d))}", v2); pg.wait_for_timeout(800); pg.reload(); pg.wait_for_timeout(300)
    st=lambda: pg.evaluate("JSON.parse(localStorage.getItem('lifebox_v1'))")
    bks=lambda: pg.evaluate("JSON.parse(localStorage.getItem('lifebox_v1_backups')||'[]')")
    s=st()
    ok("第一階段資料升級到版本 6，待辦完整保留", s['schemaVersion']==6 and len(s['todos'])==2 and s['todos'][0]['sortOrder']==1)
    ok("升級前自動備份第一階段資料", len([b for b in bks() if '升級' in b['reason']])==1 and json.loads([b for b in bks() if '升級' in b['reason']][0]['data'])['schemaVersion']==2)
    ok("新增的資料區都建立好（空的）", all(isinstance(s.get(k),list) for k in ["habits","habitRecords","moodRecords","journalEntries","reviews","goals","wishlist"]) and s['personalProfile']=={"entries":[]})
    ok("底部導覽維持 5 個（成長已合併到首頁）", [x.inner_text().strip().split(chr(10))[0] for x in pg.locator('#tabbar button').all()]==["今日","收集","待辦","安排","星光秘境"], [x.inner_text().strip() for x in pg.locator('#tabbar button').all()])
    ok("沒有習慣時，首頁不顯示習慣卡", "今日習慣" not in pg.inner_text('#app'))
    pg.click('[data-tab=home]'); pg.screenshot(path=str(OUT/'g_hub.png'),full_page=True)
    ok("首頁合併了成長的 10 個入口", pg.locator(".row[data-ghub]").count()==10)
    # ---- 習慣 ----
    pg.click('.row[data-ghub=habit]')
    pg.fill('#hTitle','閱讀'); pg.fill('#hTarget','每天 30 分鐘'); pg.click('#gAddHabit')
    pg.fill('#hTitle','喝水'); pg.click('#gAddHabit')
    ok("新增 2 個習慣", len(st()['habits'])==2)
    hid=st()['habits'][0]['id']
    pg.click(f'[data-ghtog="{hid}"]')
    ok("每日打卡寫入紀錄", any(r['habitId']==hid and r['date']=="2026-11-13" for r in st()['habitRecords']))
    ok("連續 1 天", "連續 1 天" in pg.inner_text('#app'))
    pg.click(f'[data-ghtog="{hid}"]')
    ok("再按一次可以取消打卡", not any(r['habitId']==hid for r in st()['habitRecords']))
    pg.click(f'[data-ghtog="{hid}"]')
    # 連續紀錄：跨到明天、後天打卡
    for d in [14,15]:
        pg.clock.set_system_time(datetime.datetime(2026,11,d,9,0,tzinfo=TZ)); pg.clock.run_for(61000); pg.click('[data-tab=home]'); pg.click('.row[data-ghub=habit]')
        pg.click(f'[data-ghtog="{hid}"]')
    ok("連續 3 天打卡 → 顯示連續 3 天", "連續 3 天" in pg.inner_text('#app'), pg.inner_text('#app')[:300])
    # 隔一天沒打，今天還沒打 → 連續仍從昨天算
    pg.clock.set_system_time(datetime.datetime(2026,11,16,9,0,tzinfo=TZ)); pg.clock.run_for(61000); pg.click('[data-tab=home]'); pg.click('.row[data-ghub=habit]')
    ok("今天還沒打卡時，不算中斷（仍是連續 3 天）", "連續 3 天" in pg.inner_text('#app'))
    ok("沒打卡不會扣點數或出現懲罰字眼", "扣" not in pg.inner_text('#app').replace("不會扣任何點數",""))
    # 難以維持 → 降低難度（要使用者確認）
    pg.clock.set_system_time(datetime.datetime(2026,11,24,9,0,tzinfo=TZ)); pg.clock.run_for(61000); pg.click('[data-tab=home]'); pg.click('.row[data-ghub=habit]')
    ok("建立滿 7 天、最近 7 天打卡少於 3 次 → 出現溫柔建議", pg.locator(f'[data-gheasy="{hid}"]').count()==1)
    pg.click(f'[data-gheasy="{hid}"]')
    ok("建議把 30 分鐘降成 5 分鐘", pg.input_value('#eaTarget')=="每天 5 分鐘", pg.input_value('#eaTarget'))
    ok("還沒確認前，習慣目標沒有被改", st()['habits'][0]['target']=="每天 30 分鐘")
    pg.screenshot(path=str(OUT/'g_easy.png'))
    pg.click('[data-gact=easierSave]')
    h=st()['habits'][0]
    ok("確認後才修改，並留下調整紀錄", h['target']=="每天 5 分鐘" and h['easierHistory'][0]['from']=="每天 30 分鐘")
    ok("調整後 7 天內不再重複提醒", pg.locator(f'[data-gheasy="{hid}"]').count()==0)
    pg.click(f'[data-ghtog="{hid}"]')
    pg.screenshot(path=str(OUT/'g_habit.png'),full_page=True)
    # 首頁習慣卡
    pg.click('[data-tab=home]')
    ok("首頁出現今日習慣，可直接打卡", pg.locator('#app [data-ghtog]').count()==2)
    hid2=st()['habits'][1]['id']; pg.click(f'#app [data-ghtog="{hid2}"]')
    ok("首頁打卡寫入", any(r['habitId']==hid2 and r['date']=="2026-11-24" for r in st()['habitRecords']))
    # 封存
    pg.click('[data-tab=home]'); pg.click('.row[data-ghub=habit]'); pg.click(f'[data-ghedit="{hid2}"]'); pg.click('[data-gact=habitArchive]')
    ok("封存後打卡紀錄保留", st()['habits'][1]['archived'] and any(r['habitId']==hid2 for r in st()['habitRecords']))
    # ---- 心情與日記 ----
    pg.click('.back[data-ghub=""]'); pg.click('.row[data-ghub=mood]')
    pg.click('[data-gm="焦慮"]'); pg.click('[data-ge="2"]'); pg.fill('#mNote','事情有點多'); pg.click('#gSaveMood')
    m=st()['moodRecords']
    ok("記錄今天心情與精神", len(m)==1 and m[0]['mood']=="焦慮" and m[0]['energy']==2 and m[0]['date']=="2026-11-24")
    pg.click('[data-gm="平穩"]'); pg.click('#gSaveMood')
    ok("同一天再記錄是更新，不會多一筆", len(st()['moodRecords'])==1 and st()['moodRecords'][0]['mood']=="平穩")
    for typ,txt in [("日記","今天去咖啡廳寫企劃"),("感謝","謝謝朋友幫我看提案"),("開心的事","發文反應很好")]:
        pg.click(f'[data-gjt="{typ}"]'); pg.fill('#jText',txt); pg.click('#gAddJournal')
    ok("新增 3 種日記紀錄", len(st()['journalEntries'])==3 and {e['type'] for e in st()['journalEntries']}=={"日記","感謝","開心的事"})
    pg.fill('#jSearch','提案'); pg.wait_for_timeout(100)
    ok("歷史搜尋：搜「提案」只出現 1 則", pg.locator('.entry').count()==1)
    pg.fill('#jSearch',''); pg.screenshot(path=str(OUT/'g_mood.png'),full_page=True)
    # 安排頁帶入心情
    pg.click('[data-tab=plan]')
    ok("今日建議自動帶入今天記錄的心情", pg.locator('#moodChips .chip.on').inner_text()=="平穩")
    # ---- 每日回顧 ----
    # 完成一件待辦
    pg.click('[data-tab=todo]'); pg.click('[data-dv=today]'); pg.locator('#app [data-chk]').first.click()
    pg.click('[data-tab=home]'); pg.click('.row[data-ghub=review]')
    ok("回顧顯示今日完成率 50%（1/2）", "50%" in pg.inner_text('#app'))
    pg.fill('#rHappy','提案順利'); pg.fill('#rThanks','朋友'); pg.fill('#rTomorrow','買咖啡豆\n整理素材'); pg.click('#gSaveReview')
    r=st()['reviews']
    ok("回顧已儲存（含完成率、習慣、心情、鼓勵）", len(r)==1 and r[0]['rate']==50 and r[0]['mood']=="平穩" and r[0]['message'])
    n=len(st()['todos'])
    pg.click('#gTomorrowTasks')
    ok("加入明天待辦前要先確認（尚未寫入）", len(st()['todos'])==n)
    pg.click('[data-opt="0"]')
    s=st(); new=[t for t in s['todos'] if t['title'] in ("買咖啡豆","整理素材")]
    ok("確認後建立 2 件明天的任務", len(new)==2 and all(t['scheduledDate']=="2026-11-25" for t in new))
    pg.screenshot(path=str(OUT/'g_review.png'),full_page=True)
    # ---- 目標 ----
    pg.click('.back[data-ghub=""]'); pg.click('.row[data-ghub=goal]')
    pg.click('#gNewGoal'); pg.fill('#gTitle','經營 IG 到 1 萬粉'); pg.click('[data-gact=goalSave]')
    yid=st()['goals'][0]['id']
    ok("新增年度目標（2026 年）", st()['goals'][0]['level']=="year" and st()['goals'][0]['period']=="2026")
    pg.click('.seg [data-v=quarter]'); pg.click('#gNewGoal'); pg.fill('#gTitle','每週發 3 篇'); pg.select_option('#gParent',yid); pg.click('[data-gact=goalSave]')
    q=[g for g in st()['goals'] if g['level']=="quarter"][0]
    ok("新增季度目標，期間 2026 第 4 季，連到年度目標", q['period']=="2026-Q4" and q['parentId']==yid)
    for mtxt in ["拍 10 支 Reels","整理發文行事曆"]:
        pg.fill(f'[data-gmsin="{q["id"]}"]',mtxt); pg.click(f'[data-gmsadd="{q["id"]}"]')
    pg.locator(f'[data-gms^="{q["id"]}|"]').first.click()
    q=[g for g in st()['goals'] if g['level']=="quarter"][0]
    ok("里程碑 1/2 完成 → 進度 50%", sum(m['done'] for m in q['milestones'])==1 and "50%" in pg.inner_text('#app'))
    pg.click('.seg [data-v=month]'); pg.click('#gNewGoal'); pg.fill('#gTitle','11 月發 12 篇')
    ok("月度目標可選年度與季度作為上層", pg.locator('#gParent option').count()==3)
    pg.click('[data-gact=goalSave]')
    # 任務連結目標
    pg.click('[data-tab=todo]'); pg.click('[data-dv=today]'); pg.locator('#app button.txt').first.click(); pg.select_option('#eGoal',q['id']); pg.click('[data-act=editSave]')
    ok("任務可連結目標", any(t.get('goalId')==q['id'] for t in st()['todos']))
    pg.click('[data-tab=home]'); pg.click('.row[data-ghub=goal]'); pg.click('.seg [data-v=quarter]')
    ok("目標顯示相關任務數", "相關任務 1 件" in pg.inner_text('#app'))
    pg.screenshot(path=str(OUT/'g_goal.png'),full_page=True)
    # ---- 願望清單 ----
    pg.click('.back[data-ghub=""]'); pg.click('.row[data-ghub=wish]')
    pg.click('[data-wnew]'); pg.fill('#wTitle','去京都看紅葉'); pg.select_option('#wCat','travel'); pg.fill('#wBudget','45000'); pg.click('[data-wsave]')
    pg.click('[data-wnew]'); pg.fill('#wTitle','買新相機'); pg.select_option('#wCat','goods'); pg.fill('#wBudget','30000'); pg.click('[data-wsave]')
    ok("新增 2 個願望，預算合計 NT$ 75,000", len(st()['wishlist'])==2 and "75,000" in pg.inner_text('#app'))
    wid=[w for w in st()['wishlist'] if w['title']=="買新相機"][0]['id']
    pg.click(f'[data-wedit="{wid}"]'); pg.select_option('#wStatus','achieved'); pg.fill('#wDoneDate','2026-11-24'); pg.fill('#wCost','28500'); pg.fill('#wReview','拍起來好清楚！'); pg.click('[data-wsave]'); pg.click('#sheet [data-opt="1"]')
    w=[w for w in st()['wishlist'] if w['id']==wid][0]
    ok("完成願望：狀態、完成日期、實際花費、回顧都記錄", w['status']=="done" and w['doneDate']=="2026-11-24" and w['actualCost']==28500 and w['review'])
    pg.click('[data-wt="travel"]')
    ok("依類型篩選", pg.locator('#app .list > .item').count()==1)
    pg.click('[data-wt="全部"]'); pg.screenshot(path=str(OUT/'g_wish.png'),full_page=True)
    # ---- 個人資料庫 ----
    pg.click('.back[data-ghub=""]'); pg.click('.row[data-ghub=profile]')
    pg.fill('#pKey','最有精神的時段'); pg.fill('#pVal','早上 9～11 點'); pg.click('#gAddProfile')
    ok("新增個人偏好，記錄來源", st()['personalProfile']['entries'][0]['source']=="自己填寫")
    pg.fill('#pKey','網銀密碼'); pg.fill('#pVal','abc123'); pg.click('#gAddProfile')
    ok("敏感資料（密碼）會被擋下，不儲存", len(st()['personalProfile']['entries'])==1)
    pg.click('[data-opt="0"]')
    pg.fill('#pKey','身分'); pg.fill('#pVal','A123456789'); pg.click('#gAddProfile')
    ok("長串數字（像證件號）也會被擋下", len(st()['personalProfile']['entries'])==1); pg.click('[data-opt="0"]')
    eid=st()['personalProfile']['entries'][0]['id']; pg.click(f'[data-gpedit="{eid}"]'); pg.fill('#epVal','早上 8～11 點'); pg.click('[data-gact=profileSave]')
    ok("可以修改", st()['personalProfile']['entries'][0]['value']=="早上 8～11 點")
    pg.screenshot(path=str(OUT/'g_profile.png'),full_page=True)
    # ---- 備份涵蓋第二階段 ----
    pg.click('#btnSettings')
    with pg.expect_download() as dl: pg.click('[data-act=export]')
    exp=json.load(open(dl.value.path(),encoding='utf-8'))['data']
    ok("匯出包含所有第二階段資料", all(len(exp[k])>0 for k in ["habits","habitRecords","moodRecords","journalEntries","reviews","goals","wishlist"]) and len(exp['personalProfile']['entries'])==1)
    before=st()
    pg.set_input_files('#importFile',dl.value.path()); pg.wait_for_selector('[data-opt]'); pg.click('[data-opt="0"]')
    after=st()
    ok("匯入合併不會產生重複", all(len(after[k])==len(before[k]) for k in ["todos","habits","habitRecords","moodRecords","journalEntries","reviews","goals","wishlist"]) and len(after['personalProfile']['entries'])==1)
    # ---- 畫面 ----
    pg.click('[data-tab=home]')
    for k in ["","habit","mood","review","goal","wish","profile"]:
        if k: pg.click(f'[data-ghub={k}]')
        ow=pg.evaluate("document.documentElement.scrollWidth-window.innerWidth")
        ok(f"成長/{k or '首頁'} 沒有左右溢出", ow<=0, ow)
        if k: pg.click('.back[data-ghub=""]')
    pg.click('[data-tab=home]'); pg.screenshot(path=str(OUT/'g_home.png'),full_page=True)
    snap=st(); pg.wait_for_timeout(1500); pg.reload(); pg.wait_for_timeout(500)
    after=st()
    ok("重新整理後所有第二階段資料都還在", all(len(after[k])==len(snap[k]) for k in ["habits","habitRecords","moodRecords","journalEntries","reviews","goals","wishlist","todos"]))
    ok("沒有 JavaScript 錯誤", not errs, errs)
print("\n".join(R)); print(sum(r.startswith("PASS") for r in R),"/",len(R))
