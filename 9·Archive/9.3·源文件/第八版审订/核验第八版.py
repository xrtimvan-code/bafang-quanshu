"""结构、增补范围及共同口径检查；不能代替故事和历史因果审读。"""
from pathlib import Path
from urllib.parse import unquote
from collections import Counter
import json
import re
import subprocess

HERE = Path(__file__).resolve().parent
BOOK = HERE.parents[2]
SOURCE = HERE.parent
BASE = '760b73167e459412e370d7a41fc9ef2041f6bc20'
baseline = json.loads((HERE / '原始基线.json').read_text(encoding='utf-8-sig'))
formal = sorted(p for p in BOOK.rglob('*.md') if not any(
    x in p.parts for x in ('.git', '源文件', 'work', '旧版', '旧稿', '旧版存档')))
text = {p: p.read_text(encoding='utf-8-sig') for p in formal}
hanzi = lambda s: len(re.findall(r'[\u4e00-\u9fff]', s))
checks = []


def check(name, result, detail=''):
    checks.append({'项目': name, '通过': bool(result), '说明': detail})


def original(path):
    return subprocess.run(['git', '-C', str(BOOK), 'show', BASE + ':' +
                           path.relative_to(BOOK).as_posix()], capture_output=True,
                          check=True, encoding='utf-8').stdout


links = []
for p, t in text.items():
    for m in re.finditer(r'!?\[[^\]]*\]\(([^)]+)\)', t):
        target = unquote(m[1].strip('<>').split('#', 1)[0])
        if not target or re.match(r'[a-z]+://', target):
            continue
        if not (p.parent / target).exists():
            links.append([str(p.relative_to(BOOK)), target])
check('正式正文图片与文件链接', not links, links)
countries = []
added_paragraphs = Counter()
for volume in sorted(BOOK.glob('*·卷*')):
    for p in sorted((volume / '02·横论').glob('*.md')):
        if p.name.startswith('00'):
            continue
        before = original(p)
        now = text[p]
        old_paragraphs = set(re.split(r'\n\s*\n', before))
        new_paragraphs = [s.strip() for s in re.split(r'\n\s*\n', now)
                          if s.strip() and s not in old_paragraphs]
        for s in new_paragraphs:
            if hanzi(s) >= 80:
                added_paragraphs[s] += 1
        countries.append({'国家志': str(p.relative_to(BOOK)),
                          '原稿汉字': hanzi(before), '现稿汉字': hanzi(now),
                          '净增汉字': hanzi(now)-hanzi(before),
                          '新增或改写长段数': sum(hanzi(s) >= 80 for s in new_paragraphs)})
check('29国均有实质文字增补', len(countries) == 29 and all(
    c['净增汉字'] >= 7000 and c['新增或改写长段数'] >= 25 for c in countries), countries)
duplicates = [p[:120] for p, n in added_paragraphs.items() if n > 1]
check('国别新增长段无原样套用', not duplicates, duplicates)
body = '\n'.join(t for p, t in text.items() if '·卷' in str(p))
check('各专志保留归纳', all('归纳' in t for p, t in text.items() if '·卷' in str(p)))
check('没有年公里等单位混写与旧占位符', not any(
    x in body for x in ['年公里', 'rival', 'SHORT-', 'TODO', 'TBD']))
people = json.loads((SOURCE / '主要人物名释核对.json').read_text(encoding='utf-8-sig'))
check('46位主要人物释名仍可对读', len(people) == 46 and all(p['说明'] in body for p in people))
civilizations = '\n'.join(text[p / '01·纵论' / '03·文明志.md'] for p in BOOK.glob('*·卷*'))
check('12文明名保持', all(n in civilizations for n in [
    '会稽', '巴', '罗勒', '瓜凉', '芦赫', '大元溪', '卡兹帕', '摩揭始罗', '化玻', '鹿野', '霄安', '七斗']))
geo = []
for land, nc, nd in [('衡岑', 7, 37), ('乌弥尔', 12, 123), ('萨阑', 10, 111)]:
    d = json.loads((SOURCE / (land + '·图层数据.json')).read_text(encoding='utf-8-sig'))
    check(land + '国家及二级区数', (len(d['countries']), len(d['districts'])) == (nc, nd))
    v = next(p for p in BOOK.glob('*·卷*') if land in p.name)
    domain = text[v / '01·纵论' / '08·方域志.md']
    atlas_index = text[BOOK / '01·图册' / '地名与图号索引.md']
    check(land + '二级区名录与图码索引齐全', all(
        r['name'] in domain and r['code'] in atlas_index and r['name'] in atlas_index
        for r in d['districts']))
    geo.append({'大陆': land, '国家': nc, '二级区': nd})
map_changes = subprocess.run(['git', '-C', str(BOOK), 'diff', '--name-only', BASE, '--',
                              '*.png', '*.svg', '*行政栅格.npz', '*图层数据.json'],
                             capture_output=True, encoding='utf-8', check=True).stdout.strip()
check('本轮没有改变现行地理图层', not map_changes, map_changes)
check('洲级数字口径保留', all(s in text[BOOK / '00·志纲与总目.md'] for s in [
    '4030万', '1.38亿', '271', '240公里', '300—850公里', '2400—3000公里']))
age_bad = []
age_count = 0
for p, t in text.items():
    for m in re.finditer(r'(\d{2,3})年生[，、,；;\s]*742年(?:约|时|秋)?(?:约)?(\d{1,3})岁', t):
        age_count += 1
        if abs(742-int(m[1])-int(m[2])) > 1:
            age_bad.append([str(p.relative_to(BOOK)), m[0]])
check('明确出生与现年算术', not age_bad, {'匹配': age_count, '异常': age_bad})
before_total = baseline['正文基线']
after_total = sum(map(hanzi, text.values()))
check('固定基线净增至少百分之五十', after_total-before_total >= baseline['最低净增'], {'净增': after_total-before_total, '目标': baseline['最低净增']})
report = {'文字审订版次': 8, '图册版次': 5, '基准提交': BASE,
          '原稿汉字': before_total, '现稿汉字': after_total, '净增汉字': after_total-before_total,
          '检查': checks, '国志增补范围': countries,
          '程序检查通过': all(c['通过'] for c in checks),
          '限制': '长段与字数检查只核实增补范围；历史机制、叙事逻辑和语言修订的依据见审订说明及分卷审读记录，不据本程序宣称语义绝无遗漏。'}
(HERE / '第八版文字核验.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
for c in checks:
    if not c['通过']:
        print('未通过', c['项目'], str(c['说明'])[:1000])
print('检查', sum(c['通过'] for c in checks), '/', len(checks), '净增', after_total-before_total)
raise SystemExit(0 if report['程序检查通过'] else 1)
