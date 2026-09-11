"""Isolated report contract tests. Not a full runtime/launcher integration test.

The delivery omits src/evidence; compile only the standalone report function
so its output can be checked without pretending to boot the incomplete app.
"""
import ast
import hashlib
import json
import time
from pathlib import Path
from types import SimpleNamespace

from src.observability.true_liveness import TrueLivenessTracker
from src.observability.runtime_trace import BoundedRuntimeTrace


def report_function():
    path=Path(__file__).resolve().parents[1]/'scripts/run_multicamera.py'
    tree=ast.parse(path.read_text())
    node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='_generate_physical_report')
    ns={'Path':Path,'json':json}
    exec(compile(ast.Module(body=[node],type_ignores=[]),str(path),'exec'),ns)
    return ns['_generate_physical_report']


import tempfile


def test_report_keeps_unknowns_and_uses_separate_full_hash_manifest():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        runtime = SimpleNamespace(
            evidence_root=tmp_path, _run_id='RUN-TEST', _pid=123, _camera_ids=['cam'], _entries=[],
            _true_liveness=TrueLivenessTracker(['cam']),
            _health=SimpleNamespace(snapshot=lambda **kwargs: SimpleNamespace(camera_health=[])),
            _trace=BoundedRuntimeTrace(['cam']),
            _telemetry=SimpleNamespace(snapshot=lambda: [], marker_rows=lambda: {}))
        forensics = SimpleNamespace(_started=time.time(), registry={'why_process_exited': 'NORMAL_UI_CLOSE'})
        report_function()(runtime, forensics)
        data = json.loads((tmp_path / 'physical_runtime_report.json').read_text())
        assert data['per_camera'][0]['NO_FIRST_FRAME'] is True
        assert data['per_camera'][0]['LAST_FRAME_TS'] is None
        assert data['freeze_total'] is None
        assert data['orphan_decoders'] is None
        assert data['cameras_available_start'] is None
        assert data['technical_gate'] == 'NOT_CERTIFIED'
        manifest = json.loads((tmp_path / 'sha256_manifest.json').read_text())
        assert manifest['physical_runtime_report.json'] == hashlib.sha256((tmp_path / 'physical_runtime_report.json').read_bytes()).hexdigest()
