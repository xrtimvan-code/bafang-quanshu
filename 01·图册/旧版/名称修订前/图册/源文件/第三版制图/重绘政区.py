from pathlib import Path
from collections import deque
import json, math, heapq, base64, re, importlib.util
import numpy as np
from PIL import Image, ImageDraw
from html import escape

ROOT=Path(__file__).resolve().parents[2]
BOOK=Path(__file__).resolve().parents[3]; A=BOOK/'01·图册'; S=A/'源文件'
OUT=Path(__file__).parent; STAGE=OUT/'待核图册'; STAGE.mkdir(exist_ok=True)
BASE=OUT/'第二版基线';BASE.mkdir(exist_ok=True)
spec=importlib.util.spec_from_file_location('geo',S/'第二版制图'/'绘图函数.py');geo=importlib.util.module_from_spec(spec);spec.loader.exec_module(geo)
W,H,P,step=2100,1350,1600,1.5
COLORS=['#ddcda7','#d6bed8','#b8ced5','#d8c697','#b8c9ac','#dbc0b4','#cec8a9','#c2bfd5','#d3c898','#b6c9c5','#cdb7c5','#c2ccd8']

def txt(x,y,s,size=12,fill='#343a38',anchor='middle',family='SimSun',spacing=0,rotate=0,halo=1.2):
    tr=f' transform="rotate({rotate:.1f} {x:.1f} {y:.1f})"' if rotate else ''
    return f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" font-family="{family}, Noto Serif CJK SC, serif" font-size="{size}" letter-spacing="{spacing}" fill="{fill}" stroke="#fbf5e5" stroke-width="{halo}" paint-order="stroke" stroke-linejoin="round"{tr}>{escape(s)}</text>'

def smoothpath(points,closed=False):
    if len(points)<3:return geo.path_d(points)+(' Z' if closed else '')
    q=points[:-1] if closed and points[-1]==points[0] else points
    mid=lambda a,b:((a[0]+b[0])/2,(a[1]+b[1])/2)
    if closed:
        a=mid(q[-1],q[0]);out=f'M {a[0]:.2f},{a[1]:.2f}'
        for i,p in enumerate(q):
            b=mid(p,q[(i+1)%len(q)]);out+=f' Q {p[0]:.2f},{p[1]:.2f} {b[0]:.2f},{b[1]:.2f}'
        return out+' Z'
    out=f'M {q[0][0]:.2f},{q[0][1]:.2f}'
    for i in range(1,len(q)-1):
        b=mid(q[i],q[i+1]);out+=f' Q {q[i][0]:.2f},{q[i][1]:.2f} {b[0]:.2f},{b[1]:.2f}'
    return out+f' L {q[-1][0]:.2f},{q[-1][1]:.2f}'

def distance(mask):
    active=mask.copy();dist=np.zeros(mask.shape,np.int16)
    while active.any():
        dist[active]+=1
        er=active.copy();er[1:]&=active[:-1];er[:-1]&=active[1:];er[:,1:]&=active[:,:-1];er[:,:-1]&=active[:,1:];er[[0,-1]]=False;er[:,[0,-1]]=False;active=er
    return dist

def pairs(f):
    a=f[:,:-1];b=f[:,1:];x=f[:-1,:];y=f[1:,:]
    ps=np.r_[np.stack([a[a!=b],b[a!=b]],1),np.stack([x[x!=y],y[x!=y]],1)]
    return set(tuple(sorted((int(a),int(b)))) for a,b in ps if a and b)

def load(kind):
    import shutil
    jf=BASE/(kind+'·图层数据.json')
    if not jf.exists():shutil.copy2(S/(kind+'·图层数据.json'),jf)
    d=json.loads(jf.read_text(encoding='utf-8'));d['background']=str(S/Path(d['background'].replace('\\','/')).name)
    for c in d['countries']:
        if kind!='岚衡':
            cap=next(r for r in c['districts'] if r.get('seat')==c['capital']);c['capital_x'],c['capital_y']=cap['x'],cap['y']
        else:
            text=(A/'01·岚衡大陆·疆域地形图.svg').read_text(encoding='utf-8')
            found=next((s for s in re.findall(r'<text[^>]*>★[^<]+</text>',text) if '★'+c['capital']+'<' in s),None)
            if found:c['capital_x']=float(re.search(r'x="([\d.]+)"',found)[1]);c['capital_y']=float(re.search(r'y="([\d.]+)"',found)[1])-24
            else:c['capital_x'],c['capital_y']=c['x'],c['y']
    grid=BASE/(kind+'·行政栅格.npz')
    if kind!='岚衡':
        if not grid.exists():shutil.copy2(S/(kind+'·行政栅格.npz'),grid)
        return d,np.repeat(np.repeat(np.load(grid)['country'],2,axis=0),2,axis=1)
    h,w=int(H/step),math.ceil(P/step); im=Image.new('L',(w,h));dr=ImageDraw.Draw(im)
    for c in d['countries']:dr.polygon([(x/step,y/step) for x,y in c['poly']],fill=int(c['code'][1:]))
    f=np.array(im);land=Image.new('L',(w,h));dr=ImageDraw.Draw(land)
    for p in d['land_paths']:
        if len(p['points'])>3:dr.polygon([(x/step,y/step) for x,y in p['points']],fill=255)
    missing=(f==0)&(np.array(land)>0);yy,xx=np.mgrid[:h,:w]
    score=np.array([(xx*step-c['x'])**2+(yy*step-c['y'])**2 for c in d['countries']]);f[missing]=(np.argmin(score,axis=0)+1)[missing]
    for r in d.get('islands',[]):
        cx,cy,rx,ry=r['x'],r['y'],r['rx'],r['ry'];mask=(((xx*step-cx)/rx)**2+((yy*step-cy)/ry)**2<2.8)&(np.array(land)>0)
        f[mask]=int(r['country_code'][1:])
    for c in d['countries']:
        for r in c['districts']:
            if r['name'] in ['外海岛盟','舟列府']:
                mask=(((xx*step-r['x'])/28)**2+((yy*step-r['y'])/48)**2<2)&(np.array(land)>0);f[mask]=int(c['code'][1:])
    f[np.array(land)==0]=0
    # Align the older Lan geometry with the actual coast in its accepted artwork.
    # Pixels are read for analysis only; the raster artwork itself is never edited.
    pixels=np.array(Image.open(d['background']).convert('RGB').resize((round(W/step),h)))[:,:w].astype(float)
    physical=(pixels[:,:,0]>.92*pixels[:,:,2])&(pixels[:,:,1]>.85*pixels[:,:,2])
    def dilate(a):
        b=a.copy();b[1:]|=a[:-1];b[:-1]|=a[1:];b[:,1:]|=a[:,:-1];b[:,:-1]|=a[:,1:];return b
    def erode(a):
        b=a.copy();b[1:]&=a[:-1];b[:-1]&=a[1:];b[:,1:]&=a[:,:-1];b[:,:-1]&=a[:,1:];return b
    for _ in range(2):physical=dilate(physical)
    for _ in range(2):physical=erode(physical)
    # Fill inland water gaps without filling bays connected to the sea.
    ocean=~physical;seen=np.zeros_like(ocean);q=deque()
    for x in range(w):
        for y in [0,h-1]:
            if ocean[y,x] and not seen[y,x]:seen[y,x]=True;q.append((y,x))
    for y in range(h):
        for x in [0,w-1]:
            if ocean[y,x] and not seen[y,x]:seen[y,x]=True;q.append((y,x))
    while q:
        y,x=q.popleft()
        for dy,dx in [(-1,0),(1,0),(0,-1),(0,1)]:
            ny,nx=y+dy,x+dx
            if 0<=ny<h and 0<=nx<w and ocean[ny,nx] and not seen[ny,nx]:seen[ny,nx]=True;q.append((ny,nx))
    physical=~seen;f[~physical]=0
    # Propagate coastal authority from existing inland jurisdiction, keeping shared interiors.
    unknown=physical&(f==0)
    while unknown.any():
        proposals=np.zeros_like(f)
        for dy,dx in [(-1,0),(1,0),(0,-1),(0,1)]:
            shifted=np.roll(np.roll(f,dy,axis=0),dx,axis=1);proposals[(proposals==0)&unknown&(shifted>0)]=shifted[(proposals==0)&unknown&(shifted>0)]
        progress=unknown&(proposals>0)
        if not progress.any():break
        f[progress]=proposals[progress];unknown[progress]=False
    # Separate offshore components receive the nearest established island authority.
    if unknown.any():
        known=np.argwhere(f>0)
        while unknown.any():
            sy,sx=np.argwhere(unknown)[0];cells=[];q=deque([(int(sy),int(sx))]);unknown[sy,sx]=False
            while q:
                y,x=q.popleft();cells.append((y,x))
                for dy,dx in [(-1,0),(1,0),(0,-1),(0,1)]:
                    ny,nx=y+dy,x+dx
                    if 0<=ny<h and 0<=nx<w and unknown[ny,nx]:unknown[ny,nx]=False;q.append((ny,nx))
            cells=np.array(cells)
            if len(cells)<9:continue
            cy,cx=cells.mean(axis=0);near=known[np.argmin((known[:,0]-cy)**2+(known[:,1]-cx)**2)];f[cells[:,0],cells[:,1]]=f[near[0],near[1]]
    d['land_paths']=geo.boundaries((f>0).astype(np.int16),False,step,include_zero=True)
    return d,f

def terrain(X,Y,seed):
    out=np.zeros_like(X,dtype=float);rng=np.random.default_rng(seed)
    for wavelength,amp in [(250,.5),(115,.32),(47,.21),(19,.13),(8,.055)]:
        for j in range(3):
            a=rng.uniform(0,math.pi);phase=rng.uniform(0,6.28)
            out+=amp*np.sin((X*np.cos(a)+Y*np.sin(a))*2*math.pi/wavelength+phase)
    return out

def noise(X,Y,scale,seed):
    rng=np.random.default_rng(seed);hh=int(Y.max()/scale)+3;ww=int(X.max()/scale)+3
    nodes=rng.normal(0,1,(hh,ww));gx=X/scale;gy=Y/scale;ix=gx.astype(int);iy=gy.astype(int);tx=gx-ix;ty=gy-iy
    tx=tx*tx*(3-2*tx);ty=ty*ty*(3-2*ty)
    return (1-ty)*((1-tx)*nodes[iy,ix]+tx*nodes[iy,ix+1])+ty*((1-tx)*nodes[iy+1,ix]+tx*nodes[iy+1,ix+1])

def national_shape(f,d,seed):
    yy,xx=np.mgrid[:f.shape[0],:f.shape[1]];X=xx*step;Y=yy*step;coast=distance(f>0)
    keep=np.clip(coast*step/36,0,1);rng=np.random.default_rng(seed)
    # Compose smooth geographic displacements; a shared field preserves shared borders.
    anchors=[(c['capital_x'],c['capital_y']) for c in d['countries']]
    for ax,ay in anchors:keep*=1-.85*np.exp(-((X-ax)**2+(Y-ay)**2)/28**2)
    expected=pairs(f)
    for factor in [1,.8,.6,.4]:
        q=f.copy();rng=np.random.default_rng(seed)
        for k in range(5):
            theta=rng.uniform(0,math.pi);wl=100+35*k;phase=rng.uniform(0,6.28)
            amp=(9+2*k)*factor
            wave=np.sin((X*np.cos(theta)+Y*np.sin(theta))*2*np.pi/wl+phase)
            sx=np.rint(xx+keep*amp*wave*np.sin(theta)/step).astype(int);sy=np.rint(yy-keep*amp*wave*np.cos(theta)/step).astype(int)
            sx=np.clip(sx,0,f.shape[1]-1);sy=np.clip(sy,0,f.shape[0]-1);sample=q[sy,sx];sample[(f==0)|(sample==0)]=f[(f==0)|(sample==0)];q=sample
        vx=sum(a*noise(X,Y,s,seed+97+i) for i,(s,a) in enumerate([(80,11),(34,5),(13,2),(5,.55)]))
        vy=sum(a*noise(X,Y,s,seed+191+i) for i,(s,a) in enumerate([(80,11),(34,5),(13,2),(5,.55)]))
        sx=np.clip(np.rint(xx+keep*factor*vx/step).astype(int),0,f.shape[1]-1);sy=np.clip(np.rint(yy+keep*factor*vy/step).astype(int),0,f.shape[0]-1)
        sample=q[sy,sx];sample[(f==0)|(sample==0)]=f[(f==0)|(sample==0)];q=sample
        if pairs(q)==expected:return q
    raise ValueError('国界拓扑变化，需调整形势 '+d['continent'])

def provinces(f,d,seed):
    yy,xx=np.mgrid[:f.shape[0],:f.shape[1]];X=xx*step;Y=yy*step
    relief=terrain(X,Y,seed);cost=np.exp(1.7*relief)+.45
    h,w=f.shape;dist=np.full(f.shape,np.inf);labels=np.zeros_like(f);heap=[];rows=sorted(d['districts'],key=lambda r:r['code']);owner={i+1:int(r['country_code'][1:]) for i,r in enumerate(rows)}
    # Place each provincial seat in the same country, retaining its geographic neighbourhood.
    taken=set()
    for i,r in enumerate(rows,1):
        cells=np.argwhere(f==owner[i]);score=(cells[:,0]*step-r['y'])**2+(cells[:,1]*step-r['x'])**2
        chosen=next((tuple(cells[j]) for j in np.argsort(score) if tuple(cells[j]) not in taken));taken.add(chosen);y,x=chosen
        r['seat_x'],r['seat_y']=int(x*step),int(y*step);dist[y,x]=0;labels[y,x]=i;heapq.heappush(heap,(0,int(y),int(x),i))
    weights=np.array([1]+[float(r.get('area_weight',1))**.16 for r in rows])
    dirs=[(-1,0,1),(1,0,1),(0,-1,1),(0,1,1),(-1,-1,1.4142),(-1,1,1.4142),(1,-1,1.4142),(1,1,1.4142)]
    while heap:
        value,y,x,i=heapq.heappop(heap)
        if labels[y,x]!=i or value>dist[y,x]+1e-7:continue
        ci=owner[i];weight=weights[i]
        for dy,dx,len_ in dirs:
            ny,nx=y+dy,x+dx
            if not (0<=ny<h and 0<=nx<w) or f[ny,nx]!=ci:continue
            v=value+len_*(cost[y,x]+cost[ny,nx])/(2*weight)
            if v<dist[ny,nx]:dist[ny,nx]=v;labels[ny,nx]=i;heapq.heappush(heap,(v,ny,nx,i))
    # Offshore components belong to named island districts, not the nearest mainland nation.
    island_specs=d.get('islands',[])
    unseen=(f>0)&(labels==0)
    while unseen.any():
        sy,sx=np.argwhere(unseen)[0];ci=int(f[sy,sx]);component=[];q=deque([(int(sy),int(sx))]);unseen[sy,sx]=False
        while q:
            y,x=q.popleft();component.append((y,x))
            for dy,dx,_ in dirs[:4]:
                ny,nx=y+dy,x+dx
                if 0<=ny<h and 0<=nx<w and unseen[ny,nx] and f[ny,nx]==ci:unseen[ny,nx]=False;q.append((ny,nx))
        cells=np.array(component);cy,cx=cells.mean(axis=0)*step;rules=[r for r in island_specs if r['country_code']==f"{d['countries'][ci-1]['code']}"]
        if rules:
            match=min(rules,key=lambda r:(cx-r['x'])**2+(cy-r['y'])**2)
            candidates=[(i,r) for i,r in enumerate(rows,1) if r['country_code']==d['countries'][ci-1]['code'] and (r['code']==match.get('district_code') or r['name']==match.get('district_name'))]
        else:candidates=[]
        if not candidates:candidates=[(i,r) for i,r in enumerate(rows,1) if owner[i]==ci]
        i,_=min(candidates,key=lambda v:(v[1]['seat_x']-cx)**2+(v[1]['seat_y']-cy)**2);labels[cells[:,0],cells[:,1]]=i
    assert set(np.unique(labels))==set(range(len(rows)+1))
    for i,r in enumerate(rows,1):
        cells=np.argwhere(labels==i);assert np.all(f[labels==i]==owner[i]);r['x'],r['y']=r['seat_x'],r['seat_y']
    return labels,rows

def interior(mask):
    dd=distance(mask); y,x=np.unravel_index(np.argmax(dd),dd.shape);return x*step,y*step,int(dd[y,x])*step,dd

def render(kind):
    d,f0=load(kind);seed={'岚衡':137,'洄原':293,'燧岬':431}[kind];f=national_shape(f0,d,seed);districts,rows=provinces(f,d,seed+83)
    national=geo.boundaries(f,True,step);local=geo.boundaries(districts,False,step);owner={i+1:r['country_code'] for i,r in enumerate(rows)};local=[p for p in local if owner[p['pair'][0]]==owner[p['pair'][1]]]
    country_paths=[]
    for ci,c in enumerate(d['countries'],1):country_paths.append(geo.boundaries((f==ci).astype(np.int16),False,step,include_zero=True))
    bg=base64.b64encode(Path(d['background']).read_bytes()).decode()
    out=[f'<svg xmlns="http://www.w3.org/2000/svg" width="8000" height="5143" viewBox="0 0 {W} {H}">','<rect width="2100" height="1350" fill="#f4eee0"/>',f'<image width="2100" height="1350" preserveAspectRatio="none" href="data:image/png;base64,{bg}"/>','<rect width="1600" height="1350" fill="#f8f3e7" opacity=".32"/>','<rect x="1600" width="500" height="1350" fill="#f6f0e2"/>']
    for ci,ps in enumerate(country_paths):
        path=' '.join(smoothpath(p['points'],True) for p in ps if len(p['points'])>3)
        out.append(f'<path d="{path}" fill="#fffbf0" fill-rule="evenodd" opacity=".62"/>');out.append(f'<path d="{path}" fill="{COLORS[ci]}" fill-rule="evenodd" opacity=".43"/>')
    for p in local:out.append(f'<path d="{smoothpath(p["points"])}" fill="none" stroke="#665e60" stroke-width=".80" stroke-dasharray="2.3 .8" stroke-linejoin="round" opacity=".90"/>')
    for p in national:out.append(f'<path d="{smoothpath(p["points"])}" fill="none" stroke="#fff5dc" stroke-width="2.7"/><path d="{smoothpath(p["points"])}" fill="none" stroke="#6e3f52" stroke-width="1.20" stroke-linejoin="round"/>')
    # Country lettering occupies its own territory, centred on interior space rather than city seats.
    reserved=[]
    for ci,c in enumerate(d['countries'],1):
        x,y,radius,dd=interior(f==ci)
        short=c['name'];suffix=''
        for ending in ['自由旗盟','公社联邦','合渠国','法统国','三席国','共和国','汗国','公国','王国','帝国','王朝','盟国','侯领','联省','海盟','诸社','国']:
            if short.endswith(ending):short=short[:-len(ending)];suffix=ending;break
        if c['name']=='百契公社联邦':short,suffix='百契','公社联邦'
        chars=len(short);size=min(27,max(17,radius*.7));spacing=4 if chars<=3 else 2
        width=chars*size+(chars-1)*spacing
        for shrink in [1,.9,.8,.7]:
            sz=size*shrink;ww=chars*sz+(chars-1)*spacing;hh=sz+16
            best=None;bestscore=-1
            available=np.argwhere(dd>=max(3,int(hh/(2*step))))
            for cy,cx in available[::max(1,len(available)//1500)]:
                px,py=cx*step,cy*step;tests=[(int((px+dx)/step),int((py+dy)/step)) for dx in np.linspace(-ww/2,ww/2,7) for dy in [-hh/2,0,hh/2]]
                if not all(0<=ty<f.shape[0] and 0<=tx<f.shape[1] and f[ty,tx]==ci for tx,ty in tests):continue
                score=dd[cy,cx]-.014*((px-x)**2+(py-y)**2)**.5
                if score>bestscore:bestscore=score;best=(px,py)
            if best: x,y=best;size=sz;width=ww;break
        out.append(txt(x,y,short,size,'#34302f',spacing=spacing,halo=1.8));out.append(txt(x,y+17,suffix,10.5,'#55504c',spacing=1.8,halo=1.3))
        reserved.append((x,y,width/2+5,size+18));c['label_x'],c['label_y']=x,y;c['label']=short;c['label_suffix']=suffix;c['label_size']=size
        c['capital_x'],c['capital_y']=nearest(f==ci,c['capital_x'],c['capital_y'])
    placed=[]
    for i,r in enumerate(rows,1):
        x,y,radius,dd=interior(districts==i);name=r['name'];size=8.7 if kind!='岚衡' else 10
        width=len(name)*size; small=radius<11 or width>radius*4.8
        if small:name=r['mark'];size=7.5;width=len(name)*size
        clear=lambda px,py:all(abs(px-a)>(width/2+b+3) or abs(py-c)>15 for a,c,b in placed) and all(abs(px-a)>width/2+b or abs(py-c)>h/2+9 for a,c,b,h in reserved)
        candidates=[(x,y)]+[(int(cx*step),int(cy*step)) for cy,cx in np.argwhere(dd>1)[::max(1,int(np.count_nonzero(dd>1)/100))]]
        choice=next(((px,py) for px,py in candidates if clear(px,py)),None)
        if choice is None:
            name=r['mark'];size=7.3;width=len(name)*size
            choice=next(((px,py) for px,py in candidates if clear(px,py)),None)
        if choice is None:
            choice=next(((x+dx,y+dy) for dy in [18,-18,36,-36,54,-54] for dx in [0,35,-35,70,-70] if clear(x+dx,y+dy)),(x,y))
        px,py=choice;placed.append((px,py,width/2));r['label_x'],r['label_y']=px,py;r['label_text']=name
        if choice!=(x,y):out.append(f'<path d="M {x},{y} L {px},{py}" fill="none" stroke="#79736b" stroke-width=".4"/>')
        out.append(txt(px,py,name,size,'#3b443c',family='SimSun',halo=.60))
    for c in d['countries']:
        x,y=c['capital_x'],c['capital_y'];out.append(f'<circle cx="{x}" cy="{y}" r="3.4" fill="#fff9e8" stroke="#665058" stroke-width=".65"/><circle cx="{x}" cy="{y}" r="1.25" fill="#51464c"/>');out.append(txt(x+6,y+4,c['capital'],9.5,'#69444d',anchor='start',halo=1.5))
    for isle in d.get('islands',[]):
        if isle.get('kind')=='附岛' or isle['rx']<25:continue
        cx,cy=nearest(f==int(isle['country_code'][1:]),isle['x'],isle['y'])
        owner_name=next(c['label'] for c in d['countries'] if c['code']==isle['country_code'])
        if not any(abs(cx-c['label_x'])<90 and abs(cy-c['label_y'])<90 for c in d['countries']):out.append(txt(cx,cy+10,owner_name+'属',9,'#575351',halo=1.3))
    out += [txt(40,48,kind+'政区图',29,'#3b3932',anchor='start',spacing=3),txt(40,74,f'共历742年秋　{len(d["countries"])}国 · {len(rows)}二级行政区',11,anchor='start'),txt(1550,52,'北',15),'<path d="M 1550,70 V 113 M 1543,80 L 1550,64 L 1557,80" fill="none" stroke="#585b50" stroke-width="1"/>']
    out.append(txt(1620,50,'国家及二级行政区',17,anchor='start',spacing=1));columns=3 if kind!='岚衡' else 2;split=math.ceil(len(d['countries'])/columns);y=91
    for ci,c in enumerate(d['countries']):
        if ci%split==0:y=91
        x=1620+(ci//split)*(460/columns);out.append(txt(x,y,c['code']+' '+c['name'],10.2,anchor='start',halo=0));y+=24
        for r in rows:
            if r['country_code']==c['code']:out.append(txt(x,y,r['mark']+' '+r['name'],9.4,anchor='start',halo=0));y+=18
        y+=14
    for n,s in enumerate(['国界：深紫实线　二级界：细点划线','双圆点：国都　国名按辖境居中','宽字距国名与常规地区名分层排印','小辖区仅标区号，名称见本栏索引','岛屿合隶其区；图上面积与海距为示意']):out.append(txt(1620,1198+n*24,s,11,anchor='start',halo=0))
    out.append('</svg>');prefix={'岚衡':'01','洄原':'02','燧岬':'03'}[kind];stem=prefix+'·'+kind+'大陆·疆域地形图'
    (STAGE/(stem+'.svg')).write_text('\n'.join(out),encoding='utf-8')
    for c in d['countries']:c['districts']=[r for r in rows if r['country_code']==c['code']]
    d.update(countries=d['countries'],districts=rows,national_boundaries=national,district_boundaries=local,edition='第三版政区修订',country_paths=country_paths,note='领土色带与细分界表达辖境；字位依据实际图域；保持人口、区数和既定陆地接壤。')
    (STAGE/(kind+'·图层数据.json')).write_text(json.dumps(d,ensure_ascii=False,indent=2,default=lambda v:v.item()),encoding='utf-8')
    np.savez_compressed(STAGE/(kind+'·行政栅格.npz'),country=f,district=districts,step=step)
    print(kind,len(rows),'邻接',len(pairs(f)),'国名字位全部置于本国',flush=True)

def nearest(mask,x,y):
    cells=np.argwhere(mask);i=np.argmin((cells[:,1]*step-x)**2+(cells[:,0]*step-y)**2);cy,cx=cells[i];return int(cx*step),int(cy*step)

if __name__=='__main__':
    import sys
    for k in (sys.argv[1:] or ['岚衡','洄原','燧岬']):render(k)
