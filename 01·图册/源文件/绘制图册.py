from pathlib import Path
import json
import math
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Ellipse, Circle
from matplotlib import font_manager, patheffects
from matplotlib.path import Path as PlotPath
from matplotlib.patches import PathPatch
from matplotlib.colors import LightSource
from scipy.interpolate import CubicSpline
from collections import Counter, defaultdict

ROOT = Path(r'D:\dreaming\西湾盛洲志\01·图册')
ROOT.mkdir(parents=True, exist_ok=True)
font_manager.fontManager.addfont(r'C:\Windows\Fonts\msyh.ttc')
plt.rcParams.update({'font.family': 'Microsoft YaHei', 'svg.fonttype': 'path', 'axes.unicode_minus': False})

# Coordinates establish relative placement, not a surveyed projection.
countries = [
    dict(name='罗勒共和国', color='#cfb9db', capital=('罗勒城', 20, 43),
         poly=[(10,25),(9,42),(12,55),(22,60),(35,61),(40,50),(39,40),(36,30),(28,26)],
         units=[('罗勒城邦',20,43),('银岬城邦',18,54),('橄丘城邦',28,35),('东门城邦',34,47),('外海岛盟',5,42)]),
    dict(name='萨汀王国', color='#e6c798', capital=('萨汀堡',34,19),
         poly=[(10,25),(28,26),(36,30),(42,36),(44,30),(48,28),(55,20),(55,8),(40,4),(25,6),(15,12)],
         units=[('王台领',34,19),('南谷领',37,10),('红岩领',19,17),('南衡边领',48,24),('天尺神庙领',43,17)]),
    dict(name='巴梁王国', color='#c6c99a', capital=('梁城',49,51),
         poly=[(35,61),(50,65),(62,63),(65,54),(62,46),(60,43),(55,39),(48,36),(42,36),(36,30),(39,40),(40,50)],
         units=[('梁城领',49,51),('上巴领',45,59),('铜山领',43,43),('中衡领',58,49),('北衡领',55,61)]),
    dict(name='玄峡盟国', color='#a8cbb8', capital=('石门',59,34),
         poly=[(42,36),(48,36),(55,39),(60,43),(66,36),(65,29),(55,20),(48,28),(44,30)],
         units=[('石门城邦',59,34),('上峡城邦',57,40),('双瀑城邦',54,35),('回水城邦',57,29),('雾岭城邦',45,32),('悬台城邦',49,32),('铜渡城邦',47,35.4),('月潭城邦',61,29),('南关城邦',54,24)]),
    dict(name='澄川国', color='#efd79a', capital=('澄都',71,35),
         poly=[(60,43),(62,46),(67,46),(71,43),(74,33),(73,24),(65,29),(66,36)],
         units=[('澄都府',71,35),('上澄府',67,42),('赤岸府',70,28),('西峡府',65,38)]),
    dict(name='越宁王朝', color='#bad3a1', capital=('稽京',80,49),
         poly=[(62,63),(75,66),(84,61),(87,54),(85,43),(83,36),(74,33),(71,43),(67,46),(62,46),(65,54)],
         units=[('京畿郡',80,49),('稽中郡',78,42),('镜泽郡',79,36),('北稽郡',77,59),('东衡郡',67,53)]),
    dict(name='临海国', color='#e9b5a2', capital=('潮安',88,40),
         poly=[(87,54),(92,50),(94,42),(92,35),(93,28),(89,20),(81,18),(73,24),(74,33),(83,36),(85,43)],
         units=[('潮安府',88,40),('白沙府',85,25),('海岬府',90,48),('舟列府',98,31)]),
]
islands = [(4,43,1.3,2.3,0),(5,39,0.8,1.2,0),(3,47,0.9,1.5,0),(97,32,1.1,2.2,6),(99,28,0.7,1.4,6),(97,37,0.8,1.3,6)]
rivers = [
    ('稽水', [(67,56),(71,53),(76,50),(80,49),(79,43),(74,39),(71,35),(77,34),(83,37),(88,40),(94,41)]),
    ('澄水', [(44,38),(49,36),(53,38),(57,36),(59,34),(64,35),(67,34),(71,35)]),
    ('巴川干流', [(53,62),(49,57),(49,51),(46,47),(43,43),(39,43)]),
]
roads = [([(20,43),(28,45),(34,47),(40,50),(49,51),(58,49),(65,38),(71,35)],'#936448'),
         ([(20,43),(22,34),(28,26),(34,19)],'#936448'),
         ([(34,19),(43,22),(54,24),(59,34)],'#936448')]

def clip_half(poly, a, b, limit):
    if not poly:
        return []
    out=[]
    for p,q in zip(poly, poly[1:]+poly[:1]):
        fp=a*p[0]+b*p[1]-limit
        fq=a*q[0]+b*q[1]-limit
        ip,iq=fp <= 1e-9,fq <= 1e-9
        if ip:
            out.append(p)
        if ip != iq:
            t=fp/(fp-fq)
            out.append((p[0]+t*(q[0]-p[0]),p[1]+t*(q[1]-p[1])))
    return out

# One coastline spline and one canonical curve per shared edge prevent gaps.
def edge_key(p,q):
    return tuple(sorted((tuple(np.round(p,6)),tuple(np.round(q,6)))))

edge_counts=Counter(edge_key(p,q) for c in countries for p,q in zip(c['poly'],c['poly'][1:]+c['poly'][:1]))
coast_graph=defaultdict(list)
for (p,q),count in edge_counts.items():
    if count==1:
        coast_graph[p].append(q);coast_graph[q].append(p)
assert all(len(v)==2 for v in coast_graph.values())
start=min(coast_graph);outline=[start];previous=None;current=start
while True:
    nxt=next(v for v in coast_graph[current] if v!=previous)
    if nxt==start: break
    outline.append(nxt);previous,current=current,nxt
outline.append(start)
outline=np.asarray(outline,float)
coast_t=np.r_[0,np.cumsum(np.linalg.norm(np.diff(outline,axis=0),axis=1))]
coast_spline=CubicSpline(coast_t,outline,bc_type='periodic')
edge_curves={}
for i in range(len(outline)-1):
    t=np.linspace(coast_t[i],coast_t[i+1],max(30,int((coast_t[i+1]-coast_t[i])*16)))
    pts=coast_spline(t);d=coast_spline(t,1)
    normal=np.c_[-d[:,1],d[:,0]];normal/=np.linalg.norm(normal,axis=1)[:,None]
    u=np.linspace(0,1,len(t))
    ripple=(.16*np.sin(t*3.7)+.07*np.sin(t*8.3))*np.sin(np.pi*u)**2
    coast_key=edge_key(outline[i],outline[i+1])
    bay_depth={edge_key((9,42),(12,55)):2.8,edge_key((92,35),(93,28)):2.0,
               edge_key((25,6),(40,4)):1.15,edge_key((12,55),(22,60)):.9}.get(coast_key,0)
    signed_area=np.sum(outline[:-1,0]*outline[1:,1]-outline[1:,0]*outline[:-1,1])
    ripple+=np.sign(signed_area)*bay_depth*np.exp(-((u-.53)/.18)**2)*np.sin(np.pi*u)**2
    pts+=normal*ripple[:,None]
    key=edge_key(outline[i],outline[i+1])
    edge_curves[key]=pts if tuple(outline[i])==key[0] else pts[::-1]

def curved_edge(p,q,admin=False):
    key=edge_key(p,q)
    if not admin and key in edge_curves:
        pts=edge_curves[key]
    else:
        a,b=np.array(key[0]),np.array(key[1]);v=b-a;length=np.linalg.norm(v)
        t=np.linspace(0,1,max(20,int(length*12)))
        normal=np.array([-v[1],v[0]])/max(length,.001)
        phase=(a[0]+a[1]*1.31+b[0]*.43)%6.28
        amplitude=min(.28 if admin else .46,length*.06)
        offset=amplitude*np.sin(np.pi*t)**2*(np.sin(t*2*np.pi+phase)+.3*np.sin(t*6*np.pi+phase))
        pts=a[None,:]+t[:,None]*v[None,:]+offset[:,None]*normal
    return pts if tuple(np.round(p,6))==key[0] else pts[::-1]

def curved_poly(poly,admin=False):
    return np.vstack([curved_edge(p,q,admin)[:-1] for p,q in zip(poly,poly[1:]+poly[:1])])

def flowing(points):
    points=np.asarray(points,float)
    t=np.r_[0,np.cumsum(np.linalg.norm(np.diff(points,axis=0),axis=1))]
    return CubicSpline(t,points,bc_type='natural')(np.linspace(0,t[-1],max(80,int(t[-1]*12))))

def island_shape(x,y,w,h,seed):
    t=np.linspace(0,2*np.pi,90)
    r=1+.13*np.sin(3*t+seed)+.07*np.sin(7*t+seed*.7)
    return np.c_[x+w*.5*r*np.cos(t),y+h*.5*r*np.sin(t)]

def terrain(ax,patches,admin):
    xs=np.linspace(-2,106,850);ys=np.linspace(-3,73,600)
    xx,yy=np.meshgrid(xs,ys)
    ridge_x=51+.16*(yy-30)+2*np.sin(yy*.12)
    ridge=np.exp(-((xx-ridge_x)/4.3)**2)*np.exp(-((yy-47)/26)**4)
    hills=.25*np.exp(-((xx-43)/12)**2-((yy-34)/10)**2)+.17*np.exp(-((xx-29)/13)**2-((yy-36)/17)**2)
    noise=.045*(np.sin(xx*1.4+yy*.7)+.5*np.sin(xx*3.1-yy*1.8))
    elev=ridge+hills+noise*(ridge+.15)
    shade=LightSource(azdeg=310,altdeg=42).hillshade(elev,vert_exag=5,dx=.12,dy=.12)
    clip=PathPatch(PlotPath.make_compound_path(*[p.get_path() for p in patches]),transform=ax.transData)
    relief=ax.imshow(shade,extent=(-2,106,-3,73),origin='lower',cmap='Greys',alpha=.17 if admin else .3,zorder=3)
    relief.set_clip_path(clip)
    rng=np.random.default_rng(2042)
    for cx,cy,sx,sy,n in [(66,53,3,5,35),(44,45,4,5,35),(42,33,2,3,30),(27,34,3,4,25)]:
        for x,y in zip(rng.normal(cx,sx,n),rng.normal(cy,sy,n)):
            if any(p.get_path().contains_point((x,y)) for p in patches):
                ax.plot(x,y,marker='^',ms=2.5,color='#537b55',alpha=.35 if admin else .65,zorder=5)
    for x,y in [(77,35.8),(78,37.2),(80,36.1),(79,38)]:
        ax.plot([x-.25,x,x+.25],[y-.2,y+.2,y-.2],color='#497f77',lw=.6,zorder=10)

def label(ax,x,y,s,size=11,color='#313532',weight='normal',align='center'):
    return ax.text(x,y,s,fontsize=size,color=color,fontweight=weight,ha=align,va='center',zorder=20,
        path_effects=[patheffects.withStroke(linewidth=3,foreground='#f7f3e8',alpha=.9)])

def setup(title, subtitle, admin=False):
    fig=plt.figure(figsize=(22,16),facecolor='#f7f3e8')
    fig.text(.045,.947,title,fontsize=29,fontweight='bold',color='#273d43')
    fig.text(.046,.917,subtitle,fontsize=12,color='#5b6661')
    ax=fig.add_axes([.04,.17,.69 if admin else .9,.71])
    ax.set_facecolor('#dcebf0')
    ax.set_xlim(-2,106); ax.set_ylim(-3,73); ax.set_aspect('equal')
    ax.set_xticks([]);ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_color('#a3b5b8')
    patches=[]
    for c in countries:
        patch=Polygon(curved_poly(c['poly']),facecolor=c['color'],edgecolor='#62694f',lw=1.25,zorder=2)
        ax.add_patch(patch);patches.append(patch)
    ax._country_patches=patches
    terrain(ax,patches,admin)
    for x,y,w,h,idx in islands:
        ax.add_patch(Polygon(island_shape(x,y,w,h,x+y),facecolor=countries[idx]['color'],edgecolor='#666b5d',lw=.8,zorder=2))
    for x,y,w,h,idx in [(6,45,.45,.7,0),(3.6,40.7,.5,.9,0),(7,36.8,.35,.55,0),(96.2,34.5,.5,.8,6),(99.8,34,.45,.65,6),(100.5,29.8,.35,.5,6),(95.4,27,.6,.9,6)]:
        ax.add_patch(Polygon(island_shape(x,y,w,h,x+y),facecolor=countries[idx]['color'],edgecolor='#666b5d',lw=.55,zorder=2))
    coast=curved_poly([tuple(p) for p in outline[:-1]])
    ax.plot(*np.vstack([coast,coast[:1]]).T,color='#527c83',lw=4,alpha=.13,zorder=1)
    label(ax,0,24,'落照海',18,'#537886')
    label(ax,101,53,'沧溟海',18,'#537886')
    label(ax,65,3,'珊瑚海域',17,'#537886')
    label(ax,48,69,'北缘寒冷高地',11,'#67776d')
    ax.annotate('',xy=(101,69),xytext=(101,62),arrowprops=dict(facecolor='#31484f',width=2,headwidth=9),zorder=30)
    label(ax,101,71,'北',13)
    return fig,ax

def rivers_and_roads(ax, geography=False):
    for name,points in rivers:
        pts=flowing(points);ax.plot(*pts.T,color='#387f9c',lw=2.2,zorder=8)
    tributaries=[[(69,60),(70,57),(71,53)],[(82,55),(81,52),(80,49)],[(76,46),(77,44),(79,43)],[(50,42),(52,40),(53,38)],[(62,40),(60,37),(59,34)],[(54,57),(52,54),(49,51)],[(44,54),(46,53),(49,51)],[(91,43),(90,41.5),(88,40)]]
    for points in tributaries:
        pts=flowing(points);ax.plot(*pts.T,color='#548da2',lw=.9,zorder=8)
    for points in [[(88,40),(90,40.5),(93.6,42)],[(88,40),(90,39),(93.3,38)]]:
        ax.plot(*flowing(points).T,color='#548da2',lw=.85,zorder=8)
    for points,color in roads:
        ax.plot(*flowing(points).T,color=color,lw=1.25,ls=(0,(4,3)),zorder=7)
    ax.plot(*flowing([(12,52),(8,47),(5,42),(9,33),(12,25),(16,18)]).T,color='#387f9c',lw=1.5,ls=(0,(1,3)),zorder=7)
    for x,y,w,h in [(78,36,3.0,1.6),(80,38,1.7,1.0),(61,29,1,.7)]:
        ax.add_patch(Polygon(island_shape(x,y,w,h,x+y),facecolor='#86bbc9',edgecolor='#387f9c',lw=.5,zorder=9))
    if geography:
        label(ax,82,45,'稽水',10,'#24617f')
        label(ax,64,32.5,'澄水',10,'#24617f')
        label(ax,46,53,'巴川',10,'#24617f')

def export(fig,name):
    fig.savefig(ROOT/(name+'.png'),dpi=190,facecolor=fig.get_facecolor())
    fig.savefig(ROOT/(name+'.svg'),facecolor=fig.get_facecolor())
    plt.close(fig)

fig,ax=setup('岚衡大陆 · 山川与交通总图','西湾盛洲志 · 第一卷图一  |  共历742年秋  |  北向上；方位示意，不作等距测绘')
mountains=[(57,63),(56,60),(57,57),(57,54),(58,51),(59,48),(59,45),(58,42),(57,39),(55,36),(53,32),(50,28),(48,25)]
for x,y in mountains:
    for dx,dy,scale in [(-.7,.4,.65),(.7,-.4,.8),(0,0,1)]:
        verts=[(x+dx-.62*scale,y+dy-.35*scale),(x+dx,y+dy+1.0*scale),(x+dx+.65*scale,y+dy-.35*scale)]
        ax.add_patch(Polygon(verts,facecolor='#989779',edgecolor='#696f5b',lw=.45,zorder=6))
        ax.plot([x+dx-.28*scale,x+dx,x+dx+.24*scale],[y+dy+.42*scale,y+dy+1.0*scale,y+dy+.48*scale],color='#ece8d6',lw=.7,zorder=6)
label(ax,60,59,'北衡雪岭',10)
label(ax,61,47,'衡脊',11,weight='bold')
label(ax,49,26,'南衡断崖',10)
rivers_and_roads(ax,True)
for c in countries:
    name,x,y=c['capital']; ax.plot(x,y,'*',ms=12,color='#3e3d34',zorder=14);label(ax,x,y-1.7,name,10)
for x,y,s in [(76,55,'稽水大平原'),(89,31,'东溟海岸带'),(69,31,'澄川河谷'),(47,55,'巴川盆地'),(48,31,'玄峡山地'),(24,50,'罗勒西海沿岸'),(30,15,'萨汀台原')]:
    label(ax,x,y,s,12,weight='bold')
label(ax,4,35,'外海列岛',10);label(ax,98,24,'舟列群岛',10)
label(ax,9,47,'罗勒湾',9,'#24617f');label(ax,93,30,'白沙湾',9,'#24617f')
label(ax,82,39,'镜泽湖群',10);label(ax,18,13,'红岩海岸',10)
ax.plot(58,41.4,marker='D',ms=9,color='#9b4f78',zorder=15)
label(ax,54,44,'云根祖山',11,'#783858')
ax.annotate('',xy=(58,41.4),xytext=(54,43.3),arrowprops=dict(arrowstyle='-',color='#783858'))
ax.plot(59,39.3,'s',ms=6,color='#855b38',zorder=15);label(ax,63,40,'中衡山口',9)
fig.text(.055,.13,'图例：★ 国都／盟国首府    ▲ 山岭    ◆ 祖山    蓝实线 河流    棕虚线 山道    蓝点线 近海航路',fontsize=12)
fig.text(.055,.102,'底色为七国辖域；海湾、岬角、支流与地形纹理为编纂示意。三河保持既定汇流关系，未绘全部支流。',fontsize=11,color='#5d655f')
fig.text(.055,.077,'八大地理单元包括衡脊山系，其余七区以名称标注。洄原、燧岬相对岚衡的方位尚未确定，故不入图。',fontsize=11,color='#5d655f')
export(fig,'岚衡大陆_山川交通图')

fig,ax=setup('岚衡大陆 · 七国与三十七区','西湾盛洲志 · 第一卷图二  |  国界与二级区界为编纂示意；编号对应右侧名录',True)
index=0
entries=[]
for country_idx,c in enumerate(countries):
    inside=[u for u in c['units'] if (u[1],u[2]) not in [(5,42),(98,31)]]
    for name,x,y in inside:
        cell=list(c['poly'])
        for oname,ox,oy in inside:
            if name==oname: continue
            cell=clip_half(cell,2*(ox-x),2*(oy-y),ox*ox+oy*oy-x*x-y*y)
        if len(cell)>=3:
            district=Polygon(curved_poly(cell,admin=True),facecolor='none',edgecolor='#737d70',lw=.75,ls=(0,(3,3)),zorder=4)
            district.set_clip_path(ax._country_patches[country_idx]);ax.add_patch(district)
    for name,x,y in c['units']:
        index+=1;entries.append((index,c['name'],name,x,y))
        ax.add_patch(Circle((x,y),1.0,facecolor='#fbf8ee',edgecolor='#49594f',lw=.7,zorder=17))
        ax.text(x,y,str(index),fontsize=9,ha='center',va='center',zorder=18,color='#253b3d')
    cx=np.mean([p[0] for p in c['poly']]);cy=np.mean([p[1] for p in c['poly']])
    # Place country labels away from most administrative markers.
    positions={'罗勒共和国':(25,58),'萨汀王国':(30,23),'巴梁王国':(46,62),'玄峡盟国':(48,26),'澄川国':(70,39),'越宁王朝':(79,63),'临海国':(87,21)}
    label(ax,*positions[c['name']],c['name'],12,weight='bold')
rivers_and_roads(ax)
ax.plot(58,41.4,marker='D',ms=7,color='#9b4f78',zorder=19)
label(ax,57,45,'祖山共管',9,'#783858')
ax.scatter([43,19,37],[17,17,10],s=150,facecolors='none',edgecolors='#9b4f78',lw=2,zorder=19)
label(ax,98,23,'牙环岛区*',8,'#783858')
fig.text(.758,.869,'二级行政区全目',fontsize=16,fontweight='bold',color='#273d43')
row=.838
for c in countries:
    fig.text(.758,row,c['name'],fontsize=11,fontweight='bold',color='#344b46');row-=.018
    for number,cname,name,x,y in entries:
        if cname==c['name']:
            fig.text(.767,row,f'{number:02d}  {name}',fontsize=10,color='#3d4944');row-=.0145
    row-=.007
fig.text(.055,.132,'图例：数字圆点 二级区位置索引    实线 国界    虚线 二级区概略边界    紫环 宗教自治集中地区    ◆ 祖山共管',fontsize=11)
fig.text(.055,.104,'岛盟、舟列府包含群岛；主图只绘代表岛屿。紫环依次提示天尺神庙领、赤砾矿区、明泉区，牙环岛区以文字提示。',fontsize=10,color='#5d655f')
fig.text(.055,.077,'二级区内部界线为根据区位生成的示意分区，不能据此判断面积、领土争议或精确驻地；三级区未全绘。',fontsize=10,color='#5d655f')
export(fig,'岚衡大陆_七国三十七区图')

(ROOT/'地图数据.json').write_text(json.dumps({'说明':'方位示意；poly为控制节点，实际边界由共享曲线生成；无测绘比例','国家':countries,'河流':rivers,'二级区索引':entries,'曲线国家边界':{c['name']:curved_poly(c['poly']).round(4).tolist() for c in countries}},ensure_ascii=False,indent=2),encoding='utf-8')
assert index==37
print('已输出两幅地图的PNG、SVG及地图数据；二级区数量：',index)
