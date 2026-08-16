# -*- coding: utf-8 -*-
"""LOOP-0018O — Harness de validacion fisica multicamara (4 camaras reales).

Herramienta de MEDICION/CERTIFICACION exclusivamente. NO modifica producto.
Reutiliza el SourceManager certificado del BASE (src.capture.source_manager).

Flujo:
  FASE 0  PRECHECK (proceso, dumps baseline)
  FASE 1  Deteccion pasiva de canales (probe corto, 1 frame) -> canales accesibles
  FASE 2  Seleccion de 4 camaras reales (obligatorio incluir CAM07)
  FASE 3  SourceManager: registro + start simultaneo
  FASE 4  Simultaneidad (4 health healthy + frames)
  FASE 5  Estabilidad (ventana de observacion, sin stall/reconnect/crash)
  FASE 6  Aislamiento: stop/restart de UNA camara, las otras intactas
  FASE 7  Salud individual por camara
  FASE 8  Shutdown limpio (close_all, sin huerfanos)
  FASE 9  Evidencia + certificacion

Seguridad:
  - password solo en memoria (getpass). NUNCA se imprime ni persiste.
  - URLs siempre redactadas en salida/evidencia.
  - Sin dependencias nuevas (stdlib + cv2 ya presente + ctypes).
"""

import argparse
import csv
import ctypes
import getpass
import json
import os
import sys
import threading
import time
from pathlib import Path

BASE_ROOT = Path(r"C:\Users\ASUS Zenbook\Documents\TukeVision\TukeVision")
sys.path.insert(0, str(BASE_ROOT))

import cv2  # noqa: E402

from src.capture.source_manager import (  # noqa: E402
    CameraDescriptor,
    SourceManager,
    SourceManagerError,
)
from src.capture.rtsp_url import build_rtsp_url  # noqa: E402
from src.observability.logging_setup import redact_rtsp_url  # noqa: E402

HOST = "rtsp://186.103.177.83:554/cam/realmonitor"
USER = "admin"
DETECT_SUBTYPE = 1
VALIDATE_CAM07_SUBTYPE = 0  # referencia certificada LOOP-0018L
EVID = BASE_ROOT / "evidence" / "loop_0018o"
EVID.mkdir(parents=True, exist_ok=True)

# ----------------------------------------------------------------------------
# Medición de proceso sin dependencias (ctypes, stdlib)
# ----------------------------------------------------------------------------

_PSAPI = ctypes.windll.psapi
_KERNEL = ctypes.windll.kernel32


def process_working_set_mb(pid: int) -> float:
    class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
        _fields_ = [
            ("cb", ctypes.c_ulong),
            ("PageFaultCount", ctypes.c_ulong),
            ("PeakWorkingSetSize", ctypes.c_size_t),
            ("WorkingSetSize", ctypes.c_size_t),
            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
            ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
            ("PagefileUsage", ctypes.c_size_t),
            ("PeakPagefileUsage", ctypes.c_size_t),
        ]

    handle = _KERNEL.OpenProcess(0x1000 | 0x0008, False, pid)  # QUERY + READ
    if not handle:
        return 0.0
    try:
        ctr = PROCESS_MEMORY_COUNTERS()
        ctr.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS)
        if _PSAPI.GetProcessMemoryInfo(handle, ctypes.byref(ctr), ctr.cb):
            return ctr.WorkingSetSize / (1024 * 1024)
        return 0.0
    finally:
        _KERNEL.CloseHandle(handle)


def process_handle_count(pid: int) -> int:
    handle = _KERNEL.OpenProcess(0x1000, False, pid)
    if not handle:
        return -1
    try:
        count = ctypes.c_ulong(0)
        _KERNEL.GetProcessHandleCount(handle, ctypes.byref(count))
        return count.value
    finally:
        _KERNEL.CloseHandle(handle)


def tcp554_count(pid: int) -> int:
    import subprocess

    out = subprocess.run(
        ["netstat", "-ano"], capture_output=True, text=True, timeout=10
    ).stdout
    return sum(
        1
        for line in out.splitlines()
        if "ESTABLISHED" in line and ":554" in line and str(pid) in line
    )


# ----------------------------------------------------------------------------
# FASE 0 / PRECHECK
# ----------------------------------------------------------------------------


def precheck() -> dict:
    dump_dir = Path(os.environ.get("LOCALAPPDATA", "")) / "CrashDumps"
    baseline = (
        [p.name for p in dump_dir.glob("*.dmp")] if dump_dir.exists() else []
    )
    py_procs = []
    import subprocess

    out = subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         "Get-Process python* -ErrorAction SilentlyContinue | "
         "ForEach-Object { \"$($_.Id)\" }"],
        capture_output=True, text=True, timeout=15,
    ).stdout
    for line in out.splitlines():
        line = line.strip()
        if line.isdigit():
            py_procs.append(int(line))
    return {
        "base_head": _git_short(),
        "branch": _git_branch(),
        "dumps_baseline": baseline,
        "python_procs_running": py_procs,
        "host": HOST,
    }


def _git_short() -> str:
    import subprocess

    out = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        cwd=BASE_ROOT, capture_output=True, text=True, timeout=10,
    ).stdout.strip()
    return out


def _git_branch() -> str:
    import subprocess

    out = subprocess.run(
        ["git", "branch", "--show-current"],
        cwd=BASE_ROOT, capture_output=True, text=True, timeout=10,
    ).stdout.strip()
    return out


# ----------------------------------------------------------------------------
# FASE 1 / Deteccion pasiva de canales
# ----------------------------------------------------------------------------


def probe_channel(password: str, channel: int, subtype: int,
                  open_ms: int = 5000) -> dict:
    """Probe pasivo: abre, lee 1 frame, cierra. Redactado en la salida."""
    from src.capture.live_sources import RTSPSource

    url = build_rtsp_url(HOST, USER, password, channel=channel, subtype=subtype)
    source = RTSPSource(
        rtsp_url=url,
        max_width=640,
        max_reconnect_attempts=0,
        rtsp_open_timeout_ms=open_ms,
        frame_stall_timeout_s=3.0,
    )
    result = {"channel": channel, "subtype": subtype, "ok": False,
              "resolution": "", "fps": 0.0}
    try:
        meta = source.open()
        frames = 0
        for _ in source.frames():
            frames += 1
            if frames >= 1:
                break
        if frames >= 1:
            result["ok"] = True
            result["resolution"] = f"{meta.width}x{meta.height}"
            result["fps"] = round(float(meta.fps or 0.0), 2)
    except Exception as exc:  # probe controlado, sin propagar
        result["error"] = type(exc).__name__
    finally:
        try:
            source.close()
        except Exception:
            pass
    return result


def detect_channels(password: str) -> list:
    detected = []
    failures = []
    for ch in range(1, 17):
        r = probe_channel(password, ch, DETECT_SUBTYPE)
        if r["ok"]:
            detected.append(r)
        else:
            failures.append({"channel": ch, "error": r.get("error", "")})
    return detected, failures


# ----------------------------------------------------------------------------
# FASE 3-8 / Validación SourceManager
# ----------------------------------------------------------------------------


def health_all(mgr, cam_ids) -> dict:
    out = {}
    for cid in cam_ids:
        try:
            h = mgr.health(cid)
            out[cid] = {
                "state": h.state,
                "healthy": h.healthy,
                "fps": h.fps,
                "resolution": h.resolution,
                "last_frame_age_ms": h.last_valid_frame_age_ms,
                "stall_count": h.stall_count,
                "readable_frames": h.readable_frames,
                "queue_depth": h.queue_depth,
                "last_error": h.last_error,
            }
        except SourceManagerError as e:
            out[cid] = {"error": str(e)}
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="LOOP-0018O validation harness")
    parser.add_argument("--stability-sec", type=int, default=300)
    parser.add_argument("--sample-sec", type=int, default=5)
    parser.add_argument("--cams", type=str, default="",
                        help="canales a validar separados por coma (debe incluir 7)")
    args = parser.parse_args()

    print("=" * 70)
    print("LOOP-0018O — VALIDACION FISICA MULTICAMARA (4 camaras reales)")
    print("=" * 70)

    # Password (getpass) — solo en memoria
    password = getpass.getpass("Contrasena RTSP del DVR (no se muestra, no se guarda): ")
    if not password:
        print("ERROR: contrasena vacia")
        return 1

    pc = precheck()
    print(f"\n[FASE 0] PRECHECK base={pc['base_head']} branch={pc['branch']} "
          f"python_procs={len(pc['python_procs_running'])} "
          f"dumps_baseline={len(pc['dumps_baseline'])}")
    _write("precheck.json", pc)

    # FASE 1: detección pasiva
    print("\n[FASE 1] Deteccion pasiva de canales 1-16 (subtype=1, 1 frame)...")
    detected, failures = detect_channels(password)
    print(f"CANALES_ACCESIBLES={[d['channel'] for d in detected]}")
    _write("channel_detection.json",
           {"detected": detected, "failures": failures})

    # FASE 2: selección de 4 cámaras reales
    want = [int(c) for c in args.cams.split(",") if c.strip()] if args.cams else None
    if want is None:
        prefer = [7, 1, 5, 3, 9, 11, 13, 15, 2, 4, 6, 8, 10, 12, 14, 16]
        accessible = [d["channel"] for d in detected]
        order = [c for c in prefer if c in accessible]
        want = order[:4]
    if 7 not in want:
        want = [7] + [c for c in want if c != 7]
    if len(want) < 4:
        print("\n[FASE 2] STOP: no se pueden confirmar 4 camaras accesibles.")
        print(f"Verificadas: {[d['channel'] for d in detected]}")
        _write("selection.json",
               {"verdict": "INSUFFICIENT_CAMERAS",
                "confirmed": [d['channel'] for d in detected]})
        return 3

    sel = {"camera_channels": want, "cam07_subtype": VALIDATE_CAM07_SUBTYPE,
           "others_subtype": DETECT_SUBTYPE}
    print(f"\n[FASE 2] SELECCION={want} (CAM07 subtype=0 referencia; resto subtype=1)")
    _write("selection.json", sel)

    # FASE 3: registro + start
    mgr = SourceManager()
    cam_ids = []
    for ch in want:
        cid = f"CAM-{ch:02d}"
        subtype = VALIDATE_CAM07_SUBTYPE if ch == 7 else DETECT_SUBTYPE
        mgr.register_source(CameraDescriptor(
            camera_id=cid,
            host=HOST,
            channel=ch,
            subtype=subtype,
            username=USER,
            password=password,
            max_width=640,
            rtsp_open_timeout_ms=8000,
            frame_stall_timeout_s=10.0,
        ))
        cam_ids.append(cid)

    print("\n[FASE 3] START simultaneo de 4 camaras...")
    started = []
    for cid in cam_ids:
        try:
            mgr.start(cid)
            started.append(cid)
        except SourceManagerError as e:
            print(f"START_FAILED {cid}: {e}")
    _write("start_events.json", {"started": started, "requested": cam_ids})

    # FASE 4: simultaneidad
    print("\n[FASE 4] Esperando simultaneidad (todas healthy + frames)...")
    deadline = time.monotonic() + 60
    sim_all = False
    last = None
    while time.monotonic() < deadline:
        last = health_all(mgr, cam_ids)
        if all(h.get("healthy") and h.get("readable_frames", 0) > 0
               for h in last.values()):
            sim_all = True
            break
        time.sleep(1)
    _write("simultaneity.json", {"all_healthy_with_frames": sim_all,
                                 "health": last})
    if not sim_all:
        print("\n[FASE 4] STOP: simultaneidad no confirmada.")
        print(json.dumps(last, indent=2))
        mgr.close_all()
        return 4

    # FASE 5: estabilidad
    print(f"\n[FASE 5] Observacion de estabilidad {args.stability_sec}s "
          f"(sample {args.sample_sec}s)...")
    pid = os.getpid()
    rows = []
    start = time.monotonic()
    events = []
    while time.monotonic() - start < args.stability_sec:
        h = health_all(mgr, cam_ids)
        all_ok = all(x.get("healthy") and x.get("stall_count", 0) == 0
                     and x.get("state") in ("OPEN", "READING")
                     for x in h.values())
        rows.append({
            "elapsed_s": round(time.monotonic() - start, 1),
            "pid": pid,
            "ram_mb": round(process_working_set_mb(pid), 1),
            "handles": process_handle_count(pid),
            "threads": threading.active_count(),
            "tcp554": tcp554_count(pid),
            "all_healthy": all_ok,
            "health_json": json.dumps(h),
        })
        if not all_ok:
            events.append({"elapsed_s": rows[-1]["elapsed_s"],
                           "event": "HEALTH_DIVERGENCE", "health": h})
        time.sleep(args.sample_sec)
    _write_csv("resource_samples.csv", rows)
    _write("stability_events.jsonl", events)
    stability_ok = len(events) == 0
    print(f"ESTABILIDAD={'PASS' if stability_ok else 'FAIL'} "
          f"eventos={len(events)}")

    # FASE 6: aislamiento — detener UNA cámara
    victim = cam_ids[-1]
    others = [c for c in cam_ids if c != victim]
    print(f"\n[FASE 6] Aislamiento: STOP {victim}; las otras deben seguir...")
    before = health_all(mgr, others)
    mgr.stop(victim)
    time.sleep(3)
    after = health_all(mgr, others)
    v_after = health_all(mgr, [victim])
    isolated = all(
        a.get("healthy") and a.get("readable_frames", 0) >=
        before[c].get("readable_frames", 0)
        for c, a in after.items()
    ) and not v_after.get(victim, {}).get("healthy", True)
    _write("isolation_stop.json", {"victim": victim, "others_before": before,
                                   "others_after": after, "victim_after": v_after,
                                   "isolated": isolated})
    print(f"ISOLATION_STOP={'PASS' if isolated else 'FAIL'}")

    # FASE 6b: restart aislado
    print(f"RESTART {victim} (las otras intactas)...")
    mgr.restart(victim)
    deadline = time.monotonic() + 60
    restarted = False
    while time.monotonic() < deadline:
        vh = health_all(mgr, [victim]).get(victim, {})
        if vh.get("healthy") and vh.get("readable_frames", 0) > 0:
            restarted = True
            break
        time.sleep(1)
    others_after_restart = health_all(mgr, others)
    restart_ok = restarted and all(
        x.get("healthy") for x in others_after_restart.values())
    _write("isolation_restart.json", {"victim": victim,
                                      "restarted": restarted,
                                      "others_after": others_after_restart})
    print(f"ISOLATION_RESTART={'PASS' if restart_ok else 'FAIL'}")

    # FASE 7: salud individual
    final_health = health_all(mgr, cam_ids)
    _write("final_health.json", final_health)
    print(f"\n[FASE 7] SALUD INDIVIDUAL:")
    for cid, h in final_health.items():
        print(f"  {cid}: state={h.get('state')} res={h.get('resolution')} "
              f"fps={h.get('fps')} frames={h.get('readable_frames')} "
              f"stall={h.get('stall_count')} q={h.get('queue_depth')} "
              f"err={h.get('last_error') or '-'}")

    # FASE 8: shutdown limpio
    print("\n[FASE 8] SHUTDOWN limpio (close_all)...")
    mgr.close_all()
    time.sleep(2)
    post = {c: mgr.health(c).healthy for c in cam_ids}
    post_tcp = tcp554_count(pid)
    post_threads = threading.active_count()
    clean = all(not v for v in post.values()) and post_tcp == 0
    _write("shutdown.json", {"post_healthy": post, "post_tcp554": post_tcp,
                             "post_threads": post_threads, "clean": clean})
    print(f"SHUTDOWN={'PASS' if clean else 'FAIL'} tcp554={post_tcp} "
          f"threads={post_threads}")

    # FASE 9: certificacion
    cert = {
        "verdict": "MULTICAMERA4_PHYSICAL_CERTIFIED" if (
            sim_all and stability_ok and isolated and restart_ok and clean
        ) else "MULTICAMERA4_PHYSICAL_NOT_CERTIFIED",
        "simultaneity": sim_all,
        "stability": stability_ok,
        "isolation_stop": isolated,
        "isolation_restart": restart_ok,
        "clean_shutdown": clean,
        "cameras": want,
        "stability_sec": args.stability_sec,
    }
    _write("certification.json", cert)
    print("\n" + "=" * 70)
    print("CERTIFICACION:", cert["verdict"])
    print("=" * 70)
    return 0 if cert["verdict"] == "MULTICAMERA4_PHYSICAL_CERTIFIED" else 2


def _write(name: str, obj) -> None:
    with (EVID / name).open("w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=2, ensure_ascii=False)


def _write_csv(name: str, rows: list) -> None:
    if not rows:
        return
    with (EVID / name).open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nINTERRUPTED")
        sys.exit(130)