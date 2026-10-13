"""Build original SVG cartographic layers over imagegen physical artwork.
Raster artwork is kept unchanged. Names and boundary geometry are separate.
"""
from pathlib import Path
from collections import defaultdict
import json, base64, math, re
import numpy as np
from PIL import Image, ImageDraw
from html import escape

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

