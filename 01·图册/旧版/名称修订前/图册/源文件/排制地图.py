"""Build original SVG cartographic layers over imagegen physical artwork.
Raster artwork is kept unchanged. Names and boundary geometry are separate.
"""
from pathlib import Path
from collections import defaultdict
import json, base64, math, re
import numpy as np
from PIL import Image, ImageDraw
from html import escape

ROOT=Path(__file__).resolve().parents[2]
ATLAS=Path(r'D:\dreaming\西湾盛洲志\01·图册')
SOURCE=ATLAS/'源文件'
SOURCE.mkdir(parents=True,exist_ok=True)
CFG=SOURCE/'地图背景.json'
COLORS=['#ac82b2','#d4a34f','#a7b363','#649f88','#d5b954','#72a86b','#d39a83','#9cb1cf','#c8a570','#b48093','#80bdb3','#cdbe76']

def text(x,y,s,size=13,fill='#302b23',anchor='middle',bold=False,halo=True):
    return f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" text-anchor="{anchor}" fill="{fill}" font-weight="{700 if bold else 400}"'+(' stroke="#fff4d9" stroke-width="3" paint-order="stroke" stroke-linejoin="round"' if halo else '')+'>'+escape(str(s))+'</text>'

def simplify(points,tol=1.7):
    if len(points)<3:return points
    a=np.array(points[0],float);b=np.array(points[-1],float)
    p=np.array(points,float);v=b-a;den=np.dot(v,v)
    ds=np.linalg.norm(p-(a+np.clip((p-a)@v/(den or 1),0,1)[:,None]*v),axis=1)
    k=int(np.argmax(ds))
    if ds[k]>tol:return simplify(points[:k+1],tol)[:-1]+simplify(points[k:],tol)
    return [points[0],points[-1]]

def trace_segments(segments):
    graph=defaultdict(list)
    for a,b in segments:graph[a].append(b);graph[b].append(a)
    remaining={tuple(sorted((a,b))) for a,b in segments};paths=[]
    while remaining:
        first=next(iter(remaining)); ends=[v for v in first if len(graph[v])!=2]
        cur=ends[0] if ends else first[0];pts=[cur]
        while True:
            candidates=[n for n in graph[cur] if tuple(sorted((cur,n))) in remaining]
            if not candidates:break
            nxt=candidates[0];remaining.remove(tuple(sorted((cur,nxt))));pts.append(nxt);cur=nxt
            if cur==pts[0]:break
        if len(pts)>2:paths.append(simplify(pts))
    return paths

def path_d(points,scale=1):
    return 'M '+' L '.join(f'{x*scale:.1f},{y*scale:.1f}' for x,y in points)

def boundaries(field,country,step=3,include_zero=False):
    groups=defaultdict(list);h,w=field.shape
    hv=(field[:,:-1]!=field[:,1:]);vv=(field[:-1,:]!=field[1:,:])
    if not include_zero:
        hv&=(field[:,:-1]>0)&(field[:,1:]>0);vv&=(field[:-1,:]>0)&(field[1:,:]>0)
    for yy,xx in zip(*np.where(hv)):
        a,b=int(field[yy,xx]),int(field[yy,xx+1]);groups[tuple(sorted((a,b)))].append(((xx+1,yy),(xx+1,yy+1)))
    for yy,xx in zip(*np.where(vv)):
        a,b=int(field[yy,xx]),int(field[yy+1,xx]);groups[tuple(sorted((a,b)))].append(((xx,yy+1),(xx+1,yy+1)))
    paths=[]
    for pair,segs in groups.items():
        for pts in trace_segments(segs):
            paths.append(dict(pair=pair,points=[(x*step,y*step) for x,y in pts],country=country))
    return paths

LANPOINTS=[(241,403),(234,259),(323,493),(400,356),(80,395),(432,719),(477,815),(235,724),(596,679),(555,777),(592,314),(538,205),(516,408),(712,353),(698,201),(742,556),(714,463),(682,539),(714,620),(542,570),(600,573),(576,527),(768,621),(693,703),(925,541),(806,430),(909,631),(832,507),(1037,362),(1008,447),(1011,535),(981,184),(869,292),(1124,478),(1108,672),(1176,392),(1249,586)]
HUAICENTERS=[(490,270),(650,410),(239,285),(331,550),(220,711),(400,800),(650,610),(650,800),(916,785),(950,445),(1079,670),(990,213)]

def tps(source,target):
    source=np.array(source,float);target=np.array(target,float)
    def radial(q):
        rr=((q[:,None,:]-source[None,:,:])**2).sum(2)
        return rr*np.log(rr+1e-12)
    n=len(source);P=np.c_[np.ones(n),source];K=radial(source)
    co=np.linalg.solve(np.block([[K+np.eye(n)*1e-7,P],[P.T,np.zeros((3,3))]]),np.r_[target,np.zeros((3,2))])
    def warp(q):
        q=np.array(q,float)
        return np.c_[radial(q),np.ones(len(q)),q]@co
    return warp

def map_data(kind):
    if kind=='岚衡':
        old=json.loads((ATLAS/'地图数据.json').read_text(encoding='utf-8-sig'))
        population_path=SOURCE/'岚衡·区人口核对.json'
        population_lookup={r['name']:r['pop万'] for r in json.loads(population_path.read_text(encoding='utf-8-sig'))} if population_path.exists() else {}
        rows=old['二级区索引'];warp=tps([[r[3],r[4]] for r in rows],LANPOINTS)
        cs=[];counter=0
        for i,c in enumerate(old['国家']):
            ds=[]
            for di,(name,x,y) in enumerate(c['units']):
                counter+=1;px,py=LANPOINTS[counter-1]
                ds.append(dict(code=f'L{i+1:02}-{di+1:02}',name=name,mark=f'{counter:02}',x=px,y=py))
                if name in population_lookup:ds[-1]['population_wan']=population_lookup[name]
            cap=warp([c['capital'][1:]])[0]
            poly=warp(old['曲线国家边界'][c['name']]).tolist()
            cs.append(dict(code=f'L{i+1:02}',name=c['name'],capital=c['capital'][0],x=float(cap[0]),y=float(cap[1]),districts=ds,poly=poly))
            if population_lookup:cs[-1]['population_wan']=sum(d['population_wan'] for d in ds)
        return cs,1470,1070,1290,warp
    data=json.loads((SOURCE/(kind+'·行政原始数据.json')).read_text(encoding='utf-8-sig'))
    cs=data['countries']
    if 'districts' in data:
        for c in cs:c['districts']=[dict(d,capital=d.get('seat')) for d in data['districts'] if d['country']==c['name']]
    for i,c in enumerate(cs):
        ox,oy=c['x'],c['y']
        px,py=(HUAICENTERS[i] if kind=='洄原' else (20+1.2*ox,6+1.16*oy))
        for d in c['districts']:
            d['x']=px+(d['x']-ox)*1.12;d['y']=py+(d['y']-oy)*1.12;d['mark']=d['code'].replace('-','·')
        c['x'],c['y']=px,py
    if kind=='洄原':
        islands=[(1080,145),(1230,125),(1100,375),(1220,325),(1235,530)]
        for d,p in zip(cs[-1]['districts'],islands):d['x'],d['y']=p
        cs[-1]['x'],cs[-1]['y']=1080,145
    else:
        points={'S09-05':(70,355),'S10-01':(210,755),'S10-02':(105,855),'S10-03':(175,705),'S10-04':(240,790),'S10-05':(55,590),'S07-04':(875,890),'S08-04':(575,810)}
        for c in cs:
            for d in c['districts']:
                if d['code'] in points:d['x'],d['y']=points[d['code']]
    return cs,1570,1002,(1300 if kind=='洄原' else 1200),None

def make(kind,background):
    cs,W,H,panel,warp=map_data(kind);step=3;gw=math.ceil(panel/step);gh=math.ceil(H/step)
    yy,xx=np.mgrid[:gh,:gw];X=xx*step;Y=yy*step
    field=np.zeros((gh,gw),np.int16)
    island_masks={}
    if kind=='岚衡':
        for i,c in enumerate(cs):
            mask=Image.new('L',(gw,gh));dr=ImageDraw.Draw(mask)
            dr.polygon([(x/step,y/step) for x,y in c['poly']],fill=255)
            if i in (0,6):
                for d in c['districts']:
                    if d['name'] in ('外海岛盟','舟列府'):
                        dr.ellipse(((d['x']-23)/step,(d['y']-42)/step,(d['x']+23)/step,(d['y']+42)/step),fill=255)
            field[np.asarray(mask)>0]=i+1
    else:
        coast=([(137,193),(238,140),(398,120),(583,115),(766,100),(961,67),(1100,99),(1120,219),(1127,345),(1170,433),(1135,545),(1150,662),(1120,800),(965,875),(813,902),(677,887),(532,894),(400,906),(263,856),(177,820),(110,725),(79,573),(102,490),(120,340)] if kind=='洄原' else [(121,187),(239,142),(398,158),(542,109),(697,54),(865,90),(1030,146),(1090,240),(1130,360),(1138,499),(1168,654),(1125,758),(1084,835),(967,952),(813,910),(691,895),(602,928),(449,885),(311,867),(233,824),(172,737),(143,642),(84,527),(70,374),(99,247)])
        coast=([(105,250),(150,190),(160,115),(240,65),(320,75),(360,165),(420,155),(450,70),(550,85),(610,130),(735,90),(800,60),(855,140),(915,180),(940,280),(880,325),(960,360),(1090,315),(1140,370),(1100,430),(1160,460),(1090,510),(1120,610),(1010,660),(1090,715),(1150,720),(1175,790),(1090,845),(970,825),(870,860),(825,795),(750,780),(725,900),(640,935),(610,850),(535,800),(480,845),(370,800),(280,860),(160,815),(160,755),(235,710),(275,615),(175,600),(80,645),(40,590),(75,520),(155,470),(195,425),(115,400),(65,360)] if kind=='洄原' else [(200,155),(300,100),(400,175),(495,160),(600,85),(660,35),(780,70),(805,155),(930,120),(985,185),(970,250),(1100,290),(1150,390),(1080,460),(1180,480),(1180,560),(1110,575),(1020,640),(1070,725),(1150,760),(1100,835),(970,850),(945,925),(860,915),(830,830),(760,800),(700,865),(715,945),(605,965),(565,870),(500,820),(470,900),(360,920),(310,850),(305,735),(250,700),(170,725),(90,765),(60,720),(140,640),(220,570),(205,500),(125,450),(85,385),(150,360),(155,280),(105,250),(145,200)])
        detailed=[]
        for j,a in enumerate(coast):
            b=coast[(j+1)%len(coast)];delta=np.array(b,float)-a;length=np.linalg.norm(delta);normal=np.array([-delta[1],delta[0]])/(length or 1)
            for t in np.linspace(0,1,max(2,int(length/11)),endpoint=False):
                ripple=math.sin(t*math.pi)*(4*math.sin(t*length/13+j)+2*math.sin(t*length/5.7+j*2))
                detailed.append((np.array(a)+t*delta+normal*ripple).tolist())
        coast=detailed
        mask=Image.new('L',(gw,gh));dr=ImageDraw.Draw(mask);dr.polygon([(x/step,y/step) for x,y in coast],fill=255)
        land=np.asarray(mask)>0
        # All sides share the same deformed distance field: no gaps or overlap.
        DX=X+34*np.sin(Y/61)+12*np.sin(X/42+Y/57)
        DY=Y+26*np.sin(X/79)+13*np.sin(Y/39+X/93)
        scores=np.array([(DX-c['x'])**2+(DY-c['y'])**2 for c in cs],dtype=np.float32)
        field[land]=(np.argmin(scores,axis=0)+1)[land]
        if kind=='洄原':
            # Longtidal mainland district is a coastal strip, not the northern plain.
            without_islands=np.argmin(scores[:11],axis=0)+1
            field[(field==12)&land]=without_islands[(field==12)&land]
            coast_strip=land&(((X-1100)/45)**2+((Y-375)/60)**2<1)
            field[coast_strip]=12
            north_plain=(field==2)&(X>600)&(Y<215+6*np.sin(X/45))
            field[north_plain]=1
            # Preserve the documented Yuanxi–West Chen valley corridor.
            corridor=((X-891)**2+(Y-623)**2<62**2)&np.isin(field,[9,10])
            field[corridor]=np.where((X+6*np.sin(Y/24))[corridor]<891,7,11)
        else:
            # Dachen and Mojieluo share the mountain pass; Kazilan does not border Tavina.
            saddle=((X-775)**2+(Y-429)**2<36**2)&np.isin(field,[1,6])
            field[saddle]=np.where((X+4*np.sin(Y/17))[saddle]<775,2,3)
        island_specs=({'H12-01':(75,105),'H12-02':(48,72),'H12-04':(55,95),'H12-05':(37,65)} if kind=='洄原' else {'S09-05':(37,70),'S10-02':(64,90),'S10-05':(30,90)})
        for ci,c in enumerate(cs):
            for di,d in enumerate(c['districts']):
                if d['code'] not in island_specs:continue
                rx,ry=island_specs[d['code']];angle=np.arctan2((Y-d['y'])/ry,(X-d['x'])/rx)
                radius=np.sqrt(((X-d['x'])/rx)**2+((Y-d['y'])/ry)**2)
                edge=1+.15*np.sin(3*angle+di)+.09*np.sin(7*angle+ci)+.045*np.sin(13*angle)
                island=(radius<edge)&~land
                field[island]=ci+1
                island_masks[d['code']]=island
    for ci,c in enumerate(cs,1):
        iy,ix=round(c['y']/step),round(c['x']/step)
        if not (0<=iy<gh and 0<=ix<gw and field[iy,ix]==ci):
            cells=np.argwhere(field==ci);center=cells.mean(axis=0);chosen=cells[np.argmin(((cells-center)**2).sum(axis=1))]
            c['x'],c['y']=int(chosen[1]*step),int(chosen[0]*step)
        ny=c['y']-68;iy,ix=round(ny/step),round(c['x']/step)
        c['name_y']=ny if 0<=iy<gh and 0<=ix<gw and field[iy,ix]==ci else c['y']
    districts=np.zeros_like(field);rows=[];idx=0
    for ci,c in enumerate(cs):
        DX=X+24*np.sin(Y/38)+8*np.sin(X/31+Y/49);DY=Y+20*np.sin(X/47)+9*np.sin(Y/26)
        dscores=np.array([(DX-d['x'])**2+(DY-d['y'])**2 for d in c['districts']],dtype=np.float32)
        nearest=np.argmin(dscores,axis=0)
        for di,d in enumerate(c['districts']):
            if d['code'] in island_masks:nearest[island_masks[d['code']]]=di
        for di,d in enumerate(c['districts']):
            idx+=1;districts[(field==ci+1)&(nearest==di)]=idx
            cells=np.argwhere(districts==idx)
            if not len(cells):raise ValueError('区划无图域 '+d['code'])
            dd=(cells[:,1]*step-d['x'])**2+(cells[:,0]*step-d['y'])**2
            iy,ix=cells[np.argmin(dd)];d['x'],d['y']=int(ix*step),int(iy*step)
            rows.append(dict(d,country=c['name'],country_code=c['code']))
    national=boundaries(field,True,step);local=boundaries(districts,False,step)
    np.savez_compressed(SOURCE/(kind+'·行政栅格.npz'),country=field,district=districts,step=step)
    # District paths coincident with national borders are omitted by pair lookup.
    country_for_index={i+1:r['country_code'] for i,r in enumerate(rows)}
    local=[p for p in local if country_for_index[p['pair'][0]]==country_for_index[p['pair'][1]]]
    placed=[]
    for ri,r in enumerate(rows,1):
        cells=np.argwhere(districts==ri);center=cells.mean(axis=0)*step
        score=((cells*step-center)**2).sum(axis=1)
        candidates=[(r['x'],r['y'])]+[(int(cells[j,1]*step),int(cells[j,0]*step)) for j in np.argsort(score)[::max(1,len(cells)//180)]]
        clear=lambda x,y:all(abs(x-a)>55 or abs(y-b)>23 for a,b in placed)
        chosen=next(((x,y) for x,y in candidates if clear(x,y)),None)
        if chosen is None:
            chosen=next(((r['x']+dx,r['y']+dy) for dy in [24,-24,48,-48,72,-72] for dx in [0,30,-30,60,-60] if clear(r['x']+dx,r['y']+dy)),(r['x'],r['y']))
        r['label_x'],r['label_y']=chosen;placed.append(chosen)
    b64=base64.b64encode(Path(background).read_bytes()).decode()
    parts=[f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="4000" height="{round(4000*H/W)}" viewBox="0 0 {W} {H}">', '<style>text{font-family:"Microsoft YaHei","Noto Sans CJK SC",sans-serif}</style>',f'<image width="{W}" height="{H}" href="data:image/png;base64,{b64}"/>']
    for p in local:parts.append(f'<path d="{path_d(p["points"])}" fill="none" stroke="#fff4d8" stroke-width="3.7" stroke-opacity=".88"/><path d="{path_d(p["points"])}" fill="none" stroke="#344d5a" stroke-width="1.65" stroke-dasharray="5 3"/>')
    for p in national:parts.append(f'<path d="{path_d(p["points"])}" fill="none" stroke="#f7e4bd" stroke-width="4"/><path d="{path_d(p["points"])}" fill="none" stroke="#a5352b" stroke-width="2.05"/>')
    counts={'岚衡':'七国三十七区','洄原':'十二国六十区','燧岬':'十国五十区'}
    parts.append(text(50 if kind!='岚衡' else 58,75,kind+'大陆·'+counts[kind],30 if kind!='岚衡' else 27,anchor='start',bold=True,halo=False))
    for ci,c in enumerate(cs):
        # Capital markers and labels deliberately remain separate from district ids.
        cap=next((d for d in c['districts'] if d.get('capital',d.get('seat'))==c['capital']),c['districts'][0])
        cx,cy=cap['x'],cap['y']
        parts.append(text(c['x'],c.get('name_y',c['y']-68),c['code']+' '+c['name'],15 if kind!='岚衡' else 14,bold=True))
        parts.append(text(cx,cy+24,'★'+c['capital'],10,fill='#752d29'))
    for d in rows:
        wide=14 if kind=='岚衡' else 26
        lx,ly=d.get('label_x',d['x']),d.get('label_y',d['y'])
        if (lx,ly)!=(d['x'],d['y']):parts.append(f'<path d="M {d["x"]},{d["y"]} L {lx},{ly}" stroke="#493e31" stroke-width=".7"/><circle cx="{d["x"]}" cy="{d["y"]}" r="2" fill="#493e31"/>')
        parts.append(f'<rect x="{lx-wide}" y="{ly-9}" width="{wide*2}" height="18" rx="4" fill="#fff4d9" stroke="#73604b" stroke-width=".6" opacity=".96"/>')
        parts.append(text(lx,ly+3,d['mark'],10 if kind=='岚衡' else 8.6,halo=False))
    parts.append(text(panel+14,58,'二级行政区索引',13 if kind=='岚衡' else 17,anchor='start',bold=True,halo=False))
    split=len(cs) if kind=='岚衡' else math.ceil(len(cs)/2);colwidth=(W-panel-22)/(1 if kind=='岚衡' else 2)
    line=90
    for ci,c in enumerate(cs):
        if ci==split:line=90
        lx=panel+14+(ci//split)*colwidth
        parts.append(text(lx,line,c['code']+' '+c['name'],10.5 if kind=='岚衡' else 10.3,anchor='start',bold=True,halo=False));line+=22
        for d in c['districts']:
            parts.append(text(lx+3,line,d['mark']+' '+d['name'],10.1 if kind=='岚衡' else 9.4,anchor='start',halo=False));line+=18
        line+=10
    note_y=H-77
    parts.append(text(panel+14,note_y,'共历742年秋',11,anchor='start',halo=False))
    parts.append(text(panel+14,note_y+22,'北向上 · 方位与辖境示意',9.5,anchor='start',halo=False))
    parts.append(text(panel+14,note_y+42,'岛区含群岛；不据图测面积',9.2,anchor='start',halo=False))
    ly=H-151
    if kind=='燧岬':parts.append('<g transform="translate(1170,-40)">')
    parts += [text(53,ly,'图例',12,anchor='start',bold=True,halo=False),f'<path d="M 52,{ly+19} h 45" stroke="#a5352b" stroke-width="2"/>',text(104,ly+23,'国界',10,anchor='start',halo=False),f'<path d="M 52,{ly+40} h 45" stroke="#344d5a" stroke-width="1.65" stroke-dasharray="4 2"/>',text(104,ly+44,'二级区界',10,anchor='start',halo=False),text(52,ly+65,'★ 国都  蓝线 河流',10,anchor='start',halo=False)]
    if kind=='燧岬':parts.append('</g>')
    seas=({'岚衡':[(60,600,'落照海'),(1200,300,'沧溟海'),(1000,880,'珊瑚海')],'洄原':[(58,495,'回澜海'),(1230,462,'镜门海'),(826,940,'青汐海')],'燧岬':[(66,483,'镜门海'),(1150,856,'曜东洋'),(830,965,'南绒海')]}[kind])
    for x,y,s in seas:parts.append(text(x,y,s,20,fill='#133f4c',bold=True))
    parts.append(text(panel-45,86,'北 ↑',17,fill='#264248',bold=True))
    parts.append('</svg>')
    prefix={'岚衡':'01','洄原':'02','燧岬':'03'}[kind];stem=prefix+'·'+kind+'大陆·疆域地形图'
    (ATLAS/(stem+'.svg')).write_text('\n'.join(parts),encoding='utf-8')
    landpaths=boundaries((field>0).astype(np.int16),False,step,include_zero=True)
    record=dict(continent=kind,width=W,height=H,country_count=len(cs),district_count=idx,countries=cs,districts=rows,national_boundaries=national,district_boundaries=local,land_paths=landpaths,background=str(background),note='艺术地形由imagegen绘制；SVG区号文字和国界区界为独立核对图层；北向上，非测绘投影')
    (SOURCE/(kind+'·图层数据.json')).write_text(json.dumps(record,ensure_ascii=False,indent=2,default=lambda v:int(v) if isinstance(v,np.integer) else float(v)),encoding='utf-8')
    print(kind,len(cs),idx,'国家界段',len(national),'区界段',len(local))

if __name__=='__main__':
    config=json.loads(CFG.read_text(encoding='utf-8-sig'))
    for kind,bg in config.items():
        if kind in ('岚衡','洄原','燧岬'):make(kind,bg)
