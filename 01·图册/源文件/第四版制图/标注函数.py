import numpy as np
from html import escape
import 绘图函数 as geo

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

def noise(X,Y,scale,seed):
    rng=np.random.default_rng(seed);hh=int(Y.max()/scale)+3;ww=int(X.max()/scale)+3
    nodes=rng.normal(0,1,(hh,ww));gx=X/scale;gy=Y/scale;ix=gx.astype(int);iy=gy.astype(int);tx=gx-ix;ty=gy-iy
    tx=tx*tx*(3-2*tx);ty=ty*ty*(3-2*ty)
    return (1-ty)*((1-tx)*nodes[iy,ix]+tx*nodes[iy,ix+1])+ty*((1-tx)*nodes[iy+1,ix]+tx*nodes[iy+1,ix+1])
