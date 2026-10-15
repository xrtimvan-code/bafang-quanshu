from pathlib import Path
from collections import deque
from html import escape
import json,math,importlib.util,base64
import numpy as np
from PIL import Image,ImageDraw,ImageFilter

import sys
O=Path(__file__).resolve().parent;sys.path.insert(0,str(O))
BOOK=O.parents[2];S=O/'基础数据';STAGE=BOOK;A=BOOK/'01·图册';DEST=A/'源文件'
import 绘图函数 as geo
import 标注函数 as m
G=json.loads((O/'地形绘制设计.json').read_text(encoding='utf-8'))
OLD={'衡岑':'岚衡','乌弥尔':'洄原','萨阑':'燧岬'};PREFIX={'衡岑':'01','乌弥尔':'02','萨阑':'03'}
W,H=2100,1350;STEP=1.5
PALETTE={1:'#c3dbaa',2:'#e5dda6',3:'#d4bd89',4:'#bd986f',5:'#e2d9ca'}

def txt(x,y,text,size=12,color='#303c39',anchor='middle',spacing=0,halo=1.5):
    return m.txt(x,y,text,size,color,anchor=anchor,spacing=spacing,halo=halo)

def path(points,closed=False):return m.smoothpath(points,closed)

def components(mask):
    labels=np.zeros(mask.shape,np.int32);regions=[];h,w=mask.shape
    for yy,xx in zip(*np.where(mask)):
        if labels[yy,xx]:continue
        n=len(regions)+1;todo=deque([(int(yy),int(xx))]);labels[yy,xx]=n;ys=[];xs=[]
        while todo:
            y,x=todo.popleft();ys.append(y);xs.append(x)
            for ny,nx in [(y-1,x),(y+1,x),(y,x-1),(y,x+1)]:
                if 0<=ny<h and 0<=nx<w and mask[ny,nx] and not labels[ny,nx]:labels[ny,nx]=n;todo.append((ny,nx))
        regions.append((np.array(ys),np.array(xs)))
    return labels,regions

def allpaths(mask):
    return geo.boundaries(mask.astype(np.int16),False,STEP,include_zero=True)

def joined(ps):return ' '.join(path(p['points'],True) for p in ps if len(p['points'])>3)

def relative_relief(k,f,body,labs,parts):
    # Original cartographic relief built from the agreed geographic regions, not from edited imagery.
    # Values are relative illustration levels, never measured elevations in metres.
    Y,X=np.mgrid[:f.shape[0],:f.shape[1]];X=X*STEP;Y=Y*STEP;seed={'衡岑':17,'乌弥尔':41,'萨阑':73}[k]
    noise=m.noise(X,Y,105,seed)*.32+m.noise(X,Y,38,seed+1)*.16+m.noise(X,Y,13,seed+2)*.055
    z=np.maximum(.18,.4+noise)
    def polyweight(points):
        mask=Image.new('L',(f.shape[1],f.shape[0]));ImageDraw.Draw(mask).polygon([(x/STEP,y/STEP) for x,y in points],fill=255)
        return np.array(mask.filter(ImageFilter.GaussianBlur(9)),dtype=float)/255
    def lineweight(points):
        dist=np.full(f.shape,np.inf);progress=np.zeros(f.shape);lengths=[math.dist(a,b) for a,b in zip(points,points[1:])];total=sum(lengths) or 1;previous=0
        for (ax,ay),(bx,by),length in zip(points,points[1:],lengths):
            dx,dy=bx-ax,by-ay;t=np.clip(((X-ax)*dx+(Y-ay)*dy)/(dx*dx+dy*dy or 1),0,1)
            distance=(X-ax-t*dx)**2+(Y-ay-t*dy)**2;near=distance<dist
            progress[near]=(previous+t[near]*length)/total;dist[near]=distance[near];previous+=length
        return dist,np.clip(progress,0,1)
    for p in G[k]['plateaus']:
        weight=polyweight(p['points'])*body;target={1:.3,2:.93,3:1.62,4:2.15,5:3.6}[p['level']]+noise*.85
        z=z*(1-weight)+target*weight
    for r in G[k]['ridges']:
        dist,t=lineweight(r['points']);w=r['width']*.49
        strength=np.exp(-dist/(w*w))*(.82+.18*np.sin(t*np.pi))
        amplitude=3.5 if r['level']>=5 else 2.15 if r['level']==4 else 1.45
        candidate=.42+amplitude*strength+(noise*.68+np.sin(t*8+seed)*.13)*strength
        z=np.maximum(z,candidate*body)
    for p in G[k]['plains']:
        weight=polyweight(p['points'])*body;z=z*(1-weight)+(.31+noise*.35)*weight
    for r in G[k]['rivers']:
        dist,t=lineweight(r['points']);width=5 if r.get('tributary_of') else 9
        weight=np.exp(-dist/(width*width))*body;downstream=.15 if not r.get('tributary_of') else .35
        floor=np.minimum(z,2.4*(1-t)**1.5+downstream)
        z=z*(1-weight)+floor*weight
    main=int(labs[np.where(body)[0][0],np.where(body)[1][0]])
    for n,(yy,xx) in enumerate(parts,1):
        if n==main or len(yy)<20:continue
        cx,cy=float(np.mean(xx)*STEP),float(np.mean(yy)*STEP);rx=(xx.max()-xx.min()+1)*STEP;ry=(yy.max()-yy.min()+1)*STEP
        group=min(G[k]['island_groups'],key=lambda q:(q['location'][0]-cx)**2+(q['location'][1]-cy)**2)
        flat=any(w in group['type'] for w in ['沙','堆积','珊瑚','礁坪'])
        if flat:z[yy,xx]=.22+noise[yy,xx]*.15;continue
        # Off-centre residual ridges and side valleys distinguish eroded shelf fragments from uniform cones.
        xxv=X[yy,xx];yyv=Y[yy,xx];dx=(xxv-cx-rx*.11)/(max(rx*.39,9));dy=(yyv-cy+ry*.07)/(max(ry*.35,9))
        ridge=np.exp(-(dx*dx+dy*dy))
        amp=.5 if max(rx,ry)<30 else 1.05 if max(rx,ry)<100 else 1.65
        z[yy,xx]=.33+amp*ridge+noise[yy,xx]*.55
    assert np.isfinite(z).all(),(k,'地貌表达场存在无效值')
    breaks=np.array([0,.6,1.2,1.95,2.8,3.65,4.2]);colors=np.array([[195,219,170],[202,221,170],[230,222,169],[212,190,143],[185,151,112],[231,223,207],[248,246,238]],float)
    rgb=np.zeros((*f.shape,3),float)
    for ch in range(3):rgb[:,:,ch]=np.interp(z,breaks,colors[:,ch])
    gy,gx=np.gradient(z);shade=np.clip(.99-.7*gx-.7*gy,.84,1.08);rgb=np.clip(rgb*shade[:,:,None],0,255).astype(np.uint8)
    rgba=np.dstack([rgb,np.where(f>0,255,0).astype(np.uint8)]);image=Image.fromarray(rgba)
    file=DEST/(k+'·地貌设色原图.png');image.save(file)
    np.savez_compressed(DEST/(k+'·相对地势表达场.npz'),relative_level=z.astype(np.float32),land=f>0,step=STEP)
    return base64.b64encode(file.read_bytes()).decode()

def closest(mask,x,y):
    iy,ix=round(y/STEP),round(x/STEP)
    if 0<=iy<mask.shape[0] and 0<=ix<mask.shape[1] and mask[iy,ix]:return x,y
    yy,xx=np.where(mask);assert len(xx)
    n=int(np.argmin((xx*STEP-x)**2+(yy*STEP-y)**2));return float(xx[n]*STEP),float(yy[n]*STEP)

def prepare(k):
    d=json.loads((DEST/(k+'·图层数据.json')).read_text(encoding='utf-8'))
    oldgrid=np.load(S/(OLD[k]+'·行政栅格.npz'));f=oldgrid['country'].copy();reg=oldgrid['district'].copy()
    labs,parts=components(f>0);main=max(range(len(parts)),key=lambda n:len(parts[n][0]))+1
    corrections=[]
    # The old Lan pixel-derived sea mask contained isolated ocean highlights as phantom land.
    for n,(yy,xx) in enumerate(parts,1):
        border_sliver = k=='衡岑' and xx.min()>=f.shape[1]-4 and np.ptp(yy)>300
        if n!=main and (len(yy)<20 or border_sliver):
            f[yy,xx]=0;reg[yy,xx]=0
    if k=='乌弥尔':
        moves=[(6,970,940,-270,'H12-07'),(9,970,250,155,'H12-08'),(11,770,0,0,'H12-08')]
        effective_moves={}
        for owner,min_y,dx,dy,newcode in moves:
            rid=next(i+1 for i,r in enumerate(d['districts']) if r['code']==newcode)
            pieces=[]
            for n,(yy,xx) in enumerate(parts,1):
                if n==main or np.median(yy)*STEP<min_y or not np.any(f[yy,xx]==owner):continue
                selected=f[yy,xx]>0;pieces.append((yy[selected],xx[selected]))
            if not pieces:continue
            yy=np.concatenate([p[0] for p in pieces]);xx=np.concatenate([p[1] for p in pieces]);occupied=f>0;occupied[yy,xx]=False
            choice=None
            for ddy in [0,60,-60,120,-120,180,-180]:
                for ddx in [0,60,-60,120,-120,180,-180]:
                    ny=yy+round((dy+ddy)/STEP);nx=xx+round((dx+ddx)/STEP)
                    if not ((ny>=0).all() and (ny<f.shape[0]).all() and (nx>=0).all() and (nx<f.shape[1]).all()):continue
                    if not np.any(occupied[ny,nx]):choice=(dx+ddx,dy+ddy,ny,nx);break
                if choice:break
            assert choice is not None,(k,owner,'缺少独立海面')
            dx,dy,ny,nx=choice;f[yy,xx]=0;reg[yy,xx]=0;f[ny,nx]=12;reg[ny,nx]=rid
            effective_moves[owner]=(dx,dy,newcode,min_y)
            corrections.append({'原国家码':owner,'现区码':newcode,'迁位':(dx,dy),'说明':'纠正大陆洼地/三角洲/盐岸被错误绑定远岛的图册元数据，不表示世界内领土转让'})
        # Synchronize illustrative island records with the corrected map faces.
        for isle in d.get('islands',[]):
            owner=int(isle['country_code'][1:])
            if owner in effective_moves:
                dx,dy,newcode,min_y=effective_moves[owner]
                if isle['y']>min_y:isle.update(x=isle['x']+dx,y=isle['y']+dy,country_code='H12',district_code=newcode)
    labs,parts=components(f>0);main=max(range(len(parts)),key=lambda n:len(parts[n][0]))+1;body=labs==main
    assert set(np.unique(reg))==set(range(len(d['districts'])+1))
    for i,r in enumerate(d['districts'],1):
        assert np.all(f[reg==i]==int(r['country_code'][1:])),r['code']
        # Mainland administrative cores are placed on the mainland; offshore appendages keep their district identity.
        own=(reg==i)&body
        if not own.any():own=reg==i
        sx,sy=closest(own,r.get('seat_x',r['x']),r.get('seat_y',r['y']));r['seat_x']=sx;r['seat_y']=sy;r['x']=sx;r['y']=sy
        lx,ly=closest(own,r['label_x'],r['label_y']);r['label_x']=lx;r['label_y']=ly
    d['land_paths']=allpaths(f>0)
    d['country_paths']=[allpaths(f==i) for i in range(1,len(d['countries'])+1)]
    d['national_boundaries']=geo.boundaries(f,True,STEP)
    owner={i+1:r['country_code'] for i,r in enumerate(d['districts'])}
    d['district_boundaries']=[p for p in geo.boundaries(reg,False,STEP) if owner[p['pair'][0]]==owner[p['pair'][1]]]
    for c in d['countries']:
        ci=int(c['code'][1:]);core=(f==ci)&body
        if not core.any():core=f==ci
        c['label_x'],c['label_y']=closest(core,c['label_x'],c['label_y'])
        c['capital_x'],c['capital_y']=closest(core,c['capital_x'],c['capital_y'])
        c['districts']=[r for r in d['districts'] if r['country_code']==c['code']]
    d['geography_model']=G[k];d['geography_corrections']=corrections;d['background']='第四版独立地貌设色图层，无测绘高程假定'
    d['note']='地貌设色、连续低谷与山脊独立编绘；国界及现行二级辖区叠加，地形等级为定性示意。'
    return d,f,reg,body,labs,parts

def physical(k,d,f,body,labs,parts):
    land=joined(d['land_paths']);bodypath=joined(allpaths(body))
    out=['<defs><linearGradient id="sea" x2="0" y2="1"><stop stop-color="#d2e7ed"/><stop offset="1" stop-color="#a7cbd9"/></linearGradient>','<linearGradient id="hill" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#e1cf9d"/><stop offset=".55" stop-color="#cfb081"/><stop offset="1" stop-color="#af8a69"/></linearGradient>',f'<clipPath id="land"><path d="{land}" fill-rule="evenodd"/></clipPath><clipPath id="body"><path d="{bodypath}" fill-rule="evenodd"/></clipPath></defs>', '<rect width="1600" height="1350" fill="url(#sea)"/>',f'<path d="{land}" fill="none" stroke="#dfefed" stroke-width="10"/><path d="{land}" fill="{PALETTE[1]}" fill-rule="evenodd"/>','<g clip-path="url(#body)">']
    for p in G[k]['plateaus']:out.append(f'<path d="{path(p["points"],True)}" fill="{PALETTE[p["level"]]}" opacity=".91"/>')
    for ridge in G[k]['ridges']:
        pp=path(ridge['points']);w=ridge['width'];level=ridge['level']
        for ww,color in [(w*1.65,PALETTE[2]),(w*1.16,PALETTE[3]),(w*.71,PALETTE[4])]:
            out.append(f'<path d="{pp}" fill="none" stroke="{color}" stroke-width="{ww:.1f}" stroke-linecap="round" stroke-linejoin="round"/>')
        if level>=5:out.append(f'<path d="{pp}" fill="none" stroke="{PALETTE[5]}" stroke-width="{w*.25:.1f}" stroke-linecap="round"/>')
        out.append(f'<path d="{pp}" fill="none" stroke="#685748" stroke-width="{w*.16:.1f}" opacity=".12" transform="translate(4 4)"/>')
    for p in G[k]['plains']:out.append(f'<path d="{path(p["points"],True)}" fill="{PALETTE[1]}" opacity=".95"/>')
    # Broad downstream valleys and narrow headwater valleys are reserved before drawing the river ink.
    for river in G[k]['rivers']:
        pp=path(river['points']);w=5 if river.get('tributary_of') else 12
        out.append(f'<path d="{pp}" fill="none" stroke="{PALETTE[1]}" stroke-width="{w}" stroke-linecap="round"/>')
    out.append('</g>')
    main=int(labs[np.where(body)[0][0],np.where(body)[1][0]])
    for n,(yy,xx) in enumerate(parts,1):
        if n==main or len(yy)<20:continue
        cx,cy=float(np.mean(xx)*STEP),float(np.mean(yy)*STEP)
        group=min(G[k]['island_groups'],key=lambda q:(q['location'][0]-cx)**2+(q['location'][1]-cy)**2)
        pp=joined(allpaths(labs==n));typ=group['type']
        out.append(f'<defs><clipPath id="isle{n}"><path d="{pp}" fill-rule="evenodd"/></clipPath></defs>')
        if any(word in typ for word in ['沙','堆积','珊瑚','礁坪']):
            out.append(f'<path d="{pp}" fill="#dfe4bb" fill-rule="evenodd"/>');continue
        rx=(float(xx.max()-xx.min())+1)*STEP;ry=(float(yy.max()-yy.min())+1)*STEP
        if max(rx,ry)<24:continue
        if ry>rx:points=[(cx-rx*.06,cy-ry*.27),(cx+rx*.14,cy-ry*.07),(cx-rx*.12,cy+ry*.18)]
        else:points=[(cx-rx*.3,cy-ry*.09),(cx-rx*.05,cy+ry*.15),(cx+rx*.25,cy-ry*.12)]
        out.append(f'<g clip-path="url(#isle{n})"><path d="{path(points)}" fill="none" stroke="{PALETTE[2]}" stroke-width="{min(rx,ry)*.58:.1f}" stroke-linecap="round"/><path d="{path(points)}" fill="none" stroke="url(#hill)" stroke-width="{min(rx,ry)*.29:.1f}" stroke-linecap="round"/></g>')
    # The early flat stroke draft is superseded by continuous terrain tints with subdued shading.
    relief=relative_relief(k,f,body,labs,parts)
    out=[out[0],out[1],out[2],'<rect width="1600" height="1350" fill="url(#sea)"/>',f'<path d="{land}" fill="none" stroke="#dfefed" stroke-width="9"/>',f'<image width="{f.shape[1]*STEP}" height="{f.shape[0]*STEP}" href="data:image/png;base64,{relief}"/>','<g clip-path="url(#land)">']
    for lake in G[k]['lakes']:out.append(f'<path d="{path(lake["points"],True)}" fill="#9cc8dc" stroke="#4f96ba" stroke-width=".7"/>')
    for river in G[k]['rivers']:
        width=1.7 if river.get('tributary_of') else 2.6;dash=' stroke-dasharray="5 2"' if river.get('seasonal') or river.get('type')=='人工渠' else ''
        out.append(f'<path d="{path(river["points"])}" fill="none" stroke="#287fac" stroke-width="{width}" stroke-linecap="round"{dash}/>')
    out += ['</g>',f'<path d="{land}" fill="none" stroke="#567e77" stroke-width=".65"/>']
    return out

def legend(out,y=1110):
    out.append(txt(1620,y,'地貌等级与符号',14,anchor='start',halo=0));y+=20
    for i,(level,name) in enumerate([(1,'低平原／盆底'),(2,'台地／缓坡'),(3,'丘陵／低山'),(4,'山地／高地'),(5,'高山积雪')]):
        x=1620+(i%2)*225;yy=y+(i//2)*22
        out.append(f'<rect x="{x}" y="{yy-10}" width="23" height="12" fill="{PALETTE[level]}" stroke="#7c8070" stroke-width=".4"/>');out.append(txt(x+32,yy,name,10,anchor='start',halo=0))
    y+=75
    symbols=[('国界','#754a62','8 2 1 2',1.5),('二级界','#6d716d','3 2',.65),('河流','#287fac','',1.8),('人工／季节水道','#287fac','5 2',1.3)]
    for i,(name,col,dash,width) in enumerate(symbols):
        x=1620+(i%2)*225;yy=y+(i//2)*22
        out.append(f'<path d="M {x},{yy-4} h 25" fill="none" stroke="{col}" stroke-width="{width}" stroke-dasharray="{dash}"/>');out.append(txt(x+32,yy,name,10,anchor='start',halo=0))
    out+= [txt(1620,y+51,'双圆：国都　小圆：二级治所',10,anchor='start',halo=0),txt(1620,y+71,'地势等级示意；面积、海距依正文',10,anchor='start',halo=0),txt(1620,y+91,'共历742年秋 · 第四版',10,anchor='start',halo=0)]

def country_text(c,f):
    ci=int(c['code'][1:]);x,y=c['label_x'],c['label_y'];word=c['label'];size=26;spacing=3
    for sz in [26,24,22,20,18,16,14]:
        half=(len(word)*sz+(len(word)-1)*spacing)/2
        pts=[(round((x+dx)/STEP),round((y+dy)/STEP)) for dx in [-half,0,half] for dy in [-sz/2,sz/2]]
        if all(0<=yy<f.shape[0] and 0<=xx<f.shape[1] and f[yy,xx]==ci for xx,yy in pts):size=sz;break
    c['label_size']=size
    return [txt(x,y,word,size,'#403a3d',spacing=spacing,halo=2),txt(x,y+16,c['label_suffix'],9.5,'#5b5454',spacing=1,halo=1.3)]

def render(k):
    d,f,reg,body,labs,parts=prepare(k);base=physical(k,d,f,body,labs,parts)
    start=[f'<svg xmlns="http://www.w3.org/2000/svg" width="8000" height="5143" viewBox="0 0 {W} {H}">','<rect width="2100" height="1350" fill="#f7f4e8"/>']
    out=start+base+['<rect x="1600" width="500" height="1350" fill="#f7f4e8"/>']
    for p in d['district_boundaries']:out.append(f'<path d="{path(p["points"])}" fill="none" stroke="#626f65" stroke-width=".65" stroke-dasharray="3 2" opacity=".8"/>')
    for p in d['national_boundaries']:out.append(f'<path d="{path(p["points"])}" fill="none" stroke="#faf9e6" stroke-width="3"/><path d="{path(p["points"])}" fill="none" stroke="#754a62" stroke-width="1.5" stroke-dasharray="8 2 1 2"/>')
    reserved=[]
    for c in d['countries']:
        out+=country_text(c,f);reserved.append((c['label_x'],c['label_y'],len(c['label'])*c['label_size']/2+10,32))
    for r in d['districts']:
        sx,sy=r['seat_x'],r['seat_y']
        if not any(abs(sx-c['capital_x'])<3 and abs(sy-c['capital_y'])<3 for c in d['countries']):out.append(f'<circle cx="{sx}" cy="{sy}" r="1.5" fill="#384747" stroke="#fff" stroke-width=".45"/>')
    for i,r in enumerate(d['districts'],1):
        x,y=r['label_x'],r['label_y'];word=r['name'];size=8.7 if k!='衡岑' else 10
        if any(abs(x-a)<b+len(word)*size/2 and abs(y-c)<h for a,c,b,h in reserved):
            mask=(reg==i)&body
            if not mask.any():mask=reg==i
            yy,xx=np.where(mask);candidates=list(zip(xx[::max(1,len(xx)//300)]*STEP,yy[::max(1,len(yy)//300)]*STEP))
            free=[(a,b) for a,b in candidates if all(abs(a-q)>w+len(word)*size/2 or abs(b-t)>h for q,t,w,h in reserved)]
            if free:x,y=min(free,key=lambda q:(q[0]-x)**2+(q[1]-y)**2)
            else:word=r['mark'];size=7.3
        r['label_x'],r['label_y']=float(x),float(y);r['label_text']=word
        out.append(txt(x,y,word,size,'#384039',halo=.8))
    for river in G[k]['rivers']:
        if river.get('tributary_of'):continue
        point=river['points'][len(river['points'])//2];x,y=point[0]+15,point[1]-7
        if all(abs(x-a)>b+len(river['name'])*5 or abs(y-c)>h for a,c,b,h in reserved):out.append(txt(x,y,river['name'],10,'#246e96',halo=1.3))
    for label in G[k]['labels']:
        if label['type']!='自然单元' or not any(w in label['name'] for w in ['山系','山弧','分水岭','高原']):continue
        x,y=label['x'],label['y']-26
        if all(abs(x-a)>b+len(label['name'])*5 or abs(y-c)>h for a,c,b,h in reserved):out.append(txt(x,y,label['name'],12,'#765741',spacing=1,halo=1.5))
    for c in d['countries']:
        x,y=c['capital_x'],c['capital_y'];out.append(f'<circle cx="{x}" cy="{y}" r="3.4" fill="#fff" stroke="#70516b" stroke-width=".8"/><circle cx="{x}" cy="{y}" r="1.2" fill="#70516b"/>');out.append(txt(x+6,y+5,c['capital'],9.4,'#68455e',anchor='start',halo=1.6))
    out += [txt(45,45,k+'地形与政区图',27,anchor='start',spacing=2),txt(45,71,f'{len(d["countries"])}国 · {len(d["districts"])}二级行政区',11,anchor='start'),txt(1540,55,'北',15),'<path d="M1540 70 V115 M1533 80 L1540 65 L1547 80" fill="none" stroke="#455b63" stroke-width="1.3"/>']
    cols=2 if k=='衡岑' else 3;split=math.ceil(len(d['countries'])/cols)
    out.append(txt(1620,45,'国家与现行二级区',17,anchor='start',spacing=1,halo=0))
    max_y=0
    for ci,c in enumerate(d['countries']):
        if ci%split==0:y=82
        x=1620+(ci//split)*(460/cols);title=c['code']+' '+c['name'];size=min(10.2,(450/cols)/len(title))
        out.append(txt(x,y,title,size,anchor='start',halo=0));y+=24
        for r in c['districts']:
            title=r['mark']+' '+r['name'];size=min(9.2,(450/cols)/len(title));out.append(txt(x,y,title,size,anchor='start',halo=0));y+=16 if k=='萨阑' else 18
        y+=14;max_y=max(max_y,y)
    assert max_y<1100,(k,max_y)
    legend(out,max(1090,max_y+12));out.append('</svg>')
    (A/(PREFIX[k]+'·'+k+'大陆·疆域地形图.svg')).write_text('\n'.join(out),encoding='utf-8')
    # A physical companion keeps geographic region labels legible, without 271 district labels.
    natural=start+base+['<rect x="1600" width="500" height="1350" fill="#f7f4e8"/>']
    for p in d['national_boundaries']:natural.append(f'<path d="{path(p["points"])}" fill="none" stroke="#856b7c" stroke-width=".7" stroke-dasharray="6 3" opacity=".7"/>')
    natural += [txt(45,45,k+'自然地理图',28,anchor='start',spacing=2),txt(45,72,'山川 · 地貌 · 文明形成环境',11,anchor='start'),txt(1540,55,'北',15),'<path d="M1540 70 V115 M1533 80 L1540 65 L1547 80" fill="none" stroke="#455b63" stroke-width="1.3"/>']
    for label in G[k]['labels']:
        name=label['name'];x,y=label['x'],label['y'];natural.append(txt(x,y,name,15 if label['type']=='自然单元' else 12,'#654f3d',spacing=1,halo=2))
    for river in G[k]['rivers']:
        point=river['points'][len(river['points'])//2];natural.append(txt(point[0]+12,point[1]-7,river['name'],11,'#1d6792',halo=1.5))
    for lake in G[k]['lakes']:
        p=np.array(lake['points']);natural.append(txt(float(p[:,0].mean()),float(p[:,1].mean()),lake['name'],10,'#1d6792',halo=1))
    natural.append(txt(1620,45,'自然单元与阅读提示',17,anchor='start',halo=0));y=82
    for n,label in enumerate(q for q in G[k]['labels'] if q['type']=='自然单元'):
        natural.append(txt(1620,y,f'{n+1:02d}　'+label['name'],13,anchor='start',halo=0));y+=34
    natural+= [txt(1620,y+20,'岛群成因与淡水条件见地理志',12,anchor='start',halo=0),txt(1620,y+44,'低谷留白，山脊与水系分别核定',12,anchor='start',halo=0),txt(1620,y+68,'高原与山地有别，绿色不等于森林',12,anchor='start',halo=0)]
    legend(natural,1090);natural.append('</svg>')
    (A/(str(int(PREFIX[k])+3).zfill(2)+'·'+k+'·自然地理图.svg')).write_text('\n'.join(natural),encoding='utf-8')
    # Store a reusable native physical layer for the continental overview.
    (DEST/(k+'·自然地理图层.svg')).write_text('\n'.join(start+base+['</svg>']),encoding='utf-8')
    for c in d['countries']:c['districts']=[r for r in d['districts'] if r['country_code']==c['code']]
    (DEST/(k+'·图层数据.json')).write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8')
    np.savez_compressed(DEST/(k+'·行政栅格.npz'),country=f,district=reg,step=STEP)
    print(k,'地形与政区、自然地理两图',len(d['districts']),'区；海岛元数据修订',len(d['geography_corrections']),flush=True)

def world():
    out=['<svg xmlns="http://www.w3.org/2000/svg" width="10000" height="6667" viewBox="0 0 2400 1600">','<rect width="2400" height="1600" fill="#c1dce6"/>','<rect x="2110" width="290" height="1600" fill="#f7f4e8"/>',txt(60,80,'弥 洛 洲 · 地 形 与 国 界',34,anchor='start',halo=0)]
    y=125
    for k,dx,dy,scale in [('衡岑',25,160,.32),('乌弥尔',650,680,.43),('萨阑',1400,690,.4)]:
        d=json.loads((DEST/(k+'·图层数据.json')).read_text(encoding='utf-8'));f=np.load(DEST/(k+'·行政栅格.npz'))['country']
        inner=(DEST/(k+'·自然地理图层.svg')).read_text(encoding='utf-8');inner=inner[inner.index('>')+1:inner.rindex('</svg>')]
        inner=inner.replace('<rect width="2100" height="1350" fill="#f7f4e8"/>','').replace('<rect width="1600" height="1350" fill="url(#sea)"/>','')
        # Prefix every SVG definition so terrain clip paths cannot collide between continents.
        inner=rewrite_ids(inner,k)
        out.append(f'<g transform="translate({dx} {dy}) scale({scale})">{inner}')
        for p in d['national_boundaries']:out.append(f'<path d="{path(p["points"])}" fill="none" stroke="#6b4160" stroke-width="2.6" stroke-dasharray="9 3 1 3"/>')
        for c in d['countries']:out.append(txt(c['label_x'],c['label_y'],c['label'],c['label_size']*1.35,spacing=3,halo=2))
        out+=['</g>',txt(dx+160,dy-28,k,29,spacing=5,halo=1)]
        out.append(txt(2132,y,k,24,anchor='start',spacing=4,halo=0));y+=39
        for c in d['countries']:out.append(txt(2132,y,c['code']+' '+c['name'],min(17,250/len(c['code']+' '+c['name'])),anchor='start',halo=0));y+=31
        y+=31
    out += [txt(490,480,'西 候 洋',30,'#456f86',spacing=4,halo=0),txt(1320,650,'两 门 海',24,'#456f86',spacing=4,halo=0),txt(60,1395,'北 ↑　点划线：国家边界　底色：自然地势',19,anchor='start',halo=0),txt(60,1433,'两门海最窄岸隙约240公里；常用港路300—850公里',17,anchor='start',halo=0),txt(60,1469,'衡岑—乌弥尔最近适航海路约2400—3000公里',17,anchor='start',halo=0),txt(60,1505,'相对位置与航路示意；三陆4030万平方公里，共历742年秋',17,anchor='start',halo=0)]
    for i in range(1,6):
        x=800+(i-1)*180;out.append(f'<rect x="{x}" y="1450" width="35" height="20" fill="{PALETTE[i]}" stroke="#777" stroke-width=".5"/>');out.append(txt(x+17,1490,['低平地','台地','丘陵','山地','雪岭'][i-1],14,halo=0))
    out.append('</svg>');(A/'00·弥洛洲·三陆国界图.svg').write_text('\n'.join(out),encoding='utf-8');print('弥洛洲总图：三陆29国、地势、水系、距离说明',flush=True)

def rewrite_ids(text,prefix):
    import re
    ids=re.findall(r'id="([^"]+)"',text)
    for key in ids:text=text.replace('id="'+key+'"','id="'+prefix+'-'+key+'"').replace('url(#'+key+')','url(#'+prefix+'-'+key+')')
    return text

if __name__=='__main__':
    import sys
    if '--world' in sys.argv:world()
    else:
        for k in OLD:render(k)
        world()
