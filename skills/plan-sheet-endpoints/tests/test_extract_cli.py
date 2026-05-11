import subprocess
import sys
from pathlib import Path


def test_cli_writes_three_outputs(multi_page_pdf: Path, tmp_path: Path):
    out_dir = tmp_path / "out"
    proc = subprocess.run(
        [
            sys.executable, "-m", "scripts.extract",
            str(multi_page_pdf),
            "--output-dir", str(out_dir),
        ],
        cwd=str(Path(__file__).parent.parent),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, f"stderr:\n{proc.stderr}\nstdout:\n{proc.stdout}"

    assert (out_dir / "plan_endpoints.csv").exists()
    assert (out_dir / "vicinity_reference.csv").exists()
    assert (out_dir / "plan_endpoints.kml").exists()


def test_cli_reports_summary_counts(multi_page_pdf: Path, tmp_path: Path):
    out_dir = tmp_path / "out"
    proc = subprocess.run(
        [
            sys.executable, "-m", "scripts.extract",
            str(multi_page_pdf),
            "--output-dir", str(out_dir),
        ],
        cwd=str(Path(__file__).parent.parent),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
    assert "plan-profile sheet" in proc.stdout.lower() or "sheets" in proc.stdout.lower()
    assert "native gps" in proc.stdout.lower() or "gps" in proc.stdout.lower()


def test_cli_rejects_nonexistent_input(tmp_path: Path):
    proc = subprocess.run(
        [
            sys.executable, "-m", "scripts.extract",
            str(tmp_path / "does_not_exist.pdf"),
        ],
        cwd=str(Path(__file__).parent.parent),
        capture_output=True,
        text=True,
    )
    assert proc.returncode != 0
