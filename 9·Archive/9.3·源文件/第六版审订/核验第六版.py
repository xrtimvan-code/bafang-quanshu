"""核对本次文字增量与书籍结构；语义审读另见审订说明。"""
from pathlib import Path
from collections import Counter
from urllib.parse import unquote
import json
import re

HERE = Path(__file__).resolve().parent
BOOK = HERE.parents[2]
SOURCE = HERE.parent
baseline = json.loads((HERE / '原始基线.json').read_text(encoding='utf-8-sig'))
files = sorted(p for p in BOOK.rglob('*.md')
               if not any(x in p.parts for x in ('.git', '源文件', '旧版', '旧稿', '旧版存档')))
texts = {p: p.read_text(encoding='utf-8-sig') for p in files}
count = lambda s: len(re.findall(r'[\u4e00-\u9fff]', s))
before = sum(baseline['文件'].values())
after = sum(map(count, texts.values()))
minimum = (before + 3) // 4
checks = []


def check(name, result, detail=''):
    checks.append({'项目': name, '通过': bool(result), '说明': detail})


check('冻结基线与四分之一增量', before == 446867 and after - before >= minimum,
      f'基线{before}；现稿{after}；净增{after-before}；最低{minimum}汉字')
links = []
for p, text in texts.items():
    for match in re.finditer(r'!?\[[^\]]*\]\(([^)]+)\)', text):
        target = unquote(match[1].strip('<>').split('#', 1)[0])
        if not target or re.match(r'[a-z]+://', target):
            continue
        if not (p.parent / target).exists():
            links.append([str(p.relative_to(BOOK)), target])
check('正式正文图片与文件链接', not links, links)
volumes = sorted(BOOK.glob('*·卷*'))
check('三卷幻羽专志与总目入口', len(volumes) == 3 and all(
    (p / '01·纵论' / '19·幻羽志.md').is_file() and
    str((p / '01·纵论' / '19·幻羽志.md').relative_to(BOOK)).replace('\\', '/')
    in texts[BOOK / '00·志纲与总目.md'] for p in volumes))
records = []
duplicates = []
paragraphs = Counter()
for volume in volumes:
    countries = sorted(p for p in (volume / '02·横论').glob('*.md') if not p.name.startswith('00'))
    for p in countries:
        text = texts[p]
        section = re.search(r'^## [^\n]*幻羽[^\n]*\n(.*?)(?=^## |\Z)', text, re.M | re.S)
        headings = re.findall(r'^### (.+)$', section[1], re.M) if section else []
        # 衡岑、乌弥尔前三条为核心叙事；萨阑以第一、二、三事单列。
        stories = ([x for x in headings if re.match(r'第[一二三]事：', x)]
                   if volume.name.startswith('04') else headings[:3])
        records.append({'卷': volume.name, '国家志': p.name, '主要异闻': stories,
                        '幻羽章节汉字': count(section[1]) if section else 0})
        if section:
            for paragraph in re.split(r'\n\s*\n', section[1]):
                if count(paragraph) >= 80:
                    paragraphs[paragraph.strip()] += 1
check('29国分别具有至少三处主要异闻', len(records) == 29 and all(
    len(x['主要异闻']) == 3 and x['幻羽章节汉字'] >= 2000 for x in records), records)
story_count = sum(len(x['主要异闻']) for x in records)
check('新增独立描写至少20处', story_count >= 20, f'仅计国志核心异闻{story_count}则；不计同事异本及综论补记')
duplicates = [p[:100] for p, n in paragraphs.items() if n > 1]
check('国志新增长段落无原样重复', not duplicates, duplicates)
body = '\n'.join(text for p, text in texts.items() if '·卷' in str(p))
people = json.loads((SOURCE / '主要人物名释核对.json').read_text(encoding='utf-8-sig'))
check('46位主要人物原有姓名解释保留', len(people) == 46 and all(p['说明'] in body for p in people))
check('各专志保留归纳', all('归纳' in t for p, t in texts.items() if '·卷' in str(p)))
check('未混入旧占位符或英文残词', not any(x in body for x in ['SHORT-', 'rival', 'TODO', 'TBD']))
protected = ['会稽', '巴', '罗勒', '瓜凉', '芦赫', '大元溪', '卡兹帕', '摩揭始罗', '化玻', '鹿野', '霄安', '七斗']
civilization_text = '\n'.join(texts[p / '01·纵论' / '03·文明志.md'] for p in volumes)
check('12个指定文明名称保留', all(x in civilization_text for x in protected))
registry = json.loads((SOURCE / '名称注册表.json').read_text(encoding='utf-8-sig'))
entries = {x['id']: x for x in registry['entries']}
check('名称实体类别订正', all(entries[i]['kind'] == kind for i, kind in {
    'LAN-0094': 'town', 'LAN-0096': 'town', 'LAN-0198': 'institution',
    'HY-0492': 'language', 'HY-0493': 'language', 'S-0556': 'given_name'}.items()))
check('普通词与专名替换设有语境约束', all(entries[i].get('context_only') and entries[i].get('replacement_guard')
      for i in ['LAN-0079', 'LAN-0097', 'HY-0087', 'HY-0090', 'HY-0178', 'HY-0205', 'S-0576', 'S-0585', 'S-0613']))
check('误替普通词的已知病句消除', not any(x in body for x in [
    '榕约共木本42.9', '榕约共木本4200', '两分政治', '两分安排', '区两分务',
    '允沅允沅京', '胥泊胥泊城', '乌腊乌腊城', '喀木喀木水', '阿都阿都溪']))
report = {'审订版次': 6, '图册版次': 5, '基线汉字': before, '现稿汉字': after,
          '净增汉字': after - before, '最低净增': minimum, '增幅': (after-before)/before,
          '正式Markdown文件数': len(files), '保守核心异闻数': story_count,
          '检查': checks, '国别异闻目录': records,
          '程序检查通过': all(x['通过'] for x in checks),
          '说明': '字数与链接检查不能证明语义无矛盾；本次分卷审读、共同名称修订及跨卷事实复核另见审订说明。图像未因幻羽修改。'}
(HERE / '第六版文字核验.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
for item in checks:
    if not item['通过']:
        print('未通过：', item['项目'], str(item['说明'])[:1200])
print(f'检查 {sum(x["通过"] for x in checks)}/{len(checks)}；正文{after}汉字；净增{after-before}；核心异闻{story_count}')
raise SystemExit(0 if report['程序检查通过'] else 1)
