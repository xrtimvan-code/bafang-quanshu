"""机械核验仅覆盖所列项目；逐段语义审读须另见人工记录。"""
from pathlib import Path
from collections import Counter
import json
import re
import subprocess
import urllib.parse

WORK = Path(__file__).resolve().parent
BOOK = Path(r"D:\dreaming\弥洛洲志")
SOURCE = BOOK / "01·图册" / "源文件"
baseline = json.loads((WORK / "原始基线.json").read_text(encoding="utf-8-sig"))
checks = []


def check(label, success, detail):
    checks.append({"项目": label, "通过": bool(success), "说明": detail})


missing = []
links = 0
characters = 0
for row in baseline["文件"]:
    path = BOOK / row["文件"]
    text = path.read_text(encoding="utf-8-sig")
    characters += len(re.findall(r"[\u4e00-\u9fff]", text))
    check("合并标记：" + row["文件"], not re.search(r"^(?:<{7}|={7}|>{7})(?:\s|$)", text, re.M), "只查Git冲突标记")
    for match in re.finditer(r"!?\[[^\]\n]*\]\(([^\n]+?)\)", text):
        target = match.group(1).strip()
        target = target[1:target.index(">")] if target.startswith("<") and ">" in target else target.split(' "')[0]
        if re.match(r"^[a-zA-Z]+://", target) or target.startswith("#"):
            continue
        target = urllib.parse.unquote(target.split("#")[0])
        links += 1
        if target and not (path.parent / target).exists():
            missing.append([row["文件"], target])
    for target in re.findall(r"!?\[\[([^\]]+)\]\]", text):
        target = target.split("|")[0].split("#")[0]
        if not target:
            continue
        links += 1
        if not (path.parent / target).exists() and not any(BOOK.rglob(Path(target).name)) and not any(BOOK.rglob(Path(target).name + ".md")):
            missing.append([row["文件"], target])
check("本地链接和图片目标", not missing, {"检查数": links, "缺失": missing})

index = (BOOK / "01·图册" / "地名与图号索引.md").read_text(encoding="utf-8")
rows = {}
for line in index.splitlines():
    cells = [cell.strip() for cell in line.strip("|").split("|")]
    if cells and re.fullmatch(r"[LHS]\d{2}(?:-\d{2})?", cells[0]):
        rows[cells[0]] = cells
for land, counts, population in [("衡岑", (7, 37), 3560), ("乌弥尔", (12, 123), 6400), ("萨阑", (10, 111), 3840)]:
    data = json.loads((SOURCE / (land + "·图层数据.json")).read_text(encoding="utf-8"))
    check(land + "国家及二级区数量", (len(data["countries"]), len(data["districts"])) == counts, counts)
    population_errors = []
    index_errors = []
    for country in data["countries"]:
        total = sum(d["population_wan"] for d in data["districts"] if d["country_code"] == country["code"])
        if abs(total - country["population_wan"]) > 0.001:
            population_errors.append([country["name"], total, country["population_wan"]])
    check(land + "人口汇总", not population_errors and sum(c["population_wan"] for c in data["countries"]) == population, population_errors)
    for item in data["countries"] + data["districts"]:
        row = rows.get(item["code"])
        if not row or row[1] != item["name"] or row[3] != item.get("seat", item.get("capital")):
            index_errors.append(item["code"])
    check(land + "图层和索引的现名治所", not index_errors, index_errors)

relative = "01·图册/源文件/名称注册表.json"
previous = json.loads(subprocess.check_output(["git", "-C", str(BOOK), "show", baseline["基线提交"] + ":" + relative]).decode("utf-8"))
current = json.loads((BOOK / relative).read_text(encoding="utf-8"))
identity_errors = []
fields = Counter()
for old, new in zip(previous["entries"], current["entries"]):
    if any(old.get(key) != new.get(key) for key in ["id", "old", "new", "kind"]):
        identity_errors.append(new["id"])
    for key in set(old) | set(new):
        if old.get(key) != new.get(key):
            fields[key] += 1
check("注册表未意外改名或改类", len(previous["entries"]) == len(current["entries"]) and not identity_errors, identity_errors)
check("注册表改动字段限于已审地域与释义", set(fields) <= {"country", "continent", "history"}, dict(fields))
report = {"说明": "机械检查不能代替语义审校；本轮无增字指标", "正式基线文件数": len(baseline["文件"]), "当前汉字": characters, "较基线净变化": characters - baseline["基线汉字"], "通过": all(c["通过"] for c in checks), "检查": checks}
(WORK / "机械核验.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({key: value for key, value in report.items() if key != "检查"}, ensure_ascii=False))
for item in checks:
    if not item["通过"]:
        print(json.dumps(item, ensure_ascii=False))
raise SystemExit(0 if report["通过"] else 1)
