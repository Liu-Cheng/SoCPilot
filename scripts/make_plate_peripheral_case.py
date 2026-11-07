"""Generate the active paper's peripheral-only plate case from audited data.

Refresh with --manifest <new soc_manifest.json>, or regenerate the listing from
the committed snapshot without access to soc_script. The historical five-case
preview generator and its eight-IP source remain unchanged for provenance.
No LLM request or downstream SoC flow is invoked.
"""
import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / 'data/plate_peripheral_ip_case.json'
LISTING = ROOT / 'previews/ip-selection/plate_peripherals.txt'
EXPECTED = {
    'camera_pixels': ('mipi_csi2', 'needs_evidence'),
    'camera_control': ('camera_i2c_ctrl', 'catalog_match'),
    'host_records': ('ethernet', 'catalog_match'),
}


def check(case):
    if case['application'] != 'plate_new' or case['matching_scope'] != 'peripherals':
        raise ValueError('Expected the plate_new peripheral-only case')
    if case['status'] != 'needs_review':
        raise ValueError('Case narrative must be reviewed when matching status changes')
    services = {item['service_id']: item for item in case['service_results']}
    if set(services) != set(EXPECTED):
        raise ValueError('Three peripheral requests required; no internal IPs')
    for key, (ip_id, status) in EXPECTED.items():
        item = services[key]
        if (item['selected_ip_id'], item['status']) != (ip_id, status):
            raise ValueError('Update the manuscript for changed candidate/status: ' + key)
    camera = services['camera_pixels']
    if set(camera['unknown_fields']) != {'min_channels', 'frame_sync'}:
        raise ValueError('Update the camera evidence-gap narrative')
    if sorted(case['recommended_ids']) != sorted(value[0] for value in EXPECTED.values()):
        raise ValueError('Unexpected exported recommendations')
    required = {item['id']: item['hard'] for item in case['structured_requirement']['platform_services']}
    if required != {
        'camera_pixels': {'protocol': 'csi2', 'min_channels': 1, 'frame_sync': True},
        'camera_control': {'protocol': 'i2c', 'role': 'controller'},
        'host_records': {'protocol': 'ethernet'},
    }:
        raise ValueError('Update the listing for changed interface requirements')
    if case['interpretation_provenance']['llm_called'] or case['total_soc_area_mm2'] is not None:
        raise ValueError('This case must not claim measured LLM interpretation or area')
    if case['auto_deployable_ip_ids'] or case['physical_feasibility'] != 'not_established':
        raise ValueError('Deployment/feasibility narrative must be reviewed')


def extract(path):
    raw = path.read_bytes()
    manifest = json.loads(raw)
    rows = []
    for item in manifest['service_results']:
        chosen = next(candidate for candidate in item['candidates']
                      if candidate['ip_id'] == item['selected_ip_id'])
        rows.append({key: item[key] for key in ('service_id', 'service', 'selected_ip_id', 'status')})
        rows[-1].update(unknown_fields=chosen['unknown_fields'], checks=chosen['checks'],
                        provenance=chosen['provenance'])
    return {
        'application': manifest['application'],
        'paper_application': 'plate_roi',
        'matching_scope': manifest['matching_scope'],
        'status': manifest['status'],
        'source': {'manifest': str(path.resolve()), 'manifest_sha256': hashlib.sha256(raw).hexdigest(),
                   'library_snapshot_sha256': manifest['library_snapshot_sha256'],
                   'generated_at': manifest['generated_at'],
                   'note': 'Display summaries are abridged, not a verbatim LLM transcript.'},
        'structured_requirement': manifest['structured_requirement'],
        'service_results': rows,
        'recommended_ids': [item['id'] for item in manifest['selected_reusable_ips']],
        'interpretation_provenance': manifest['interpretation_provenance'],
        'total_soc_area_mm2': manifest['area_accounting']['total_soc_area_mm2'],
        'physical_feasibility': manifest['feasibility']['status'],
        'auto_deployable_ip_ids': manifest['deployment']['auto_deployable_ip_ids'],
        'recommendation_only_ip_ids': manifest['deployment']['recommendation_only_ip_ids'],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, help='Explicitly refresh audited snapshot from a new run')
    args = parser.parse_args()
    case = extract(args.manifest) if args.manifest else json.loads(SNAPSHOT.read_text(encoding='utf-8'))
    check(case)
    lines = [
        '# 1. Deployment description (abridged)',
        '"Parking-entry plate-region extraction:',
        ' one CSI-2 camera; I2C sensor setup;',
        ' Ethernet records to a parking host."',
        'scope: external peripherals only',
        '',
        '# 2. Structured interface requirements',
        'pixels: CSI-2; channels>=1; frame_sync=true',
        'sensor setup: I2C controller',
        'host link: Ethernet',
        '',
        '# 3. Library matching and capability checks',
        'camera_pixels  -> mipi_csi2',
        '  protocol: pass; channels/sync: unknown',
        '  result: needs_evidence',
        'camera_control -> camera_i2c_ctrl',
        '  result: catalog_match',
        'host_records   -> ethernet',
        '  result: catalog_match',
        '',
        '# 4. Exported recommendations (abridged)',
        'selected: [mipi_csi2, camera_i2c_ctrl,',
        '           ethernet]',
        'status: needs_review',
        'deployment: recommendation_only',
    ]
    if max(map(len, lines)) > 48:
        raise ValueError('Listing exceeds audited single-column width')
    if args.manifest:
        SNAPSHOT.write_text(json.dumps(case, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    LISTING.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print('Audited three recommendations, two catalog matches, one evidence gap.')
    print(LISTING)


if __name__ == '__main__':
    main()
