from pathlib import Path
import json,base64
from html import escape
A=Path(r'D:\dreaming\西湾盛洲志\01·图册');S=A/'源文件'
def img(p):return 'data:image/png;base64,'+base64.b64encode(Path(p).read_bytes()).decode()
def line(p):return 'M '+' L '.join(f'{x:.1f},{y:.1f}' for x,y in p)
def coast(p):
 q=p[:-1] if p[0]==p[-1] else p
 if len(q)<4:return line(p)+' Z'
 mid=lambda a,b:((a[0]+b[0])/2,(a[1]+b[1])/2)
 a=mid(q[-1],q[0]);r=f'M {a[0]},{a[1]}'
 for i,v in enumerate(q):
  b=mid(v,q[(i+1)%len(q)]);r+=f' Q {v[0]},{v[1]} {b[0]},{b[1]}'
 return r+' Z'
def txt(x,y,s,z=14):return f'<text x="{x}" y="{y}" font-size="{z}" fill="#302d24" stroke="#fff3db" stroke-width="2" paint-order="stroke">{escape(s)}</text>'
out=['<svg xmlns="http://www.w3.org/2000/svg" width="4000" height="2502" viewBox="0 0 1586 992"><g font-family="Microsoft YaHei, SimSun, sans-serif">',f'<image width="1586" height="992" href="{img(S/"大洲海底·生图底画.png")}"/>',txt(52,77,'西湾盛洲·三陆国界图',29)]
legend=100
for k,dx,dy,scale in [('岚衡',0,85,.275),('洄原',465,375,.35),('燧岬',920,405,.32)]:
 d=json.loads((S/(k+'·图层数据.json')).read_text(encoding='utf8'))
 paths=' '.join(coast(p['points']) for p in d['land_paths'] if len(p['points'])>3)
 out += [f'<defs><clipPath id="clip{k}"><path d="{paths}" fill-rule="evenodd"/></clipPath></defs>',f'<g transform="translate({dx} {dy}) scale({scale})">',f'<image width="{d["width"]}" height="{d["height"]}" href="{img(d["background"])}" clip-path="url(#clip{k})"/>',f'<path d="{paths}" fill="none" stroke="#f6e9c1" stroke-width="2"/>']
 for p in d['national_boundaries']:out.append(f'<path d="{line(p["points"])}" fill="none" stroke="#9c3026" stroke-width="3.5"/>')
 for c in d['countries']:out.append(txt(c['x']-14,c['y'],c['code'],27))
 out.append('</g>');lx,ly={'岚衡':(360,160),'洄原':(625,750),'燧岬':(1070,780)}[k];out.append(txt(lx,ly,k+'大陆',20))
 out.append(txt(1320,legend,k+'大陆',18));legend+=27
 for c in d['countries']:out.append(txt(1320,legend,c['code']+' '+c['name'],13));legend+=22
 legend+=20
out += [txt(365,315,'沧溟远海',25),txt(850,360,'镜门海',21),txt(750,875,'南部诸海',20),txt(62,870,'国界：红线   北 ↑',17),txt(62,903,'共历742年秋 · 三大陆二十九国',15),txt(62,931,'方位与疆域示意；海距以正文航路记载为准',13),txt(370,840,'岚衡—洄原适航2400—3000公里',14),txt(940,865,'镜门常用港路300—850公里',13),'</g></svg>']
(A/'00·西湾盛洲·三陆国界图.svg').write_text('\n'.join(out),encoding='utf8')
print('洲图：29国；国界复用三张大陆图的同一图层')
