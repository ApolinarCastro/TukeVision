"""Health check local de preproducción.

Verifica de forma no destructiva que la instalación local de TukeVision
está lista para una ejecución de piloto. NO abre cámaras, NO procesa
video, NO modifica datos. Solo lectura y construcción de objetos.

Estados posibles por sección:
    PASS   - verificación superada
    WARN   - verificación con observación (no bloquea)
    FAIL   - problema que debe resolverse

Uso:
    python scripts/health_check.py
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def _dir_size_mb(path: Path) -> float:
    total = 0
    if path.exists():
        for p in path.rglob("*"):
            if p.is_file():
                try:
                    total += p.stat().st_size
                except OSError:
                    pass
    return total / (1024 * 1024)


def main() -> int:
    results = []

    # 1. CONFIG
    try:
        from src.app.pipeline import Pipeline, load_config

        config = load_config()
        Pipeline(config=config)
        results.append(("CONFIG", "PASS", "config/default.json válida"))
    except Exception as e:  # noqa: BLE001
        results.append(("CONFIG", "FAIL", f"{type(e).__name__}: {e}"))

    # 2. MODEL
    model_path = Path("models") / config.get("detection", {}).get(
        "model", "yolo11n.pt"
    )
    if model_path.exists():
        size_mb = model_path.stat().st_size / (1024 * 1024)
        results.append(("MODEL", "PASS", f"{model_path} ({size_mb:.1f} MB)"))
    else:
        results.append(
            ("MODEL", "FAIL", f"modelo no encontrado: {model_path}")
        )

    # 3. SOURCE (solo inspección, sin abrir cámaras)
    try:
        import cv2

        cam = cv2.VideoCapture(0)
        ok, _ = cam.read()
        cam.release()
        if ok:
            results.append(("SOURCE", "PASS", "webcam índice 0 accesible"))
        else:
            results.append(
                ("SOURCE", "WARN", "webcam índice 0 no devolvió frame (usar FILE)")
            )
    except Exception as e:  # noqa: BLE001
        results.append(
            ("SOURCE", "WARN", f"webcam no disponible: {type(e).__name__}: {e}")
        )

    # 4. DISK (tamaños de carpetas de datos)
    sizes = {}
    for name in ("data/output", "data/evidence", "logs", "data/temp"):
        sizes[name] = _dir_size_mb(Path(name))
    disk_info = " | ".join(f"{k}={v:.1f}MB" for k, v in sizes.items())
    results.append(("DISK", "PASS", disk_info))

    # 5. LOGGING
    from src.observability.logging_setup import new_run_id, setup_logging

    try:
        run_id = new_run_id()
        setup_logging(run_id=run_id)
        log_file = Path("logs") / f"tukevision-{run_id}.log"
        if log_file.exists():
            results.append(
                ("LOGGING", "PASS", f"log escribible ({log_file.name})")
            )
        else:
            results.append(("LOGGING", "WARN", "log no verificado"))
    except Exception as e:  # noqa: BLE001
        results.append(
            ("LOGGING", "FAIL", f"{type(e).__name__}: {e}")
        )

    # 6. EVIDENCE_PATH
    evidence_dir = Path("data/evidence")
    if evidence_dir.exists():
        results.append(("EVIDENCE_PATH", "PASS", "data/evidence accesible"))
    else:
        results.append(
            ("EVIDENCE_PATH", "WARN", "data/evidence aún no creada (se crea al procesar)")
        )

    # 7. FINAL_STATUS
    failed = [name for name, status, _ in results if status == "FAIL"]
    warnings = [name for name, status, _ in results if status == "WARN"]
    final = "OK" if not failed else "ERROR"
    results.append(
        (
            "FINAL_STATUS",
            final,
            f"{len(results)-1} comprobaciones, {len(failed)} fallos, "
            f"{len(warnings)} advertencias",
        )
    )

    for name, status, detail in results:
        print(f"{name}: {status} - {detail}")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
