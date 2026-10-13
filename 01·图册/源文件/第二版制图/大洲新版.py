from pathlib import Path
import json,base64
from html import escape
A=Path(r'D:\dreaming\西湾盛洲志\01·图册');S=A/'源文件'
def img(p):return 'data:image/png;base64,'+base64.b64encode(Path(p).read_bytes()).decode()
def line(p):return 'M '+' L '.join(f'{x:.1f},{y:.1f}' for x,y in p)
def txt(x,y,s,z=17):return f'<text x="{x}" y="{y}" font-size="{z}" fill="#302d24" stroke="#fff3db" stroke-width="2" paint-order="stroke">{escape(s)}</text>'
out=['<svg xmlns="http://www.w3.org/2000/svg" width="10000" height="6667" viewBox="0 0 2400 1600"><g font-family="Microsoft YaHei, SimSun, sans-serif">','<rect width="2400" height="1600" fill="#275e73"/>',f'<image width="2400" height="1600" preserveAspectRatio="none" href="{img(S/"大洲海底·第二版生图底画.png")}"/>','<rect x="2110" width="290" height="1600" fill="#eee2c8" opacity=".97"/>',txt(62,85,'西湾盛洲·三陆国界图',38)]
legend=130
for k,dx,dy,scale in [('岚衡',25,160,.32),('洄原',650,680,.43),('燧岬',1400,690,.4)]:
 d=json.loads((S/(k+'·图层数据.json')).read_text(encoding='utf-8'));paths=' '.join(line(p['points'])+' Z' for p in d['land_paths'] if len(p['points'])>3)
 out += [f'<defs><clipPath id="clip{k}"><path d="{paths}" fill-rule="evenodd"/></clipPath></defs>',f'<g transform="translate({dx} {dy}) scale({scale})">',f'<image width="{d["width"]}" height="{d["height"]}" href="{img(d["background"])}" clip-path="url(#clip{k})"/>',f'<path d="{paths}" fill="none" stroke="#f5e7c1" stroke-width="2"/>']
 for p in d['national_boundaries']:out.append(f'<path d="{line(p["points"])}" fill="none" stroke="#a53328" stroke-width="4"/>')
 for c in d['countries']:out.append(txt(c['x']-14,c['y'],c['code'],29))
 for r in d.get('islands',[]):
  if r['rx']>25:out.append(txt(r['x']-14,r['y'],r['country_code'],24))
 out.append('</g>');out.append(txt(dx+175,dy-30,k,27));out.append(txt(2130,legend,k,23));legend+=38
 for c in d['countries']:out.append(txt(2130,legend,c['code']+' '+c['name'],17));legend+=31
 legend+=30
out += [txt(480,495,'沧溟远海',35),txt(1345,610,'镜门海',29),txt(1270,1360,'南部诸海',28),txt(65,1405,'北 ↑　红线为国界　岛屿合隶其国家',21),txt(65,1445,'共历742年秋 · 三大陆二十九国',20),txt(65,1485,'方位与疆域示意；岛屿间距、面积和海路长度以正文为准',18),txt(490,620,'岚衡—洄原最近适航海路2400—3000公里',19),txt(1370,565,'镜门常用港路300—850公里',18),'</g></svg>']
(A/'00·西湾盛洲·三陆国界图.svg').write_text('\n'.join(out),encoding='utf-8');print('洲图10000像素宽、29国')
