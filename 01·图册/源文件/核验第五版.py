"""核对现行图文；视觉审阅另由记录明确列出，不由程序推定。"""
from pathlib import Path
from collections import Counter
import json,re,sys
import xml.etree.ElementTree as ET
import numpy as np
from PIL import Image,ImageDraw

S=Path(__file__).resolve().parent;A=S.parent;B=A.parent
sys.path.insert(0,str(S/'第四版制图'))
import 绘制图册 as cart
checks=[];details={}
def check(name,condition,detail=''):
    checks.append({'项目':name,'通过':bool(condition),'说明':detail})

def samples(points):
    # Read the actual cubic water path, including its control points.
    tokens=re.findall(r'[MC]|-?\d+(?:\.\d+)?',cart.water_path(points))
    here=np.array([float(tokens[1]),float(tokens[2])]);out=[here];n=3
    while n<len(tokens):
        assert tokens[n]=='C';v=np.array(list(map(float,tokens[n+1:n+7]))).reshape(3,2)
        for t in np.linspace(0,1,9)[1:]:out.append((1-t)**3*here+3*(1-t)**2*t*v[0]+3*(1-t)*t*t*v[1]+t**3*v[2])
        here=v[2];n+=7
    return np.array(out)

def crossing(a,b,c,d):
    v=b-a;w=d-c;den=v[0]*w[1]-v[1]*w[0]
    if abs(den)<1e-8:return None
    q=c-a;t=(q[0]*w[1]-q[1]*w[0])/den;u=(q[0]*v[1]-q[1]*v[0])/den
    return a+t*v if 1e-6<t<1-1e-6 and 1e-6<u<1-1e-6 else None

article=(A/'07·山川岛屿考.md').read_text(encoding='utf-8')
counts=[];national_total=0;district_total=0
for land,expected in [('衡岑',(7,37,11)),('乌弥尔',(12,123,22)),('萨阑',(10,111,19))]:
    d=json.loads((S/(land+'·图层数据.json')).read_text(encoding='utf-8'))
    grid=np.load(S/(land+'·行政栅格.npz'));f=grid['country'];reg=grid['district'];water=cart.lake_mask(land,f.shape)
    pairs={tuple(p['pair']) for p in d['national_boundaries']}
    national_total+=len(d['countries']);district_total+=len(d['districts'])
    check(land+'国家、二级区及双边陆界组合数',(len(d['countries']),len(d['districts']),len(pairs))==expected)
    check(land+'二级区归属',all(np.all(f[reg==i]==int(r['country_code'][1:])) for i,r in enumerate(d['districts'],1)))
    check(land+'二级区均有图形',set(np.unique(reg))==set(range(len(d['districts'])+1)))
    check(land+'治所落点',all(reg[round(r['seat_y']/1.5),round(r['seat_x']/1.5)]==i and not water[round(r['seat_y']/1.5),round(r['seat_x']/1.5)] for i,r in enumerate(d['districts'],1)))
    check(land+'国都落点',all(f[round(c['capital_y']/1.5),round(c['capital_x']/1.5)]==int(c['code'][1:]) and not water[round(c['capital_y']/1.5),round(c['capital_x']/1.5)] for c in d['countries']))
    natural=A/(str(int(cart.PREFIX[land])+3).zfill(2)+'·'+land+'·自然地理图.svg')
    svg=natural.read_text(encoding='utf-8')
    check(land+'自然单元文字',all(x['name'] in svg and x['name'] in article for x in cart.G[land]['labels'] if x['type']=='自然单元'))
    check(land+'岛群图号与说明',all(x['name'] in svg and x['name'] in article and '岛'+str(i) in svg for i,x in enumerate(cart.G[land]['island_groups'],1)))
    labels,parts=cart.components(f>0);main=max(range(len(parts)),key=lambda i:len(parts[i][0]))+1;groups=Counter()
    for n,(yy,xx) in enumerate(parts,1):
        if n!=main:groups[cart.island_form(land,yy,xx)[8]['name']]+=1
    check(land+'每组已命名岛群存在独立陆块',all(groups[g['name']]>0 for g in cart.G[land]['island_groups']),str(dict(groups)))
    rs=cart.G[land]['rivers'];curves=[samples(r['points']) for r in rs];bad=[];offland=[];mouths=[]
    lake_faces=[]
    for lake in cart.G[land]['lakes']:
        im=Image.new('L',(f.shape[1],f.shape[0]));ImageDraw.Draw(im).polygon([(x/1.5,y/1.5) for x,y in lake['points']],fill=1)
        face=np.array(im)>0;lake_faces.append(face)
        check(land+'·'+lake['name']+'湖面在岸内',np.all(f[face]>0))
        allowed=set(lake.get('inflows',[])+[lake.get('outflow')])
        unrelated=[]
        for r,curve in zip(rs,curves):
            if r['name'] in allowed:continue
            indices=np.rint(curve/1.5).astype(int)
            if any(face[y,x] for x,y in indices):unrelated.append(r['name'])
        check(land+'·'+lake['name']+'无无关干流穿湖',not unrelated,str(unrelated))
    check(land+'各湖水面不误叠',all(not np.any(a&b) for i,a in enumerate(lake_faces) for b in lake_faces[i+1:]))
    for i,r in enumerate(rs):
        for j,s in enumerate(rs[i+1:],i+1):
            for a,b in zip(curves[i],curves[i][1:]):
                for c,e in zip(curves[j],curves[j][1:]):
                    hit=crossing(a,b,c,e)
                    if hit is not None and all(np.linalg.norm(hit-np.array(p))>3 for p in [r['points'][0],r['points'][-1],s['points'][0],s['points'][-1]]):
                        bad.append([r['name'],s['name'],np.round(hit,2).tolist()])
        for x,y in curves[i][:-2]:
            ix,iy=round(x/1.5),round(y/1.5)
            if not f[iy,ix] and not (f[max(0,iy-5):iy+6,max(0,ix-5):ix+6]>0).any():offland.append([r['name'],round(x,1),round(y,1)])
        if r['termination'] in ['胥溟海','勒汶西海','瑟铎南海域','西海','两门海','东海','南汇海']:
            x,y=r['points'][-1];iy,ix=round(y/1.5),round(x/1.5)
            mouths.append((r['name'],bool((f[max(0,iy-3):iy+4,max(0,ix-3):ix+4]==0).any())))
        parent=r.get('tributary_of') or r.get('branch_of')
        if parent:
            q=next(s for s in rs if s['name']==parent);point=r['points'][0] if r.get('branch_of') else r['points'][-1]
            check(land+'·'+r['name']+'汇分流连接',any(np.linalg.norm(np.array(p)-point)<.1 for p in q['points']))
    check(land+'无未接通的平面交叉',not bad,str(bad))
    self_hits=[]
    for r,curve in zip(rs,curves):
        for i,(a,b) in enumerate(zip(curve,curve[1:])):
            for c,e in zip(curve[i+2:],curve[i+3:]):
                hit=crossing(a,b,c,e)
                if hit is not None:self_hits.append(r['name'])
    check(land+'河线无自交',not self_hits,str(sorted(set(self_hits))))
    check(land+'河线没有越海串岛',not offland,str(offland[:8]))
    check(land+'入海河段抵达岸线',all(ok for _,ok in mouths),str(mouths))
    if land=='萨阑':
        sea=f==0;near=np.zeros(f.shape,bool)
        near[1:]|=sea[:-1];near[:-1]|=sea[1:];near[:,1:]|=sea[:,:-1];near[:,:-1]|=sea[:,1:]
        port=next(i+1 for i,r in enumerate(d['districts']) if r['code']=='S05-04')
        check('照浦海港有本国海岸',np.any((reg==port)&(f==5)&near))
        curve=curves[next(i for i,r in enumerate(rs) if r['name']=='德维恩河')]
        owners=[int(f[round(y/1.5),round(x/1.5)]) for x,y in curve]
        check('德维恩河从埃沃拉港域入海',next(owner for owner in reversed(owners) if owner)!=0 and next(owner for owner in reversed(owners) if owner)==5)
    # Every international pair has its own explanatory row, rather than a generic list of neighbors.
    cs={int(c['code'][1:]):c['name'] for c in d['countries']}
    check(land+'双边界段说明齐全',all(cs[a]+'—'+cs[b] in article for a,b in pairs))
    details[land]={'离岸陆块':len(parts)-1,'岛群分配':dict(groups),'岛内季节短水':len(d.get('island_streams',[])),'主要河线':len(rs),'双边陆界':len(pairs)}

check('国家、二级区合计',(national_total,district_total)==(29,271))
people=json.loads((S/'主要人物名释核对.json').read_text(encoding='utf-8'))
body='\n'.join(p.read_text(encoding='utf-8') for p in B.glob('*·卷*/*/*.md'))
check('主要人物姓名解释46人',len(people)==46 and all(p['说明'] in body for p in people))
check('正文没有内部简称占位标记','SHORT-' not in body and 'rival' not in body)
check('各专志保留归纳',all('归纳' in p.read_text(encoding='utf-8') for p in B.glob('*·卷*/*/*.md')))
links=[]
for p in B.rglob('*.md'):
    if '.git' in p.parts or '旧版' in p.parts:continue
    for match in re.finditer(r'!?\[[^\]]*\]\(([^)]+)\)',p.read_text(encoding='utf-8')):
        target=match[1].strip('<>').split('#',1)[0]
        if not target or re.match(r'[a-z]+://',target):continue
        if not (p.parent/target).exists():links.append([str(p.relative_to(B)),target])
check('现行Markdown图片与文件链接',not links,str(links))
maps=sorted(p for p in A.glob('0[0-6]·*.png'))
check('七幅高清图与预览齐全',len(maps)==7 and all((A/'预览'/(p.stem+'预览.png')).exists() for p in maps))
check('图像尺寸',all(Image.open(p).size==((10000,6667) if p.name.startswith('00') else (8000,5143)) for p in maps))
check('六幅大陆图标记第五版',all('第五版' in p.read_text(encoding='utf-8') for p in A.glob('0[1-6]·*.svg')))
world=(A/'00·弥洛洲·三陆国界图.svg').read_text(encoding='utf-8')
check('洲图29个国都符号',len(re.findall(r'r="4" fill="#fff" stroke="#70516b"',world))==29)
root=ET.fromstring(world)
ys=[float(e.attrib['y']) for e in root.iter('{http://www.w3.org/2000/svg}text') if float(e.attrib.get('x','0'))==2132]
check('洲图国家名录逐行无重叠',len(ys)==32 and all(b-a>=28 for a,b in zip(ys,ys[1:])))
check('七幅矢量图可解析',all(ET.parse(p).getroot().tag.endswith('svg') for p in A.glob('0[0-6]·*.svg')))
report={'版次':5,'检查':checks,'地理记录':details,'程序检查通过':all(x['通过'] for x in checks),'视觉审阅':'须在图像生成后逐图检查；程序不自动宣告视觉通过','内容依据':'07·山川岛屿考.md；主要地理单元28，命名岛群26，双边陆界52。未编号的碎小近岸附岛另按邻岸地形合述。'}
(S/'第五版综合核验.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
for item in checks:
    if not item['通过']:print('未通过',item['项目'],item['说明'])
print('程序检查',sum(x['通过'] for x in checks),'/',len(checks))
print(json.dumps(details,ensure_ascii=False))
sys.exit(0 if report['程序检查通过'] else 1)
