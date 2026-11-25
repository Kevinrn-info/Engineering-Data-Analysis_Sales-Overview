"""Run the full pipeline:  python -m summitbase  [--dry-run] [--export]

--dry-run  extract, transform and validate only (no database needed)
--export   also write the cleaned tables to data/processed/*.csv
"""

from __future__ import annotations

import argparse
import logging
import sys
import time

from summitbase.config import PROCESSED_DIR, DbSettings
from summitbase.extract import extract_all
from summitbase.load import load_all
from summitbase.transform import transform_all
from summitbase.validate import validate_all

log = logging.getLogger("summitbase")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="summitbase", description="SummitBase ETL pipeline")
    parser.add_argument("--dry-run", action="store_true", help="skip the database load")
    parser.add_argument("--export", action="store_true", help="write data/processed/*.csv")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    start = time.perf_counter()

    raw = extract_all()
    log.info("Extracted %s rows from %s files", sum(map(len, raw.values())), len(raw))

    clean = transform_all(raw)
    log.info("Transformed tables: %s", ", ".join(clean))

    issues = validate_all(clean)
    if issues:
        for issue in issues:
            log.error("Data quality: %s", issue)
        log.error("Pipeline stopped: %s data-quality issue(s)", len(issues))
        return 1
    log.info("Data quality: all checks passed")

    if args.export:
        PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
        for name, df in clean.items():
            df.to_csv(PROCESSED_DIR / f"{name}.csv", index=False)
        log.info("Exported cleaned CSVs to %s", PROCESSED_DIR)

    if not args.dry_run:
        counts = load_all(DbSettings.from_env().conninfo(), clean)
        for name, n in counts.items():
            log.info("Loaded staging.%-12s %8d rows", name, n)
        log.info("Analytics views rebuilt")

    log.info("Done in %.1fs", time.perf_counter() - start)
    return 0


if __name__ == "__main__":
    sys.exit(main())
