"""Recompute the chip-area/energy table from frozen reports and board latencies."""
from pathlib import Path
import hashlib,json,math,re
from paper_app_names import app_label

ROOT=Path(__file__).resolve().parents[1]
FOLDER=ROOT/'data/chip_area_energy_20261103'
inputs=json.loads((FOLDER/'inputs.json').read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for row in inputs['provenance']:
    assert sha(ROOT/row['file'])==row['sha256'],row['file']
data=json.loads((ROOT/'data/experiment_results.json').read_text())
assert hashlib.sha256(json.dumps(data,sort_keys=True,separators=(',',':')).encode()).hexdigest()==inputs['experiment_results_semantic_sha256']
configs={x['application']:x for x in data['selected_soc_configs']}
rows=[]
for source in inputs['applications']:
    app=source['application'];latency=data['board_latencies'][app]
    totals=re.findall(r'\b\w+_TIME\s+[^\r\n]*?mode=(cpu|hw) stage=total cycles_lo=(0x[0-9a-f]+) cycles_hi=(0x[0-9a-f]+) ms=([0-9.]+) freq_khz=(\d+)',(ROOT/latency['source']).read_text(encoding='utf-8-sig'))
    checked={}
    for mode,lo,hi,ms,freq in totals:
        cycles=int(hi,16)*2**32+int(lo,16)
        assert 0<=cycles/int(freq)-float(ms)<.00101
        checked[mode]=float(ms)
    assert checked==dict(cpu=latency['cpu_ms'],hw=latency['accelerated_ms'])
    powers={}
    for mode in ['cpu','accelerated']:
        report=(ROOT/source[mode+'_power_report']).read_text()
        assert re.search(r'Design State\s*:\s*routed',report)
        powers[mode]=float(re.search(r'\|\s*Total On-Chip Power \(W\)\s*\|\s*([0-9.]+)',report)[1])
    baseline=json.loads((ROOT/source['cpu_fpga_validation']).read_text())
    assert baseline['success'] and baseline['accelerators']==[] and baseline['clock_mhz']==75 and baseline['routed_timing_met']
    assert powers['cpu']==baseline['estimated_power_w']
    assert sha(ROOT/source['cpu_power_report'])==baseline['power_report_sha256']
    assert source['params']==configs[app]['params']
    cpu_area=None
    if source.get('cpu_area_summary'):
        area_path=ROOT/source['cpu_area_summary'];a=json.loads(area_path.read_text())
        receipt=json.loads((ROOT/source['cpu_area_validation']).read_text())
        assert receipt['success'] and receipt['area_summary_sha256']==sha(area_path)
        assert a['success'] and a['accelerators']==[] and a['params']==source['params']
        assert a['process_nm']==90 and a['excluded_application_ram_bytes']==1024000 and a['unmapped_cells']==0
        assert math.isclose(a['total_area_mm2'],a['sram_macro_area_mm2']+a['standard_cell_area_mm2'])
        cpu_area=a['total_area_mm2']/4
    if app=='wami':
        archive=json.loads((ROOT/source['accelerated_area_summary']).read_text())
        a=next(x for x in archive['rows'] if x['point']=='p030')
        assert a['status']=='completed_and_validated' and a['params']==source['params']
        accelerated_area=a['native90_mm2']/4
    else:
        a=json.loads((ROOT/source['accelerated_area_summary']).read_text())
        assert a['success'] and a['process_nm']==90
        accelerated_area=a['total_area_mm2']/4
    assert math.isclose(accelerated_area,configs[app]['synthesis_equivalent_mm2'],rel_tol=1e-9)
    cpu_s=latency['cpu_ms']/1000;acc_s=latency['accelerated_ms']/1000
    ratio=powers['accelerated']*acc_s**2/(powers['cpu']*cpu_s**2)
    assert math.isclose(ratio,powers['accelerated']/powers['cpu']/latency['adjusted_speedup']**2)
    rows.append(dict(application=app,display_name=app_label(app),cpu_power_w=powers['cpu'],accelerated_power_w=powers['accelerated'],cpu_latency_ms=latency['cpu_ms'],accelerated_latency_ms=latency['accelerated_ms'],cpu_edp_j_s=powers['cpu']*cpu_s**2,accelerated_edp_j_s=powers['accelerated']*acc_s**2,cpu_normalized_edp=1.,accelerated_normalized_edp=ratio,edp_reduction_percent=(1-ratio)*100,cpu_area_45nm_equivalent_mm2=cpu_area,accelerated_area_45nm_equivalent_mm2=accelerated_area))
result=dict(rows=rows,power_basis='Post-route vectorless Vivado total on-chip estimate including PS and static power; CPU power is from actual zero-accelerator hardware.',latency_basis='Reported paired board application latencies in data/experiment_results.json; the new zero-accelerator bitstreams have not been separately board timed.',edp_definition='power_w * runtime_s ** 2; normalized independently to each CPU baseline=1; lower is better',area_basis='90nm mapped standard cells and physical SRAM macros divided by4; only1000KiB application RAM excluded; missing CPU areas remain null until final validation',area_complete=all(x['cpu_area_45nm_equivalent_mm2'] is not None for x in rows))
(FOLDER/'results.json').write_bytes((json.dumps(result,indent=2)+'\n').encode())
tex=[r'\begin{table}[t]',r'\centering',r'\caption{Normalized EDP and synthesis areas of CPU-only and CPU--accelerator systems. Areas are expressed in 45-nm-equivalent mm$^2$.}',r'\label{tab:chip_area_energy}',r'\footnotesize',r'\renewcommand{\arraystretch}{1.15}',r'\setlength{\tabcolsep}{3pt}',r'\begin{tabular*}{\columnwidth}{@{\extracolsep{\fill}}lrrrr@{}}',r'\toprule',r' & \multicolumn{2}{c}{\textbf{Norm. EDP}} & \multicolumn{2}{c}{\textbf{Synth. area}} \\',r'\cmidrule(lr){2-3}\cmidrule(lr){4-5}',r'\textbf{Application} & \textbf{CPU} & \textbf{Accel.} & \textbf{CPU} & \textbf{Accel.} \\',r'\midrule']
for row in rows:
    area='---' if row['cpu_area_45nm_equivalent_mm2'] is None else f"{row['cpu_area_45nm_equivalent_mm2']:.3f}"
    name=row['display_name'].replace('_',r'\_')
    tex.append(f"{name} & 1.0000 & {row['accelerated_normalized_edp']:.4f} & {area} & {row['accelerated_area_45nm_equivalent_mm2']:.3f}"+r' \\')
tex += [r'\bottomrule',r'\end{tabular*}',r'\par\vspace{4pt}',r'\parbox{\columnwidth}{\scriptsize CPU denotes hardware without accelerator tiles; Accel. denotes the selected CPU--accelerator system. EDP is normalized to each CPU-only baseline; lower is better.'+(' Dashes indicate pending area validation.' if not result['area_complete'] else '')+'}',r'\end{table}']
(ROOT/'data/generated/chip_area_energy.tex').write_text('\n'.join(tex)+'\n')
print(json.dumps(dict(success=True,applications=len(rows),area_complete=result['area_complete'],rows=rows),indent=2))
