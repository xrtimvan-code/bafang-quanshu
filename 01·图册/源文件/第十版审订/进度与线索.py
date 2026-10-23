from pathlib import Path
from collections import Counter
import re,json,subprocess
B=Path(r'D:\dreaming\弥洛洲志');W=Path(__file__).resolve().parent
base=json.loads((W/'原始基线.json').read_text(encoding='utf-8'))
han=lambda s:len(re.findall('[\u4e00-\u9fff]',s))
formal=lambda p:not any(x in p.parts for x in ['.git','源文件','work','旧版','旧稿','旧版存档'])
real=lambda p:'·卷' in str(p) and '索引' not in p.name
paths=sorted(p for p in B.rglob('*.md') if formal(p))
texts={p:p.read_text(encoding='utf-8-sig') for p in paths}
def unique_count(entries):
 seen=set();n=0
 for t in entries:
  for para in re.split(r'\n\s*\n',t):
   para=para.strip();k=han(para)
   if k>=100:
    if para in seen:continue
    seen.add(para)
   n+=k
 return n
old={}
for row in base['文件']:
 p=B/row['文件']
 if real(p):
  old[p]=subprocess.check_output(['git','-C',str(B),'show',base['基线提交']+':'+row['文件']],encoding='utf-8')
raw_growth=sum(han(t) for p,t in texts.items() if real(p))-sum(han(t) for t in old.values())
unique_growth=unique_count(t for p,t in texts.items() if real(p))-unique_count(old.values())
# 改写一份旧重复段可能使去重差额上升；不能将这当作实际新写字数。
def prose_only(t):
 t=re.sub(r'!?\[[^\]]*\]\([^)]*\)','',t)
 return '\n'.join(line for line in t.splitlines()
                  if not re.match(r'^\s*(?:#{1,6}\s|>)',line))
new_prose=[prose_only(t) for p,t in texts.items() if real(p)]
old_prose=[prose_only(t) for t in old.values()]
prose_growth=sum(han(t) for t in new_prose)-sum(han(t) for t in old_prose)
prose_unique_growth=unique_count(new_prose)-unique_count(old_prose)
# 另扣一千字余量，覆盖短摘要和导读中未能机械识别的复述；不把它宣称为新增。
growth=min(raw_growth,unique_growth,prose_growth,prose_unique_growth)-1000
vols=[]
for v in sorted(B.glob('*·卷*')):
 before=sum(han(t) for p,t in old.items() if v in p.parents)
 now=sum(han(t) for p,t in texts.items() if real(p) and v in p.parents)
 vols.append({'卷':v.name,'旧有效正文':before,'现有效正文':now,'未去重净增':now-before})
out={'全部正式Markdown汉字':sum(han(t) for t in texts.values()),'相对全量基线净增':sum(han(t) for t in texts.values())-base['正文基线'],'去报告索引及完全重复长段的有效净增':growth,'最低有效净增':base['最低净增'],'剩余至少':max(0,base['最低净增']-growth),'分卷':vols,'仅计量不等于审校完成':True}
out.update({'剔除链接标题与引文元数据后净增':prose_growth,
            '同口径再去完全重复长段后净增':prose_unique_growth,
            '另扣短摘要及导读保守余量':1000,
            '有效净增算法':'全卷非索引净增、去重净增、纯叙述净增、纯叙述去重净增取最小值，再扣1000；源文件及报告不计。'})
(W/'最新量化进度.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(out,ensure_ascii=False))
suspects=[]
for p,t in texts.items():
 for line_no,line in enumerate(t.splitlines(),1):
  reasons=[]
  if re.search(r'(的的|是是|了了|并且且|因此因此|以及及|但是但|由于因为|所以因此)',line):reasons.append('叠字或关联词')
  if re.search(r'(?<!\d)(?:74[3-9]|7[5-9]\d|[89]\d\d)年',line):reasons.append('742以后的年份，须区分任期未来计划与已发生叙事')
  if re.search(r'\b(?:rival|likewise|however|therefore|TODO|TBD)\b',line,re.I):reasons.append('英文残留')
  if reasons:suspects.append({'文件':p.relative_to(B).as_posix(),'行':line_no,'线索':reasons,'句段':line[:450]})
(W/'机械筛查候选.json').write_text(json.dumps(suspects,ensure_ascii=False,indent=2),encoding='utf-8')
print('候选线索',len(suspects),'；不自动认定为错误')
