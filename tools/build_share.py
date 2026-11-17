"""從 index.html（🌻芊的工具檯）產生分享版「🌻生活工具檯」。
用法：python tools/build_share.py <分享版資料夾>   例如 ../life-tools
會覆寫該資料夾的 index.html、manifest.webmanifest、sw.js、icons/。"""
import sys, re, shutil
from pathlib import Path
SRC = Path(__file__).resolve().parents[1]
DST = Path(sys.argv[1]).resolve()
s = (SRC/'index.html').read_text(encoding='utf-8')
s = s.replace('🌻芊的工具檯','🌻生活工具檯').replace('content="芊的工具檯"','content="生活工具檯"').replace('"芊的工具檯・星光秘境 探索紀錄"','"生活工具檯・星光秘境 探索紀錄"')
s = s.replace('LifeOS備份_${D.today()}.json','生活工具檯備份_${D.today()}.json')
css = '''
.phone{padding-bottom:calc(150px + env(safe-area-inset-bottom))}
.copyfoot{margin:22px 18px 0;padding:14px 4px 0;border-top:1px dashed var(--line);text-align:center;font-size:11.5px;line-height:1.75;color:var(--coffee-soft)}
.copyfoot b{color:var(--coffee);font-weight:600}
.starwrap .copyfoot{border-top-color:rgba(232,216,191,.18);color:#c9bfd8}
.starwrap .copyfoot b{color:#e3c58d}
'''
a = '.grid2>*,.fld,.hrow>*{min-width:0}'
assert s.count(a)==1; s = s.replace(a, css+a)
r = 'render=function(){ _render0();'
assert s.count(r)==1
s = s.replace(r, 'const COPY_FOOT=`<div class="copyfoot"><b>@Chien1104</b></div>`;\n'+r+' (()=>{ const host=$("app").querySelector(".starwrap")||$("app"); host.insertAdjacentHTML("beforeend", COPY_FOOT); })();')
assert '芊' not in s, '分享版裡還有「芊」'
(DST/'index.html').write_text(s, encoding='utf-8')
m = (SRC/'manifest.webmanifest').read_text(encoding='utf-8').replace('🌻芊的工具檯','🌻生活工具檯').replace('"芊的工具檯"','"生活工具檯"')
(DST/'manifest.webmanifest').write_text(m, encoding='utf-8')
w = (SRC/'sw.js').read_text(encoding='utf-8').replace('🌻芊的工具檯','🌻生活工具檯')
w = re.sub(r'const CACHE = "qian-tools-v(\d+)";', lambda mm: f'const CACHE = "life-tools-v{mm.group(1)}";', w)
(DST/'sw.js').write_text(w, encoding='utf-8')
shutil.copytree(SRC/'icons', DST/'icons', dirs_exist_ok=True)
print('分享版已產生：', DST)
