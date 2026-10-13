from pathlib import Path
import json,re,shutil,hashlib
import numpy as np
from PIL import Image
O=Path(__file__).parent;ROOT=O.parents[1];STAGE=O/'待核图册';BOOK=Path(r'D:\dreaming\西湾盛洲志');A=BOOK/'01·图册';S=A/'源文件'
report={'版次':'第三版政区地图','国家数':29,'二级区数':271,'大陆':[],'错误':[]}
def pairs(f):
    a,b=f[:,:-1],f[:,1:];x,y=f[:-1,:],f[1:,:];ps=np.r_[np.stack([a[a!=b],b[a!=b]],1),np.stack([x[x!=y],y[x!=y]],1)]
    return set(tuple(sorted((int(a),int(b)))) for a,b in ps if a and b)
expected_lan={(1,2),(1,3),(2,3),(2,4),(3,4),(3,5),(3,6),(4,5),(5,6),(5,7),(6,7)}
for k,n,prefix in [('岚衡',37,'01'),('洄原',123,'02'),('燧岬',111,'03')]:
    d=json.loads((STAGE/(k+'·图层数据.json')).read_text(encoding='utf-8'));grid=np.load(STAGE/(k+'·行政栅格.npz'));f=grid['country'];district=grid['district'];unit=float(grid['step'])
    assert len(d['districts'])==n;assert set(np.unique(district))==set(range(n+1))
    if k=='岚衡':assert pairs(f)==expected_lan
    else:assert pairs(f)==pairs(np.load(O/'第二版基线'/(k+'·行政栅格.npz'))['country'])
    original=json.loads((O/'第二版基线'/(k+'·图层数据.json')).read_text(encoding='utf-8'));lookup={r['code']:r for r in original['districts']}
    for i,r in enumerate(d['districts'],1):
        assert np.all(f[district==i]==int(r['country_code'][1:]))
        for key in ['code','name','population_wan','seat','capital','official_name','official','official_title','faction']:
            if key in lookup[r['code']]:assert r.get(key)==lookup[r['code']][key],(r['code'],key)
    for c in d['countries']:
        ci=int(c['code'][1:]);assert f[round(c['label_y']/unit),round(c['label_x']/unit)]==ci;assert f[round(c['capital_y']/unit),round(c['capital_x']/unit)]==ci
    stem=prefix+'·'+k+'大陆·疆域地形图'
    with Image.open(STAGE/(stem+'.png')) as im:assert (im.width,im.height)==(8000,5143)
    report['大陆'].append({'大陆':k,'国家数':len(d['countries']),'二级区数':n,'接壤关系':'与既定名录一致','国名字位及国都':'全部在本国图域','分区图域':'无缺区、无跨国覆盖','行政字段及人口':'与书稿数据一致'})
with Image.open(STAGE/'00·西湾盛洲·三陆国界图.png') as im:assert (im.width,im.height)==(10000,6667)

archive=A/'旧版'/'第三版修订前';archive.mkdir(parents=True,exist_ok=True)
for p in A.glob('0[0-3]·*'):
    if p.suffix in ['.png','.svg'] and not (archive/p.name).exists():shutil.copy2(p,archive/p.name)
data_archive=archive/'源文件';data_archive.mkdir(exist_ok=True)
for k in ['岚衡','洄原','燧岬']:
    for suffix in ['·图层数据.json','·行政栅格.npz']:
        p=S/(k+suffix)
        if p.exists() and not (data_archive/p.name).exists():shutil.copy2(p,data_archive/p.name)
for p in STAGE.glob('0[0-3]·*'):
    if p.suffix in ['.png','.svg']:shutil.copy2(p,A/p.name)
for k in ['岚衡','洄原','燧岬']:
    for suffix in ['·图层数据.json','·行政栅格.npz']:shutil.copy2(STAGE/(k+suffix),S/(k+suffix))
previews=A/'预览';previews.mkdir(exist_ok=True)
for p in O.glob('0[0-3]·*预览.png'):shutil.copy2(p,previews/p.name)

# Change only prose describing replaced map symbols.
for volume in BOOK.glob('*卷*'):
    for p in volume.rglob('*.md'):
        t=p.read_text(encoding='utf-8');new=t.replace('地图红线','地图国界线').replace('红线为国界，细虚线为区界','深紫实线为国界，细点划线为区界')
        if new!=t:p.write_text(new,encoding='utf-8')
g=A/'图册说明.md';t=g.read_text(encoding='utf-8').replace('紅实线为国界，蓝虚线为二级区界，星号为国都','深紫实线为国界，细点划线为二级区界，双圆点为国都')
t=t.replace('区号与右侧索引对应','小辖区的区号与右侧索引对应').replace('中文文字、国界和行政区界独立排制，不采用生图中的文字。','中文文字、国界和行政区界独立排制，不采用生图中的文字。第三版采用淡领土色、宋体宽字距国名及常规地区名；国名依本国图域排放，城区、牧旗、谷地和群岛的地区轮廓按不同的空间条件细化。')
t+='\n## 第三版参考与检查\n\n[第三版政区修订说明](源文件/第三版政区修订说明.md)记录线型、注记层次和图层核验。[预览](预览/02·洄原大陆·疆域地形图预览.png)适合屏幕查看，正式PNG保留高清尺寸。旧版图和旧图层保存在旧版/第三版修订前。\n'
g.write_text(t,encoding='utf-8')
note='''# 第三版政区修订说明

本版针对上一版国界和二级区边界呈机械切块、国名位置失当及注记层次混杂的问题，重新排制四图。维持29国、271个二级区、人口与地方官名录，三大陆既定陆地接壤关系全部保留。

## 图形与注记

国境采用不重复的局部转折，并使相邻国家共享同一条界线。二级区改用具有示意地形阻隔代价的区域生长方法，保留治所的大致地域与群岛归属；边线的弯曲密度、地区面积和轮廓有别。算法图形用于表达辖境，不是新测绘证据，也不作为设定中某次领土变更。河谷、山脊与旧契界的法律意义仍依各国志说明。

国家采用淡色领土区分、深紫实线界线；二级区采用细点划界线。国名使用宋体宽字距，国家名称与政体称谓分两行，字位从本国图域选择。省、旗、领、府和公社通常显示名称；狭小地区仅标区号并在名录中查名，必要时使用细引线。国都用双圆点标识；海岛所属国家采用小号‘某国属’文字。大陆形状和现有大小岛链维持第二版底画，国界、分区和文字为独立图层。

大洲图复用三张大陆图的国界与国家辖境色，图中以国家名称代替原代码标签；国家代码只在右侧名录用于查阅。大陆图宽8000像素，大洲图宽10000像素，预览图宽1600像素。

## 参考资料

- [法国行政区图，1991，得克萨斯大学Perry–Castañeda地图馆藏](https://maps.lib.utexas.edu/maps/france.html?p=print)：参考国境、地区界和部门界的线型层次，以及国家、地区和城市的注记区分。原图由美国中央情报局制作，本书未复制其图形。
- [瑞士联邦测绘局概览地图](https://www.swisstopo.admin.ch/en/general-maps-of-switzerland)：参考州、区和市镇边界的分层表达，以及行政图与地势图的组合。
- [美国人口普查局边界与区划地图](https://www.census.gov/geographies/reference-maps/2026/geo/bas/2026-bas-maps.html)：参考行政边界、机关类别和地名的分层。

## 核验

第三版图层JSON和行政栅格均在本目录；完整核验见第三版政区核验.json。全部二级区都有图域，没有跨国覆盖；国家名称和国都位于对应国家图域；行政名称、人口及地方官字段与第二版书稿一致；大陆图和洲图共享国境。旧版资料单独归档，正文的相对图片链接继续指向最新版。
'''
(S/'第三版政区修订说明.md').write_text(note,encoding='utf-8')
(S/'第三版政区核验.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
code=S/'第三版制图';code.mkdir(exist_ok=True)
for p in O.glob('*.py'):shutil.copy2(p,code/p.name)

readme='''# 西湾盛洲志

虚构世界的历史、地理与社会政治志书，记述共历742年秋的岚衡、洄原与燧岬。三卷共80篇正文，29个国家、271个二级行政区。每卷保留按领域组织的纵论，并另设大陆总志及各国志组成横论。

[志纲与总目](00·志纲与总目.md) · [图册](01·图册/图册说明.md) · [最新版地图说明](01·图册/源文件/第三版政区修订说明.md)

## 阅读

可直接阅读Markdown，也可把本目录作为Obsidian资料库打开。正文以相对路径引用最新版地图。高清大陆图宽8000像素，大洲图宽10000像素；旧版图保留在图册的旧版目录。

![洄原政区图预览](01·图册/预览/02·洄原大陆·疆域地形图预览.png)

## 下载地图

PNG使用Git LFS保存，避免高清和旧版图超过GitHub普通文件大小限制。克隆后运行`git lfs pull`获取实际图片；SVG、Markdown和地图数据作为普通文件保存。浏览器预览不替代正文的面积、人口和航程估数。

## 文件

- `00·志纲与总目.md`：全书说明与导航。
- `01·图册`：四张正式地图、预览、图层资料和旧版存档。
- `02·卷一·岚衡`、`03·卷二·洄原`、`04·卷三·燧岬`：纵论与横论。

本书的人物、国家、史料与历史事件属于虚构设定。地图参考现实行政地图的表达方法，未将现实疆域复制为本书国境。
'''
(BOOK/'README.md').write_text(readme,encoding='utf-8')
(BOOK/'.gitignore').write_text('__pycache__/\n*.pyc\n.obsidian/\n',encoding='utf-8')
broken=[]
for p in [BOOK/'README.md',BOOK/'00·志纲与总目.md',g]+[p for v in BOOK.glob('*卷*') for p in v.rglob('*.md')]:
    for link in re.findall(r'\]\(([^)]+)\)',p.read_text(encoding='utf-8')):
        if not link.startswith(('http','codex')) and not (p.parent/link.split('#')[0]).exists():broken.append([p.name,link])
assert not broken,broken
report['书稿与地图链接']='全部有效';(O/'第三版核验.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
dst=ROOT/'outputs'/'西湾盛洲志';shutil.copytree(BOOK,dst,dirs_exist_ok=True,ignore=shutil.ignore_patterns('.git','__pycache__','*.pyc'))
for p in BOOK.rglob('*'):
    if p.is_file() and '.git' not in p.parts and '__pycache__' not in p.parts and p.suffix!='.pyc':assert hashlib.sha256(p.read_bytes()).digest()==hashlib.sha256((dst/p.relative_to(BOOK)).read_bytes()).digest()
print(json.dumps(report,ensure_ascii=False))
