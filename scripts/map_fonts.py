from pathlib import Path
import urllib.request,urllib.parse,concurrent.futures,json
root=Path(__file__).resolve().parents[1]/'assets'/'map'
def one(pair):
    font,ran=pair;file=root/'fonts'/font/(ran+'.pbf');file.parent.mkdir(parents=True,exist_ok=True)
    if not file.exists():
        url='https://protomaps.github.io/basemaps-assets/fonts/'+urllib.parse.quote(font)+'/'+ran+'.pbf'
        with urllib.request.urlopen(url,timeout=60) as r:file.write_bytes(r.read())
    return str(file)
fonts=['Noto Sans Regular','Noto Sans Medium','Noto Sans Italic','Noto Sans Devanagari Regular v1']
ranges=['0-255','256-511','512-767','768-1023','2304-2559','8192-8447','8448-8703','63488-63743','64256-64511','65024-65279']
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as p:list(p.map(one,[(f,r) for f in fonts for r in ranges]))
for suffix in ['.json','.png','@2x.json','@2x.png']:
    file=root/('dark'+suffix)
    if not file.exists():
        with urllib.request.urlopen('https://protomaps.github.io/basemaps-assets/sprites/v4/dark'+suffix,timeout=60) as r:file.write_bytes(r.read())
print('Local glyphs and sprites ready')
