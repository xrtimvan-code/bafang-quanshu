from pathlib import Path
import json, math, base64, importlib.util
import numpy as np
from PIL import Image, ImageDraw
ROOT=Path(__file__).resolve().parents[3];B=Path(r'D:\dreaming\西湾盛洲志');A=B/'01·图册';S=A/'源文件';O=Path(__file__).parent
spec=importlib.util.spec_from_file_location('geo',Path(__file__).parent/'绘图函数.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
W,H,P,step=2100,1350,1600,3
def prepare():
 d=json.loads((S/'岚衡·图层数据.json').read_text(encoding='utf-8'));mask=Image.new('L',(math.ceil(P/step),H//step));dr=ImageDraw.Draw(mask)
 for p in d['land_paths']:
  if len(p['points'])>3:dr.polygon([(x/step,y/step) for x,y in p['points']],fill=255)
 field=np.array(mask)>0;yy,xx=np.mgrid[:field.shape[0],:field.shape[1]];X=xx*step;Y=yy*step;isles=[]
 for gi,(ci,name,cx,cy,rx,ry) in enumerate([(1,'外海岛盟',60,1050,28,52),(1,'外海岛盟',125,95,43,64),(7,'舟列府',1440,715,66,112),(7,'舟列府',1390,1130,58,30)]):
  for j in range(6):
   if j==0:sx,sy,ax,ay=cx,cy,rx,ry
   else:sx=cx+math.cos(j*1.9+gi)*(rx+20+j*9);sy=cy+math.sin(j*1.9+gi)*(ry+25+j*10);ax=5+j*2;ay=8+((j+gi)*7)%19
   aa=np.arctan2((Y-sy)/ay,(X-sx)/ax);rr=np.sqrt(((X-sx)/ax)**2+((Y-sy)/ay)**2);sm=(rr<1+.17*np.sin(3*aa+gi)+.1*np.sin(7*aa+j))&~field
   if sx<10 or sx>P-10 or sy<100 or sy>H-30:continue
   field|=sm;paths=m.boundaries(sm.astype(np.int16),False,step,include_zero=True)
   isles.append(dict(country_code=f'L{ci:02}',district_name=name,x=sx,y=sy,rx=ax,ry=ay,paths=paths))
 d['land_paths']=m.boundaries(field.astype(np.int16),False,step,include_zero=True);d['width']=W;d['height']=H;d['islands']=isles
 (O/'岚衡·新图层.json').write_text(json.dumps(d,ensure_ascii=False,indent=2,default=lambda v:v.item()),encoding='utf-8')
 im=Image.new('RGB',(W,H),'#b9d4d5');draw=ImageDraw.Draw(im)
 for p in d['land_paths']:
  if len(p['points'])>3:draw.polygon(p['points'],fill='#e8d9b8',outline='#62563e')
 draw.rectangle((P,0,W,H),fill='#eee1c4');im.save(O/'岚衡·海岸引导.png');print('岚衡新增岛形',len(isles))
def render(bg):
 import re
 original_svg=(A/'01·岚衡大陆·疆域地形图.svg').read_text(encoding='utf-8')
 d=json.loads((O/'岚衡·新图层.json').read_text(encoding='utf-8'));d['background']=bg;b64=base64.b64encode(Path(bg).read_bytes()).decode()
 out=[f'<svg xmlns="http://www.w3.org/2000/svg" width="8000" height="5143" viewBox="0 0 {W} {H}">','<style>text{font-family:"Microsoft YaHei",SimSun,sans-serif}</style>',f'<image width="{W}" height="{H}" href="data:image/png;base64,{b64}"/>',f'<rect x="{P}" width="500" height="{H}" fill="#eee2c9" opacity=".97"/>',m.text(45,60,'岚衡·疆域与地方行政',28,anchor='start',bold=True),m.text(45,86,'共历742年秋　七国三十七区',13,anchor='start')]
 for paths,color,weight,dash in [(d['district_boundaries'],'#385961',1.3,'4 2'),(d['national_boundaries'],'#a33328',2.1,'')]:
  for p in paths:out.append(f'<path d="{m.path_d(p["points"])}" fill="none" stroke="#f8edcf" stroke-width="{weight+2}"/><path d="{m.path_d(p["points"])}" fill="none" stroke="{color}" stroke-width="{weight}" stroke-dasharray="{dash}"/>')
 for r in d['districts']:
  x,y=r.get('label_x',r['x']),r.get('label_y',r['y']);out.append(f'<rect x="{x-13}" y="{y-8}" width="26" height="16" rx="3" fill="#fff3d9"/>');out.append(m.text(x,y+3,r['mark'],10,halo=False))
 for c in d['countries']:out.append(m.text(c['x'],c.get('name_y',c['y'])-23,c['code']+' '+c['name'],15,bold=True))
 out.extend(re.findall(r'<text[^>]*>★[^<]+</text>',original_svg))
 for isle in d['islands']:
  if isle['rx']>25:
   unit=next(r for r in d['districts'] if r['name']==isle['district_name']);out.append(m.text(isle['x'],isle['y'],unit['name']+'('+unit['mark']+')',10))
 x,y=P+22,68;out.append(m.text(x,y,'二级行政区索引',19,anchor='start',bold=True,halo=False));y+=34
 for ci,c in enumerate(d['countries']):
  if ci==4:x=P+255;y=102
  out.append(m.text(x,y,c['code']+' '+c['name'],13,anchor='start',bold=True,halo=False));y+=26
  for r in c['districts']:out.append(m.text(x,y,r['mark']+' '+r['name'],12,anchor='start',halo=False));y+=24
  y+=16
 out+=[m.text(P+22,1120,'红实线：国界　蓝虚线：二级区界',12,anchor='start',halo=False),m.text(P+22,1150,'北 ↑　属岛合隶外海岛盟、舟列府',12,anchor='start',halo=False),m.text(P+22,1180,'各区治所、官员与人口见国家志',12,anchor='start',halo=False),'</svg>']
 (A/'01·岚衡大陆·疆域地形图.svg').write_text('\n'.join(out),encoding='utf-8');(S/'岚衡·图层数据.json').write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8')
if __name__=='__main__':
 import sys
 if sys.argv[1]=='prepare':prepare()
 else:render(sys.argv[2])
