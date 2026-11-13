from playwright.sync_api import sync_playwright
import json, datetime, subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent; OUT=HERE/'out'; OUT.mkdir(exist_ok=True)
URL=''+__import__('pathlib').Path(__file__).resolve().parents[1].joinpath('index.html').as_uri()+''
R=[]
def ok(n,c,extra=""): R.append(("PASS" if c else "FAIL")+"  "+n+(("  ["+str(extra)[:300]+"]") if (not c and extra!="") else ""))
TZ=datetime.timezone(datetime.timedelta(hours=8))
T0=datetime.datetime(2026,11,13,9,0,tzinfo=TZ)
v4={"schemaVersion":4,"todos":[{"id":"t1","title":"剪影片","text":"剪影片","category":"內容創作","cat":"內容創作","priority":"高","pri":"高","scheduledDate":"2026-11-13","dueDate":None,"createdAt":1,"created":1,"completedAt":None,"status":"open","done":False,"sortOrder":1,"rolloverCount":0,"rolloverHistory":[],"updatedAt":1,"mins":60,"description":""}],
  "results":[],"plans":[],"cards":[{"date":"2026-11-01","level":"大吉"}],"draft":"","lastRolloverDate":"2026-11-13",
  "wishlist":[{"id":"w1","title":"去京都看紅葉","type":"旅遊","status":"want","priority":"中","budget":30000,"note":"秋天","createdAt":5},
              {"id":"w2","title":"買相機","type":"購物","status":"done","priority":"高","budget":20000,"doneDate":"2026-10-01","actualCost":18000,"createdAt":6}],
  "settings":{"welcomed":True}}
def fresh(b, seed=None, tz='Asia/Taipei'):
    ctx=b.new_context(viewport={'width':390,'height':844},timezone_id=tz); pg=ctx.new_page(); errs=[]
    pg.on('pageerror',lambda e:errs.append(str(e))); pg.clock.install(time=T0)
    pg.goto(URL); pg.evaluate("d=>{localStorage.clear(); if(d) localStorage.setItem('lifebox_v1', typeof d==='string'?d:JSON.stringify(d))}", seed); pg.reload(); pg.wait_for_timeout(300)
    return ctx,pg,errs
st=lambda pg: pg.evaluate("JSON.parse(localStorage.getItem('lifebox_v1'))")
bks=lambda pg: pg.evaluate("JSON.parse(localStorage.getItem('lifebox_v1_backups')||'[]')")
with sync_playwright() as p:
    b=p.chromium.launch()
    # ===== P0：資料損壞 =====
    ctx,pg,errs=fresh(b,"{壞掉的資料")
    ok("損壞資料：主資料沒有被覆蓋", pg.evaluate("localStorage.getItem('lifebox_v1')")=="{壞掉的資料")
    ok("損壞資料：顯示保護提示與處理選項", pg.locator('.lockbar').count()==1 and "下載原始內容" in pg.inner_text('#sheet'))
    ok("損壞資料：原始內容另存一份備份", any(x['data']=="{壞掉的資料" for x in bks(pg)))
    pg.click('#sheet [data-opt="3"]'); pg.click('[data-tab=todo]'); pg.fill('#quickInput','測試', timeout=1500) if pg.locator('#quickInput').count() else None
    pg.evaluate("Store.save && save()")
    ok("損壞資料：操作後仍不寫入", pg.evaluate("localStorage.getItem('lifebox_v1')")=="{壞掉的資料")
    pg.click('[data-lockopen]'); pg.click('#sheet [data-opt="2"]'); pg.click('#sheet [data-opt="0"]')
    ok("確認「重新開始」後才寫入新資料", st(pg) and st(pg)['schemaVersion']==5 and pg.locator('.lockbar').count()==0)
    ok("損壞情境沒有程式錯誤", not errs, errs); ctx.close()
    # ===== P0：升級前備份失敗 =====
    ctx=b.new_context(viewport={'width':390,'height':844},timezone_id='Asia/Taipei'); pg=ctx.new_page(); pg.clock.install(time=T0)
    pg.goto(URL); pg.evaluate("d=>{localStorage.clear();localStorage.setItem('lifebox_v1',JSON.stringify(d))}", v4)
    ctx.add_init_script("const _s=Storage.prototype.setItem; Storage.prototype.setItem=function(k,v){ if(k==='lifebox_v1_backups') throw new Error('QuotaExceeded'); return _s.call(this,k,v); }")
    pg.reload(); pg.wait_for_timeout(300)
    ok("升級前備份失敗：停止升級、不寫入", st(pg)['schemaVersion']==4 and pg.locator('.lockbar').count()==1 and "匯出備份" in pg.inner_text('#sheet'))
    ctx.close()
    # ===== 正常升級 v4 → v5 =====
    ctx,pg,errs=fresh(b,v4)
    s=st(pg)
    ok("升級到版本 5，原資料完整保留", s['schemaVersion']==5 and len(s['todos'])==1 and len(s['wishlist'])==2 and s['cards']==v4['cards'])
    ok("升級前備份，原因寫明版本 4 → 5", any("版本 4 → 5" in x['reason'] and json.loads(x['data'])['schemaVersion']==4 for x in bks(pg)))
    ok("建立 star 資料區與個人亂數種子", isinstance(s['star']['draws'],list) and len(s['star']['profile']['seed'])>4)
    w1,w2=s['wishlist']
    ok("舊願望補上顯化欄位（分類對應）", w1['category']=="travel" and w1['mstatus']=="manifesting" and w1['desc']=="秋天" and w1['budget']==30000)
    ok("已完成的舊願望 → 已實現，保留完成日與花費", w2['mstatus']=="achieved" and w2['doneDate']=="2026-10-01" and w2['actualCost']==18000 and w2['category']=="goods")
    pg.reload(); pg.wait_for_timeout(200)
    ok("再次載入不重複升級（seed 不變）", st(pg)['star']['profile']['seed']==s['star']['profile']['seed'] and len([x for x in bks(pg) if '升級' in x['reason']])==1)
    # 導覽
    tabs=[x.inner_text().strip().split("\n")[0] for x in pg.locator('#tabbar button').all()]
    ok("第五個分頁改名為星光秘境", tabs==["今日","收集","待辦","安排","星光秘境"], tabs)
    ok("首頁：今日肯定語取代療癒語錄", "今日肯定語" in pg.inner_text('#app') and "今日療癒語錄" not in pg.inner_text('#app'))
    ok("首頁 emoji 標題", "✅ 今天的待辦" in pg.inner_text('#app') and "🌱 成長與生活管理" in pg.inner_text('#app'))
    # 復原刪除
    pg.click('[data-tab=todo]'); pg.wait_for_timeout(100)
    if pg.locator('[data-del]').count():
        pg.locator('[data-del]').first.click()
        ok("刪除待辦後出現「復原」", pg.locator('#undo.show').count()==1 and len(st(pg)['todos'])==0)
        pg.click('#undoBtn'); ok("按復原，待辦完整回來", len(st(pg)['todos'])==1 and st(pg)['todos'][0]['title']=="剪影片")
    else: ok("刪除按鈕存在", False)
    # ===== 星光秘境 =====
    pg.click('[data-tab=card]')
    a1=pg.inner_text('.cosmic')
    pg.click('.stool[data-sp=oracle]'); pg.click('[data-odraw=daily]'); pg.wait_for_timeout(100)
    d=st(pg)['star']['draws']; ok("每日神諭卡：抽一張並保存", len(d)==1 and d[0]['tool']=="oracle" and pg.locator('.ocard').count()==1)
    card1=d[0]['cards'][0]['cardId']
    ok("神諭卡標示原創與娛樂", "娛樂與自我反思" in pg.inner_text('#app'))
    pg.reload(); pg.wait_for_timeout(200); pg.click('[data-tab=card]'); pg.click('.stool[data-sp=oracle]')
    ok("每日一張：重新整理後同一張、不能重抽", pg.locator('[data-odraw=daily]').count()==0 and len(st(pg)['star']['draws'])==1)
    pg.click('.seg[data-seg=oracle] button[data-v=free]'); pg.click('[data-odraw=free]'); pg.click('[data-odraw=free]')
    ok("自由抽卡不限次數並保存", len([x for x in st(pg)['star']['draws'] if x['mode']=="free"])==2)
    pg.click('.seg[data-seg=oracle] button[data-v=theme]'); pg.click('[data-otheme]>>nth=0'); pg.click('[data-odraw=theme]')
    ok("主題抽卡附主題解讀", len([x for x in st(pg)['star']['draws'] if x['mode']=="theme"])==1)
    # 運勢籤
    pg.click('.sback'); pg.click('.stool[data-sp=fortune]'); pg.click('[data-fdraw]'); pg.clock.run_for(1200); pg.wait_for_timeout(100)
    f=[x for x in st(pg)['star']['draws'] if x['tool']=="fortune"]
    lv=pg.inner_text('.slv') if pg.locator('.slv').count() else ""
    ok("運勢籤：抽到並顯示六等級之一", len(f)==1 and lv in ["大吉","中吉","吉","小吉","平平","需要加油"], lv)
    ok("運勢籤：等級說明依序列出", pg.inner_text('.lvrow').split()==["大吉","中吉","吉","小吉","平平","需要加油"], pg.inner_text('.lvrow'))
    ok("舊版籤提示保留", "舊版籤" in pg.inner_text('#app'))
    # 三張牌
    pg.click('.sback'); pg.click('.stool[data-sp=spread]'); pg.fill('#sprQ','工作方向'); pg.click('[data-sprdraw]')
    sp=[x for x in st(pg)['star']['draws'] if x['tool']=="spread"]
    ok("三張牌：三張不重複、保存問題", len(sp)==1 and len(set(c['cardId'] for c in sp[0]['cards']))==3 and sp[0]['question']=="工作方向")
    ok("三張牌：標示整體統整不是 AI", "不是 AI" in pg.inner_text('#app'))
    # 肯定語
    pg.click('.sback'); pg.click('.stool[data-sp=affirm]'); pg.click('[data-afav]>>nth=0')
    ok("肯定語可收藏", any(x['fav'] for x in st(pg)['star']['affirmations']))
    # 願望（合併）
    pg.click('.sback'); pg.click('.stool[data-sp=wishes]')
    ok("顯化許願池顯示舊願望（同一份資料）", "去京都看紅葉" in pg.inner_text('#app') and "買相機" in pg.inner_text('#app'))
    pg.click('[data-wnew]'); pg.fill('#wTitle','存到旅遊基金'); pg.select_option('#wCat','wealth'); pg.fill('#wActNew','每月存五千'); pg.click('[data-wactadd]'); pg.click('[data-wsave]')
    w=[x for x in st(pg)['wishlist'] if x['title']=="存到旅遊基金"]
    ok("新增願望：分類、行動清單、舊欄位同步", len(w)==1 and w[0]['category']=="wealth" and w[0]['actions'][0]['text']=="每月存五千" and w[0]['status']=="want" and 'type' in w[0])
    wid=w[0]['id']
    pg.click(f'[data-wedit="{wid}"]'); pg.select_option('#wStatus','achieved'); pg.click('[data-wsave]')
    ok("標記已實現 → 詢問加入成功牆", "加入成功紀錄牆" in pg.inner_text('#sheet'))
    pg.click('#sheet [data-opt="0"]'); pg.fill('#sRef','真的做到了'); pg.click('[data-ssave]')
    s=st(pg); sc=s['star']['successes']; ww=[x for x in s['wishlist'] if x['id']==wid][0]
    ok("成功紀錄與願望互相連結，願望保留", len(sc)==1 and sc[0]['wishId']==wid and ww['successId']==sc[0]['id'] and ww['status']=="done" and ww['progress']==100)
    ok("成功紀錄保存願望原始快照", sc[0].get('originalSnapshot',{}).get('title')=="存到旅遊基金", sc[0].get('originalSnapshot'))
    pg.click('[data-tab=home]'); pg.click('.row[data-ghub=wish]')
    ok("成長 → 願望清單看得到同一個願望", "存到旅遊基金" in pg.inner_text('#app'))
    # 感恩 + 同步
    pg.click('[data-tab=card]'); pg.click('.stool[data-sp=gratitude]'); pg.fill('#gr0','家人'); pg.check('#grSync'); pg.click('[data-grsave]')
    s=st(pg); ok("感恩日記保存，勾選才同步到心情日記", len(s['star']['gratitude'])==1 and any(j.get('source')=="感恩日記" for j in s['journalEntries']))
    # 刪除的功能
    pg.click('.sback'); home=pg.inner_text('#app')
    ok("星座運勢、個人星盤、盧恩符文、易經都已移除", all(x not in home for x in ["星座運勢","個人星盤","盧恩","易經"]), home[:300])
    pg.click('.stool[data-sp=oracle]'); pg.click('.seg[data-seg=oracle] button[data-v=free]'); pg.click('[data-odraw=free]')
    ok("神諭卡顯示天使傳統：名字原意與出處", "名字原意" in pg.inner_text('#app') and "出處" in pg.inner_text('#app'))
    pg.click('.sback')
    # 天使數字、靈魂提問、月相
    pg.click('.stool[data-sp=angel]'); pg.click('[data-an]>>nth=0'); pg.click('[data-ansave]')
    ok("天使數字可記錄", len(st(pg)['star']['angelNumbers'])==1)
    pg.click('.sback'); pg.click('.stool[data-sp=soul]'); pg.fill('#soulA','想多休息'); pg.click('[data-soulsave]')
    ok("靈魂提問可回答", len(st(pg)['star']['soulQA'])==1)
    pg.click('.sback'); pg.click('.stool[data-sp=moon]')
    ok("月相日曆顯示 11/24 滿月", "滿月" in pg.inner_text('#app'))
    # 紀錄
    pg.click('.sback'); pg.click('.srow[data-sp=records]')
    n0=pg.locator('.rrow').count()
    ok("探索紀錄彙整各工具", n0>=7, n0)
    pg.click('[data-rt=oracle]'); ok("可依工具篩選", 0<pg.locator('.rrow').count()<n0)
    ok("全部頁面沒有程式錯誤", not errs, errs)
    ow=pg.evaluate("document.documentElement.scrollWidth"); ok("390px 不會水平溢出", ow<=390, ow)
    seedA=st(pg)['star']['profile']['seed']; affA=pg.evaluate("affToday().id"); oA=pg.evaluate("oracleFor(D.today()).id"); fA=pg.evaluate("fortuneFor(D.today()).id")
    ok("同一人同一天：每日卡固定", oA==card1)
    ctx.close()
    # 每個人不同
    diffs=0
    for i in range(6):
        ctx,pg2,_=fresh(b,v4); 
        if pg2.evaluate("[affToday().id,oracleFor(D.today()).id,fortuneFor(D.today()).id].join()")!=",".join([affA,oA,fA]): diffs+=1
        ctx.close()
    ok("不同人：每日內容隨機（6 人中至少 5 人不同）", diffs>=5, diffs)
    # 月相精確度
    ctx,pg,_=fresh(b,v4)
    ev=pg.evaluate("Moon.between('2026-01-01','2027-12-31').map(e=>[e.type,e.at instanceof Date?e.at.getTime():e.at])")
    ctx.close()
    js="""const A=require('astronomy-engine');const ev=%s;const q={new:0,first:90,full:180,last:270};let bad=[],mx=0;
    for(const [t,ms] of ev){ const r=A.SearchMoonPhase(q[t], new Date(ms-3*86400000), 6); const d=Math.abs(r.date.getTime()-ms)/60000; mx=Math.max(mx,d);
      const tw=x=>new Date(x+8*3600000).toISOString().slice(0,10); if(d>5||tw(ms)!==tw(r.date.getTime())) bad.push([t,new Date(ms).toISOString(),r.date.toISOString(),d.toFixed(1)]); }
    console.log(JSON.stringify({n:ev.length,mx,bad}));""" % json.dumps(ev)
    out=json.loads(subprocess.run(['node','-e',js],capture_output=True,text=True,cwd=str(__import__('pathlib').Path(__file__).parent)).stdout)
    ok(f"月相 2026–2027 共 {out['n']} 次，與 astronomy-engine 誤差 < 5 分鐘且台北日期相同（最大 {out['mx']:.1f} 分）", out['n']>=95 and not out['bad'], out['bad'][:3])
    b.close()
print("\n".join(R)); print(sum(r.startswith("PASS") for r in R),"/",len(R))
