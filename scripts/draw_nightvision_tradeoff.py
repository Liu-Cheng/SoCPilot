"""Draw Nightvision latency and selected-area budget sweeps with PGFPlots (requires pdflatex).
Run: python scripts/draw_nightvision_tradeoff.py
The CSV retains all 3--16 mm2 points; the figure displays 3--11 mm2.
"""
from pathlib import Path
import csv
import subprocess

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / 'scripts/nightvision_tradeoff_template.tex'
rows = list(csv.DictReader((ROOT / 'data/nightvision_area_sweep.csv').open(encoding='utf-8')))
rows = [r for r in rows if 3 <= int(r['area_limit_mm2']) <= 11]
assert [int(r['area_limit_mm2']) for r in rows] == list(range(3, 12))
def coords(selected, field='time_ms'):
    return ' '.join('(%s,%.9f)' % (r['area_limit_mm2'], float(r[field])) for r in selected)
text = TEMPLATE.read_text(encoding='utf-8')
for key, selected in [('ALL', rows), ('ZOOM', rows[1:]),
                      ('IBEX', [r for r in rows if r['cpu'] == 'ibex']),
                      ('LEON', [r for r in rows if r['cpu'] == 'leon3']),
                      ('ARIANE', [r for r in rows if r['cpu'] == 'ariane'])]:
    text = text.replace('@' + key + '@', coords(selected))
    if key != 'ZOOM':
        text = text.replace('@AREA_' + key + '@', coords(selected, 'total_area_mm2'))
# Annotate all nine values from the CSV, with 4--11 shown in the inset.
main_label = (
    r'\node[anchor=west,font=\fontsize{8}{9}\selectfont,text=ibex]'
    r' at (axis cs:3.25,1155) {%.2f};' % float(rows[0]['time_ms']))
labels = []
for row in rows[1:]:
    budget = int(row['area_limit_mm2'])
    value = float(row['time_ms'])
    below = budget in (8, 10)
    anchor = 'north' if below else 'south'
    shift = '-7pt' if below else '5pt'
    color = 'leon' if row['cpu'] == 'leon3' else 'ariane'
    labels.append(
        r'\node[anchor=%s,yshift=%s,font=\fontsize{7}{8}\selectfont,text=%s]'
        r' at (axis cs:%d,%.9f) {%.2f};' % (anchor, shift, color, budget, value, value))
text = text.replace('@MAIN_LABELS@', main_label)
text = text.replace('@ZOOM_LABELS@', '\n'.join(labels))
# Place area labels away from the budget line and keep edge labels inside the axes.
area_labels = []
for row in rows:
    budget = int(row['area_limit_mm2'])
    value = float(row['total_area_mm2'])
    assert 0 < value <= budget, 'Selected design exceeds its area budget'
    color = {'ibex': 'ibex', 'leon3': 'leon', 'ariane': 'ariane'}[row['cpu']]
    anchor = 'west' if budget == 3 else 'north east' if budget == 11 else 'north'
    shift = '0pt' if budget == 3 else '-6pt'
    xshift = '5pt' if budget == 3 else '0pt'
    area_labels.append(
        r'\node[anchor=%s,yshift=%s,font=\fontsize{7}{8}\selectfont,text=%s,'
        r'xshift=%s,fill=white,inner sep=1pt] at (axis cs:%d,%.9f) {%.3f};'
        % (anchor, shift, color, xshift, budget, value, value))
text = text.replace('@AREA_LABELS@', '\n'.join(area_labels))
assert '@' not in text, 'Unresolved plot template token'

build = ROOT / 'build/nightvision-figure'
build.mkdir(parents=True, exist_ok=True)
source = build / 'nightvision-area-latency.tex'
source.write_text(text, encoding='utf-8')
log = build / 'compile.stdout'
with log.open('w', encoding='utf-8') as stream:
    subprocess.run(['pdflatex', '-interaction=nonstopmode', '-halt-on-error',
                    '-output-directory', str(build), str(source)],
                   cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT, check=True)
output = ROOT / 'pic/nightvision-area-latency.pdf'
output.write_bytes((build / 'nightvision-area-latency.pdf').read_bytes())
print(output)
