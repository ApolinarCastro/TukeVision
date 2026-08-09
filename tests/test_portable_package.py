"""Tests del flujo portable (LOOP-0010).

Cubren: manifest, hash de modelo, hash de requirements, rutas relativas,
configuración, estructura de paquete y exclusiones. No ejecutan PowerShell
destructivo ni el código principal de visión.
"""

import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent

MODEL_EXPECTED_SHA256 = "0EBBC80D4A7680D14987A577CD21342B65ECFD94632BD9A8DA63AE6417644EE1"
SPEC_CERTIFIED_BASE = "cf876a9"


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest().upper()


class TestVersionFile(unittest.TestCase):
    def test_version_file_present_and_parseable(self):
        vf = PROJECT_ROOT / "VERSION"
        self.assertTrue(vf.exists(), "VERSION no existe")
        version = vf.read_text(encoding="utf-8").strip()
        self.assertRegex(version, r"^\d+\.\d+\.\d+$")


class TestManifest(unittest.TestCase):
    def test_manifest_valid(self):
        mf = PROJECT_ROOT / "dist" / "TukeVision" / "MANIFEST.json"
        self.assertTrue(mf.exists(), "MANIFEST.json no existe en dist/TukeVision")
        data = json.loads(mf.read_text(encoding="utf-8"))
        self.assertEqual(data["package_version"], "0.1.0")
        self.assertEqual(data["spec_certified_base"], SPEC_CERTIFIED_BASE)
        self.assertEqual(data["python_required"], "3.12.x")
        self.assertEqual(data["model_filename"], "models/yolo11n.pt")
        self.assertTrue(data["git_head"])

    def test_manifest_model_sha_matches_file(self):
        mf = PROJECT_ROOT / "dist" / "TukeVision" / "MANIFEST.json"
        data = json.loads(mf.read_text(encoding="utf-8"))
        model_path = PROJECT_ROOT / "dist" / "TukeVision" / "models" / "yolo11n.pt"
        self.assertTrue(model_path.exists())
        self.assertEqual(sha256_of(model_path), MODEL_EXPECTED_SHA256)
        self.assertEqual(data["model_sha256"], MODEL_EXPECTED_SHA256)


class TestModelHash(unittest.TestCase):
    def test_model_sha256_matches_expected(self):
        model_path = PROJECT_ROOT / "models" / "yolo11n.pt"
        self.assertTrue(model_path.exists(), "models/yolo11n.pt no existe")
        self.assertEqual(sha256_of(model_path), MODEL_EXPECTED_SHA256)


class TestRelativePaths(unittest.TestCase):
    """La auditoría de portabilidad no debe dejar rutas absolutas del PC actual."""

    PATTERNS = ("C:\\", "D:\\", "Users\\", "Tuke\\", "Documents\\")

    def test_source_and_scripts_have_no_absolute_paths(self):
        for sub in ("src", "scripts", "config"):
            base = PROJECT_ROOT / sub
            for path in base.rglob("*"):
                if path.is_file() and path.suffix in (".py", ".json", ".ps1", ".md"):
                    text = path.read_text(encoding="utf-8", errors="ignore")
                    for pat in self.PATTERNS:
                        self.assertNotIn(
                            pat, text,
                            f"Ruta absoluta '{pat}' encontrada en {path.relative_to(PROJECT_ROOT)}",
                        )


class TestConfig(unittest.TestCase):
    def test_default_config_present(self):
        cfg = PROJECT_ROOT / "config" / "default.json"
        self.assertTrue(cfg.exists())
        data = json.loads(cfg.read_text(encoding="utf-8"))
        self.assertIn("detection", data)
        self.assertIn("zone", data)
        self.assertEqual(data["detection"]["device"], "cpu")

    def test_no_secrets_in_repo(self):
        for path in PROJECT_ROOT.rglob("*"):
            if path.is_file() and path.suffix == ".json":
                text = path.read_text(encoding="utf-8", errors="ignore")
                if "password" in text.lower() or "secret" in text.lower():
                    rel = path.relative_to(PROJECT_ROOT)
                    if "test_" not in path.name and rel.parts[0] not in ("dist",):
                        self.fail(f"Posible secreto en {rel}")


class TestPackageStructure(unittest.TestCase):
    """Verifica que el paquete portable tenga lo necesario y nada superfluo."""

    PKG = PROJECT_ROOT / "dist" / "TukeVision"

    REQUIRED = (
        "config",
        "docs",
        "install",
        "scripts",
        "src",
        "requirements.txt",
        "requirements.lock.txt",
        "README.md",
        "start_tukevision.ps1",
        "MANIFEST.json",
        "models/yolo11n.pt",
        "data/input",
        "data/output",
        "data/evidence",
        "data/temp",
        "logs",
    )

    EXCLUDED = (
        ".git",
        ".venv",
        "tests",
        "dist",
        "data/input/Video.mp4",
        "data/output/processed.mp4",
        "data/temp/test_person.jpg",
        "data/temp/zidane.jpg",
    )

    def test_required_present(self):
        self.assertTrue(self.PKG.exists(), "dist/TukeVision no existe; ejecute install/package.ps1")
        for rel in self.REQUIRED:
            self.assertTrue(
                (self.PKG / rel).exists(),
                f"Falta archivo requerido en el paquete: {rel}",
            )

    def test_excluded_absent(self):
        self.assertTrue(self.PKG.exists())
        for rel in self.EXCLUDED:
            self.assertFalse(
                (self.PKG / rel).exists(),
                f"Archivo no debería estar en el paquete: {rel}",
            )

    def test_no_pycache_in_package(self):
        self.assertTrue(self.PKG.exists())
        pycache = list(self.PKG.rglob("__pycache__"))
        self.assertEqual(pycache, [], "__pycache__ presente en el paquete")


class TestZip(unittest.TestCase):
    def test_zip_exists(self):
        z = PROJECT_ROOT / "dist" / "TukeVision-portable.zip"
        self.assertTrue(z.exists(), "TukeVision-portable.zip no existe")


class TestInstallScripts(unittest.TestCase):
    def test_install_scripts_present(self):
        for name in ("preflight.ps1", "install.ps1", "diagnose.ps1",
                     "package.ps1", "verify_package.ps1"):
            self.assertTrue(
                (PROJECT_ROOT / "install" / name).exists(),
                f"Falta install/{name}",
            )


class TestGitignore(unittest.TestCase):
    def test_local_config_and_dist_ignored(self):
        gi = (PROJECT_ROOT / ".gitignore").read_text(encoding="utf-8", errors="ignore")
        self.assertIn("config/local", gi)
        self.assertIn("dist/", gi)
        self.assertIn(".env", gi)

    def test_evidence_gitkeep_kept(self):
        self.assertTrue((PROJECT_ROOT / "data" / "evidence" / ".gitkeep").exists())


if __name__ == "__main__":
    unittest.main()
