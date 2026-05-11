"""CLI entry point for plan-sheet-endpoints.

Usage:
    python -m scripts.extract <pdf_or_folder> [--output-dir <dir>]

Produces three deliverables in --output-dir:
    plan_endpoints.csv         - one row per plan-profile sheet
    vicinity_reference.csv     - cover/vicinity-page coords (reference only)
    plan_endpoints.kml         - pins for sheets with native GPS only
"""
import argparse
import sys
from pathlib import Path
from typing import List, Optional

from scripts.output_writer import write_kml, write_main_csv, write_vicinity_csv
from scripts.pdf_processor import process_input


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Extract per-sheet start/end metadata from fiber/cable construction-drawing PDFs.",
    )
    parser.add_argument("input", type=Path, help="Path to a PDF file or a folder of PDFs")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("output"),
        help="Output directory (default: ./output)",
    )
    args = parser.parse_args(argv)

    if not args.input.exists():
        print(f"ERROR: input path does not exist: {args.input}", file=sys.stderr)
        return 2

    args.output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Processing {args.input} ...")
    results = process_input(args.input)

    main_csv = args.output_dir / "plan_endpoints.csv"
    vicinity_csv = args.output_dir / "vicinity_reference.csv"
    kml_path = args.output_dir / "plan_endpoints.kml"

    write_main_csv(results, main_csv)
    write_vicinity_csv(results, vicinity_csv)
    write_kml(results, kml_path)

    total_sheets = sum(len(r.sheets) for r in results)
    native_gps = sum(1 for r in results for s in r.sheets if s.has_native_gps)
    raster_pages = sum(len(r.raster_pages) for r in results)
    vicinity_count = sum(len(r.vicinity_coords) for r in results)

    print(f"  PDFs processed:        {len(results)}")
    print(f"  Plan-profile sheets:   {total_sheets}")
    print(f"  Sheets with native GPS:{native_gps}")
    print(f"  Vicinity coord rows:   {vicinity_count}")
    print(f"  Raster pages flagged:  {raster_pages}")
    print(f"  CSV: {main_csv}")
    print(f"  CSV: {vicinity_csv}")
    print(f"  KML: {kml_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
