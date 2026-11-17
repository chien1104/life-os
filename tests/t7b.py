# 第 7 組：確認 App 已完全移除 AI 與雲端同步（即使在 Claude 環境中打開也一樣）
from playwright.sync_api import sync_playwright
import json, datetime
from pathlib import Path
HERE=Path(__file__).resolve().parent; OUT=HERE/'out'; OUT.mkdir(exist_ok=True)
URL=HERE.parent.joinpath('index.html').as_uri()
R=[]
def ok(n,c,extra=""): R.append(("PASS" if c else "FAIL")+"  "+n+(("  ["+str(extra)[:200]+"]") if (not c and extra!="") else ""))
TZ=datetime.timezone(datetime.timedelta(hours=8))
T0=datetime.datetime(2026,11,13,9,0,tzinfo=TZ)
PAGES=[("home",None),("collect",None),("todo",None),("plan",None),("card",None)]
HUBS=["habit","mood","review","goal","wish","content","fin","kb","report","reward"]
with sync_playwright() as p:
    b=p.chromium.launch()
    for label,mock in [("一般網址",False),("Claude 環境",True)]:
        ctx=b.new_context(viewport={'width':390,'height':844},timezone_id='Asia/Taipei')
        if mock: ctx.add_init_script(path=str(HERE/'mock.js'))
        pg=ctx.new_page(); errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)))
        pg.clock.install(time=T0); pg.goto(URL); pg.wait_for_timeout(400); pg.clock.run_for(3000)
        ok(f"{label}：第一次打開顯示歡迎說明，沒有 AI 字樣", pg.locator('#sheet.show').count()==1 and "AI" not in pg.inner_text('#sheet') and "Claude" not in pg.inner_text('#sheet'))
        if pg.locator('#sheet.show').count(): pg.click('#sheet [data-act=close]')
        texts=[]
        for t,_ in PAGES:
            pg.click(f'[data-tab={t}]'); texts.append(pg.inner_text('#app'))
        pg.click('[data-tab=home]')
        for h in HUBS:
            pg.evaluate(f"go('growth',{{keepHub:true}}); hub='{h}'; render();") if False else None
            pg.click('[data-tab=home]'); pg.click(f'.row[data-ghub={h}]'); texts.append(pg.inner_text('#app'))
        all_t="\n".join(texts)
        ok(f"{label}：所有分頁與成長子頁都沒有 AI 按鈕或字樣", "AI" not in all_t and pg.locator('.aibtn').count()==0, [l for l in all_t.split("\n") if "AI" in l][:3])
        pg.click('#btnSettings'); st_txt=pg.inner_text('#sheet')
        ok(f"{label}：設定頁沒有 AI 與雲端同步", "AI" not in st_txt and "雲端同步" not in st_txt.replace("目前沒有帳號與雲端同步",""), st_txt[:200])
        pg.click('#sheet [data-act=close]') if pg.locator('#sheet [data-act=close]').count() else pg.keyboard.press('Escape')
        # 收集照常可用（規則整理）
        pg.click('[data-tab=collect]'); pg.fill('#captureInput','明天交提案給客戶'); pg.click('#btnOrganize'); pg.wait_for_timeout(200)
        ok(f"{label}：收集用規則整理出預覽", pg.locator('.rcard').count()==1)
        ok(f"{label}：沒有程式錯誤", not errs, errs)
        if mock:
            pg.wait_for_timeout(500); pg.clock.run_for(5000)
            ok("Claude 環境：不會寫入任何雲端資料", pg.evaluate("Object.keys(window.__store||{}).length")==0, pg.evaluate("Object.keys(window.__store||{})"))
            ok("Claude 環境：資料存在本機", pg.evaluate("!!localStorage.getItem('lifebox_v1')"))
        ctx.close()
    b.close()
print("\n".join(R)); print(sum(r.startswith("PASS") for r in R),"/",len(R))
