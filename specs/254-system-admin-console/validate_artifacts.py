#!/usr/bin/env python3
"""Проверка целостности документов Feature 254; не проверка реализации."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent
errors: list[str] = []
def require(condition: bool, message: str) -> None:
    if not condition:
        errors.append(message)

spec = (ROOT / 'spec.md').read_text()
tasks = (ROOT / 'tasks.md').read_text()
acceptance = (ROOT / 'acceptance.md').read_text()
fr = re.findall(r'\*\*(FR-\d{3})\.', spec)
sc = re.findall(r'\*\*(SC-\d{3})\.', spec)
ac = re.findall(r'^### (AC-\d{3})\.', acceptance, re.M)
task_ids = re.findall(r'^- \[[ xX]\] (T\d{3})\b', tasks, re.M)
for name, items, count in [('FR', fr, 90), ('SC', sc, 12), ('AC', ac, 42), ('tasks', task_ids, 39)]:
    require(len(items) == len(set(items)) == count, f'{name}: неверное число/дубли {len(items)}')
require(set(fr) <= set(re.findall(r'FR-\d{3}', acceptance)), 'FR без AC')
require(set(sc) <= set(re.findall(r'SC-\d{3}', acceptance)), 'SC без AC')
coverage = dict(re.findall(r'^\| (FR-\d{3}) \| ([^|]+) \|', tasks, re.M))
for item in fr:
    mapped = set(re.findall(r'T\d{3}', coverage.get(item, '')))
    require(bool(mapped) and mapped <= set(task_ids), f'{item}: отсутствует корректный владелец задач')
blocks = re.split(r'^- \[[ xX]\] (T\d{3})\b', tasks, flags=re.M)
graph: dict[str, list[str]] = {}
for i in range(1, len(blocks), 2):
    tid, block = blocks[i:i + 2]
    dep = re.search(r'Зависимости: (.*?)\.', block)
    graph[tid] = re.findall(r'T\d{3}', dep.group(1)) if dep else []
    require(all(x in task_ids and x != tid for x in graph[tid]), f'{tid}: неизвестная/self зависимость')
    for aid in re.findall(r'AC-\d{3}', block.split('\n## ')[0]):
        require(aid in ac, f'{tid}: неизвестный {aid}')
visited: set[str] = set()
active: set[str] = set()
def visit(tid: str) -> None:
    if tid in active:
        errors.append(f'Цикл зависимостей: {tid}')
        return
    if tid in visited:
        return
    active.add(tid)
    for child in graph.get(tid, []):
        visit(child)
    active.remove(tid)
    visited.add(tid)
for tid in graph:
    visit(tid)
for file in ROOT.rglob('*.md'):
    text = file.read_text()
    require(not re.search(r'TODO|TBD|NEEDS CLARIFICATION|\[FEATURE\]|\[DATE\]', text), f'{file.name}: незаполненный шаблон')
    for target in re.findall(r'\]\(([^)]+)\)', text):
        if target.startswith(('https:', 'http:', '#')):
            continue
        require((file.parent / target.split('#')[0]).exists(), f'{file.name}: битая ссылка {target}')
    for lineno, line in enumerate(text.splitlines(), 1):
        require(not line.endswith((' ', '\t')) or line.endswith('  '), f'{file.name}:{lineno}: случайный пробел')
issues = (ROOT / 'issues.md').read_text()
issue_rows = re.findall(r'^\| (T\d{3}) \| \[#(\d+)\]', issues, re.M)
require({x for x, _ in issue_rows} == set(task_ids), 'GitHub: неполное покрытие tasks')
require(len(issue_rows) == len({x for _, x in issue_rows}) == len(task_ids), 'GitHub: дубли ownership')
if errors:
    raise SystemExit('\n'.join(errors))
print(f'OK: {len(fr)} FR, {len(sc)} SC, {len(ac)} AC, {len(task_ids)} tasks; links, dependency DAG, issue ownership')
print('Проверены документы. Runtime tests/release не выполнялись этим скриптом.')
