import json
import math
from pathlib import Path

def test_c2_outliers_reconciliation():
    raw_path = Path("evidence/c2_operational_baseline/c2_metrics_raw.json")
    with open(raw_path, 'r') as f:
        raw = json.load(f)
    
    cameras = raw['cameras']
    p95_values = []
    for cid, cdata in cameras.items():
        if 'frame_age_ms' in cdata.get('metrics', {}):
            p95 = cdata['metrics']['frame_age_ms'].get('p95_ms')
            if p95 is not None:
                p95_values.append((cid, p95))
    
    p95_values.sort(key=lambda x: x[1])
    p95_only = [v[1] for v in p95_values]
    
    def percentile(N, percent, key=lambda x:x):
        if not N:
            return None
        k = (len(N)-1) * percent
        f = math.floor(k)
        c = math.ceil(k)
        if f == c:
            return key(N[int(k)])
        d0 = key(N[int(f)]) * (c-k)
        d1 = key(N[int(c)]) * (k-f)
        return d0+d1

    q1 = percentile(p95_only, 0.25)
    q3 = percentile(p95_only, 0.75)
    iqr = q3 - q1
    upper_fence = q3 + 1.5 * iqr
    
    outliers = []
    for cid, p95 in p95_values:
        if p95 > upper_fence:
            outliers.append(cid)
    
    # Based on the formula and the snapshot, outliers should be cam_09, cam_12, cam_14
    assert sorted(outliers) == sorted(['cam_09', 'cam_12', 'cam_14'])
