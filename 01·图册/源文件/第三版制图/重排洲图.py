from pathlib import Path
import json,base64,importlib.util
import numpy as np
ROOT=Path(__file__).resolve().parents[2];O=Path(__file__).parent;STAGE=O/'待核图册'
spec=importlib.util.spec_from_file_location('political',O/'重绘政区.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
S=m.S
img=lambda p:'data:image/png;base64,'+base64.b64encode(Path(p).read_bytes()).decode()
out=['<svg xmlns="http://www.w3.org/2000/svg" width="10000" height="6667" viewBox="0 0 2400 1600">','<rect width="2400" height="1600" fill="#b4c9cd"/>',f'<image width="2400" height="1600" preserveAspectRatio="none" href="{img(S/"大洲海底·第二版生图底画.png")}"/>','<rect width="2400" height="1600" fill="#f7f2e6" opacity=".65"/>','<rect x="2110" width="290" height="1600" fill="#f6f0e3"/>',m.txt(60,80,'西 湾 盛 洲 政 区 图',38,anchor='start',halo=.5)]
y=130
for kind,dx,dy,scale in [('岚衡',25,160,.32),('洄原',650,680,.43),('燧岬',1400,690,.4)]:
    d=json.loads((STAGE/(kind+'·图层数据.json')).read_text(encoding='utf-8'));f=np.load(STAGE/(kind+'·行政栅格.npz'))['country'];unit=m.step
    land=' '.join(m.smoothpath(p['points'],True) for p in d['land_paths'] if len(p['points'])>3)
    out += [f'<defs><clipPath id="land{kind}"><path d="{land}" fill-rule="evenodd"/></clipPath></defs>',f'<g transform="translate({dx} {dy}) scale({scale})">',f'<image width="2100" height="1350" preserveAspectRatio="none" href="{img(d["background"])}" clip-path="url(#land{kind})"/>',f'<path d="{land}" fill="#fffbed" fill-rule="evenodd" opacity=".62"/>']
    for ci,ps in enumerate(d['country_paths']):
        p=' '.join(m.smoothpath(p['points'],True) for p in ps if len(p['points'])>3);out.append(f'<path d="{p}" fill="{m.COLORS[ci]}" opacity=".43" fill-rule="evenodd"/>')
    for p in d['national_boundaries']:out.append(f'<path d="{m.smoothpath(p["points"])}" fill="none" stroke="#6e3f52" stroke-width="2.4"/>')
    for ci,c in enumerate(d['countries'],1):
        text=c['label'];x,y=c['label_x'],c['label_y'];size=c.get('label_size',24)*1.5
        for shrink in [1,.9,.8,.7,.6]:
            ww=len(text)*size*shrink+(len(text)-1)*3;hh=size*shrink
            points=[(round((x+tx)/unit),round((y+ty)/unit)) for tx in [-ww/2,0,ww/2] for ty in [-hh/2,0,hh/2]]
            if all(0<=py<f.shape[0] and 0<=px<f.shape[1] and f[py,px]==ci for px,py in points):size*=shrink;break
        out.append(m.txt(x,y,text,size,spacing=3,halo=1.3))
    for isle in d.get('islands',[]):
        if isle['rx']<25:continue
        c=next(c for c in d['countries'] if c['code']==isle['country_code'])
        if (isle['x']-c['label_x'])**2+(isle['y']-c['label_y'])**2>150**2:out.append(m.txt(isle['x'],isle['y'],c['label']+'属',21,halo=1))
    out+=['</g>',m.txt(dx+160,dy-28,kind,29,spacing=7,halo=.5)]
    out.append(m.txt(2132,y,kind,24,anchor='start',spacing=4,halo=0));y+=39
    for c in d['countries']:out.append(m.txt(2132,y,c['code']+' '+c['name'],17,anchor='start',halo=0));y+=31
    y+=31
out += [m.txt(485,460,'沧 溟 远 海',32,'#52696c',halo=.5),m.txt(1325,620,'镜 门 海',25,'#52696c',halo=.5),m.txt(1270,1370,'南 部 诸 海',27,'#52696c',halo=.5),m.txt(60,1410,'北 ↑　实线为国界　国名以辖境标注',20,anchor='start',halo=.5),m.txt(60,1450,'共历742年秋　三大陆二十九国',19,anchor='start',halo=.5),m.txt(60,1490,'示意图；岛屿辖属、面积与实际航程以正文为准',18,anchor='start',halo=.5),'</svg>']
(STAGE/'00·西湾盛洲·三陆国界图.svg').write_text('\n'.join(out),encoding='utf-8');print('三陆政区洲图重排：国名替代图内代码')
