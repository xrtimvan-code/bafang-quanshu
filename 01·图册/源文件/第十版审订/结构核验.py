"""只核结构与共同口径；不替代逐段语义审校。运行前更新进度与线索.py。"""
from pathlib import Path
from urllib.parse import unquote
import json
import re
import subprocess

WORK = Path(__file__).resolve().parent
BOOK = Path(r'D:\dreaming\弥洛洲志')
SOURCE = BOOK / '01·图册/源文件'
baseline = json.loads((WORK / '原始基线.json').read_text(encoding='utf-8'))
progress = json.loads((WORK / '最新量化进度.json').read_text(encoding='utf-8'))
paths = sorted(p for p in BOOK.rglob('*.md') if not any(
    x in p.parts for x in ('.git', '源文件', 'work', '旧版', '旧稿', '旧版存档')))
texts = {p: p.read_text(encoding='utf-8-sig') for p in paths}
checks = []


def check(name, result, detail):
    checks.append({'项目': name, '通过': bool(result), '说明': detail})


bad_links = []
for p, text in texts.items():
    for m in re.finditer(r'!?\[[^\]]*\]\(([^)]+)\)', text):
        target = unquote(m[1].strip('<>').split('#', 1)[0])
        if target and not re.match(r'[a-z]+://', target) and not (p.parent / target).exists():
            bad_links.append([p.relative_to(BOOK).as_posix(), target])
check('正式文件及图片链接', not bad_links, bad_links)
actual = sum(len(re.findall(r'[\u4e00-\u9fff]', t)) for t in texts.values())
check('计量对应当前磁盘', actual == progress['全部正式Markdown汉字'], actual)
check('固定基线及百分之二十门槛', baseline['正文基线'] == 940026 and
      baseline['最低净增'] == 188006 and
      progress['去报告索引及完全重复长段的有效净增'] >= 188006, progress)
toc = texts[BOOK / '00·志纲与总目.md']
body = '\n'.join(t for p, t in texts.items() if '·卷' in str(p))
check('现状与公共规模', all(x in toc for x in ('742年秋', '1.38亿', '4030万', '271')), '')
check('篇章可重构原则已写入', '篇章修订原则' in toc and '合并、拆分、移置' in toc, '')
check('无已知英文残留及占位', not re.search(
    r'\b(?:rival|likewise|however|therefore|TODO|TBD)\b', body, re.I), '')
civil = '\n'.join(t for p, t in texts.items() if p.name == '03·文明志.md')
check('十二文明名称保留', all(x in civil for x in (
    '会稽', '巴', '罗勒', '瓜凉', '芦赫', '大元溪', '卡兹帕', '摩揭始罗',
    '化玻', '鹿野', '霄安', '七斗')), '')
for land, countries, districts in [('衡岑', 7, 37), ('乌弥尔', 12, 123), ('萨阑', 10, 111)]:
    volume = next(p for p in BOOK.glob('*·卷*') if land in p.name)
    data = json.loads((SOURCE / (land + '·图层数据.json')).read_text(encoding='utf-8-sig'))
    national = [p for p in (volume / '02·横论').glob('*.md') if not p.name.startswith('00')]
    check(land + '国家及二级区数', len(national) == len(data['countries']) == countries
          and len(data['districts']) == districts, [len(national), len(data['districts'])])
    domain = texts[volume / '01·纵论/08·方域志.md']
    atlas = texts[BOOK / '01·图册/地名与图号索引.md']
    missing = [r['name'] for r in data['districts'] if
               r['name'] not in domain or r['name'] not in atlas or r['code'] not in atlas]
    check(land + '现行区名图号对照', not missing, missing)
    new = [p for p in (volume / '01·纵论').glob('*.md') if int(p.name.split('·')[0]) >= 20]
    check(land + '新篇总目入口及篇末归纳', bool(new) and all(
        p.relative_to(BOOK).as_posix() in toc and '归纳' in texts[p] for p in new),
        [p.name for p in new])
changed_maps = subprocess.check_output(['git', '-C', str(BOOK), 'diff', '--name-only',
    baseline['基线提交'], '--', '*.png', '*.svg', '*图层数据.json', '*行政栅格.npz'], encoding='utf-8')
check('现图未被文字修订误改', not changed_maps.strip(), changed_maps)
report = {'固定基线': baseline['基线提交'], '程序项目': checks,
          '程序检查通过': all(c['通过'] for c in checks),
          '限制': '不检查每一句的意义，不证明历史因果与指代正确；须结合实际覆盖记录、改句及交叉审读。'}
(WORK / '最新结构核验.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
for c in checks:
    if not c['通过']:
        print('未通过：', c['项目'], str(c['说明'])[:700])
print('程序项目', sum(c['通过'] for c in checks), '/', len(checks))
raise SystemExit(0 if report['程序检查通过'] else 1)
