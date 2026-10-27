from pathlib import Path
import json, math, sys, importlib.util
import numpy as np
from PIL import Image, ImageDraw

ROOT=Path(__file__).resolve().parents[3]
BOOK=Path(r'D:\dreaming\西湾盛洲志'); ATLAS=BOOK/'01·图册';SOURCE=ATLAS/'源文件'
OUT=Path(__file__).parent;OUT.mkdir(parents=True,exist_ok=True)
spec=importlib.util.spec_from_file_location('cartography',Path(__file__).parent/'绘图函数.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
W,H,PANEL,STEP=2100,1350,1600,3

BASELINE=SOURCE/'第二版基线'
def read(kind):return json.loads((BASELINE/(kind+'·图层数据.json')).read_text(encoding='utf-8'))
def prepare(kind):
    old=read(kind);oldgrid=np.load(BASELINE/(kind+'·行政栅格.npz'))
    field=np.zeros((H//STEP,math.ceil(PANEL/STEP)),np.int16);parents=np.zeros_like(field)
    of=oldgrid['country'];od=oldgrid['district'];field[:of.shape[0],:of.shape[1]]=of;parents[:od.shape[0],:od.shape[1]]=od
    new=json.loads((SOURCE/(kind+'·行政原始数据.json')).read_text(encoding='utf-8'))
    countries=new['countries']; yy,xx=np.mgrid[:field.shape[0],:field.shape[1]];X=xx*STEP;Y=yy*STEP
    # The new sea margin contains distinct shelf islands and distant volcanic chains.
    if kind=='洄原':
        groups=[(12,6,1430,145,65,115),(12,7,1470,505,83,52),(12,8,1420,1070,42,64),
        (5,5,45,920,30,55),(6,2,410,1060,49,33),(9,5,1000,1040,61,30),(11,3,1260,845,24,45)]
    else:
        groups=[(10,6,115,1080,65,80),(10,7,70,1220,29,46),(10,10,330,1140,77,45),
        (9,8,70,155,48,38),(3,3,1400,380,54,105),(4,3,1410,770,75,40),(7,4,1060,1170,56,26),(8,3,625,1185,30,46)]
    island_records=[]
    for gi,(ci,di,cx,cy,rx,ry) in enumerate(groups):
        # Different angular spectra create long, broken, forked and steep island coasts.
        a=np.arctan2((Y-cy)/ry,(X-cx)/rx);r=np.sqrt(((X-cx)/rx)**2+((Y-cy)/ry)**2)
        edge=1+.24*np.sin(2*a+gi)+.16*np.sin(5*a+gi*.7)+.08*np.sin(11*a+gi)
        mask=(r<edge)&(field==0);field[mask]=ci
        island_records.append(dict(country_code=countries[ci-1]['code'],district_code=countries[ci-1]['districts'][di-1]['code'],x=cx,y=cy,rx=rx,ry=ry,kind='主岛'))
        # Shelf satellites vary in distance and do not each form a separate province.
        for j in range(3+gi%3):
            ang=gi*.63+j*2.13;dist=1.3+.3*j
            sx=cx+math.cos(ang)*rx*dist;sy=cy+math.sin(ang)*ry*dist
            ax=5+(gi*7+j*11)%14;ay=6+(gi*11+j*5)%17
            aa=np.arctan2((Y-sy)/ay,(X-sx)/ax);rr=np.sqrt(((X-sx)/ax)**2+((Y-sy)/ay)**2)
            sm=(rr<1+.2*np.sin(3*aa+j)+.08*np.sin(7*aa))&(field==0)
            if sx<10 or sx>PANEL-10 or sy<110 or sy>H-30:continue
            field[sm]=ci;island_records.append(dict(country_code=countries[ci-1]['code'],district_code=countries[ci-1]['districts'][di-1]['code'],x=sx,y=sy,rx=ax,ry=ay,kind='附岛'))
    districts=np.zeros_like(field);rows=[]
    oldby={(r['country_code'],r['name']):i+1 for i,r in enumerate(old['districts'])}
    for ci,c in enumerate(countries,1):
        oldc=next(x for x in old['countries'] if x['code']==c['code'])
        c['x'],c['y']=oldc['x'],oldc['y'];c['name_y']=oldc.get('name_y',c['y'])
        for group in c['historical_groups']:
            all_ds=[r for r in c['districts'] if r['parent_group']==group]
            remote=[r for r in all_ds if int(r['code'][-2:])>5 and ('岛' in r['name'] or '礁' in r['name'])]
            ds=[r for r in all_ds if r not in remote]
            oldid=oldby[(c['code'],group)];cells=np.argwhere(parents==oldid)
            # Place core and new seats within their own historical region.
            core=next(r for r in old['districts'] if r['code']==ds[0]['code'])
            points=[np.array([core['y']/STEP,core['x']/STEP])]
            for di in range(1,len(ds)):
                distances=np.min(np.array([((cells-p)**2).sum(axis=1) for p in points]),axis=0)
                p=cells[np.argmax(distances)];points.append(p)
            # Unequal weights reflect accessible valley cores and extensive sparse hinterlands.
            scores=np.array([((yy-p[0])**2+(xx-p[1])**2)/(d.get('area_weight',1)**.65) for p,d in zip(points,ds)])
            choice=np.argmin(scores,axis=0)
            for di,(d,p) in enumerate(zip(ds,points)):
                idx=len(rows)+1;mask=(parents==oldid)&(choice==di);districts[mask]=idx
                if not np.any(mask):raise ValueError('missing province '+d['code'])
                d['x'],d['y']=int(p[1]*STEP),int(p[0]*STEP);d['mark']=d['code'].replace('-','·');rows.append(dict(d,country_code=c['code']))
            for d in remote:
                isle=next(i for i in island_records if i['district_code']==d['code'] and i['kind']=='主岛')
                d['x'],d['y']=isle['x'],isle['y'];d['mark']=d['code'].replace('-','·');rows.append(dict(d,country_code=c['code']))
    # Index rows in code order to match the book's administrative register.
    ordered=sorted(rows,key=lambda r:r['code']);renumber={r['code']:i+1 for i,r in enumerate(ordered)}
    oldnumber={i+1:r['code'] for i,r in enumerate(rows)};lookup=np.array([0]+[renumber[oldnumber[i]] for i in range(1,len(rows)+1)])
    districts=lookup[districts].astype(np.int16);rows=ordered
    # Assign every added island explicitly, not by nearest mainland district.
    for r in island_records:
        ci=int(r['country_code'][1:]);a=np.arctan2((Y-r['y'])/r['ry'],(X-r['x'])/r['rx']);rad=np.sqrt(((X-r['x'])/r['rx'])**2+((Y-r['y'])/r['ry'])**2)
        mask=(rad<1.8)&(parents==0)&(field==ci)&(districts==0);districts[mask]=renumber[r['district_code']]
    # Any remaining coast sliver goes to a district of that country.
    for ci,c in enumerate(countries,1):
        missing=(field==ci)&(districts==0)
        if missing.any():districts[missing]=renumber[c['districts'][0]['code']]
    for c in countries:c['districts']=[r for r in rows if r['country_code']==c['code']]
    nat=m.boundaries(field,True,STEP);local=m.boundaries(districts,False,STEP)
    local=[p for p in local if rows[p['pair'][0]-1]['country_code']==rows[p['pair'][1]-1]['country_code']]
    land=m.boundaries((field>0).astype(np.int16),False,STEP,include_zero=True)
    record=dict(continent=kind,width=W,height=H,country_count=len(countries),district_count=len(rows),countries=countries,districts=rows,national_boundaries=nat,district_boundaries=local,land_paths=land,islands=island_records,note='北向上；疆域方位示意，非等面积投影；附岛合隶其区。')
    (OUT/(kind+'·新图层.json')).write_text(json.dumps(record,ensure_ascii=False,indent=2,default=lambda v:v.item()),encoding='utf-8')
    np.savez_compressed(OUT/(kind+'·新栅格.npz'),country=field,district=districts,step=STEP)
    # New guide drawn from geometry, not an edit of the existing raster artwork.
    guide=Image.new('RGB',(W,H),'#b9d4d5');draw=ImageDraw.Draw(guide)
    for p in land:
        if len(p['points'])>3:draw.polygon(p['points'],fill='#e8d9b8',outline='#62563e')
    draw.rectangle((PANEL,0,W,H),fill='#eee1c4');guide.save(OUT/(kind+'·海岸引导.png'))
    print(kind,len(rows),'new island shapes',len(island_records))

def render(kind,background):
    import base64
    from html import escape
    d=json.loads((OUT/(kind+'·新图层.json')).read_text(encoding='utf-8'));grid=np.load(OUT/(kind+'·新栅格.npz'));field=grid['district']
    b64=base64.b64encode(Path(background).read_bytes()).decode()
    d['background']=str(background)
    p=[f'<svg xmlns="http://www.w3.org/2000/svg" width="8000" height="5143" viewBox="0 0 {W} {H}">','<style>text{font-family:"Microsoft YaHei","SimSun",sans-serif}</style>',f'<image width="{W}" height="{H}" href="data:image/png;base64,{b64}"/>',f'<rect x="{PANEL}" width="{W-PANEL}" height="{H}" fill="#eee2c9" opacity=".96"/>']
    for b in d['district_boundaries']:p.append(f'<path d="{m.path_d(b["points"])}" fill="none" stroke="#fbefd5" stroke-width="3"/><path d="{m.path_d(b["points"])}" fill="none" stroke="#3d5962" stroke-width="1.3" stroke-dasharray="4 2"/>')
    for b in d['national_boundaries']:p.append(f'<path d="{m.path_d(b["points"])}" fill="none" stroke="#fbefd5" stroke-width="4"/><path d="{m.path_d(b["points"])}" fill="none" stroke="#a33328" stroke-width="2.1"/>')
    p.append(m.text(45,55,kind+'·疆域与地方行政',27,anchor='start',bold=True));p.append(m.text(45,82,f"共历742年秋　{d['country_count']}国 · {d['district_count']}个二级区",13,anchor='start'))
    placed=[]
    for i,r in enumerate(d['districts'],1):
        cells=np.argwhere(field==i);ctr=cells.mean(axis=0);order=np.argsort(((cells-ctr)**2).sum(axis=1));candidates=[(r['x'],r['y'])]+[(int(cells[j,1]*STEP),int(cells[j,0]*STEP)) for j in order[::max(1,len(order)//200)]]
        clear=lambda x,y:all(abs(x-a)>50 or abs(y-b)>20 for a,b in placed)
        chosen=next((q for q in candidates if clear(*q)),None)
        if chosen is None:chosen=next(((r['x']+dx,r['y']+dy) for dy in [24,-24,48,-48,72,-72] for dx in [0,35,-35,70,-70] if clear(r['x']+dx,r['y']+dy)),None)
        if chosen is None:raise ValueError('label crowded '+r['code'])
        x,y=chosen;r['label_x'],r['label_y']=x,y;placed.append(chosen)
        if chosen!=(r['x'],r['y']):p.append(f'<path d="M {r["x"]},{r["y"]} L {x},{y}" stroke="#443d31" stroke-width=".7"/>')
        p.append(f'<rect x="{x-24}" y="{y-8}" width="48" height="16" rx="3" fill="#fff4dc" stroke="#71614b" stroke-width=".5"/>');p.append(m.text(x,y+3,r['mark'],8.5,halo=False))
    for c in d['countries']:
        p.append(m.text(c['x'],c['name_y']-22,c['code']+' '+c['name'],15,bold=True))
        cap=next((r for r in c['districts'] if r['seat']==c['capital']),c['districts'][0]);p.append(m.text(cap['x'],cap['y']+21,'★'+c['capital'],10,fill='#792c26'))
    for isle in d['islands']:
        if isle['kind']!='主岛':continue
        unit=next(r for r in d['districts'] if r['code']==isle['district_code'])
        if (unit['x']-isle['x'])**2+(unit['y']-isle['y'])**2>55**2:
            p.append(m.text(isle['x'],isle['y'],unit['mark']+'属岛',10))
    p.append(m.text(PANEL+18,50,'二级行政区索引',18,anchor='start',bold=True,halo=False))
    half=math.ceil(len(d['countries'])/3); y=85
    for ci,c in enumerate(d['countries']):
        if ci%half==0:y=85
        x=PANEL+14+(ci//half)*160;p.append(m.text(x,y,c['code']+' '+c['name'],10.5,anchor='start',bold=True,halo=False));y+=24
        for r in c['districts']:p.append(m.text(x,y,r['mark']+' '+r['name'],9.8,anchor='start',halo=False));y+=18
        y+=12
    p+= [m.text(PANEL+18,1220,'红实线：国界　蓝虚线：二级区界',12,anchor='start',halo=False),m.text(PANEL+18,1245,'★ 国都　北 ↑　群岛合隶，大小示意',12,anchor='start',halo=False),m.text(PANEL+18,1270,'治所、人口、官员与派系见各国志',12,anchor='start',halo=False),m.text(PANEL+18,1295,'原五区系保留宪制推举关系',12,anchor='start',halo=False),'</svg>']
    prefix='02' if kind=='洄原' else '03';(ATLAS/(prefix+'·'+kind+'大陆·疆域地形图.svg')).write_text('\n'.join(p),encoding='utf-8')
    (SOURCE/(kind+'·图层数据.json')).write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8')
    import shutil
    shutil.copy2(OUT/(kind+'·新栅格.npz'),SOURCE/(kind+'·行政栅格.npz'))
    print(kind,'SVG8000',len(placed),'labels')

if __name__=='__main__':
    if sys.argv[1]=='prepare':
        for kind in ['洄原','燧岬']:prepare(kind)
    else:render(sys.argv[2],sys.argv[3])

