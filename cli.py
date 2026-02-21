import argparse
import json
import os
import sys
import db
import scraper


def parse_args(argv: list[str]):
    p = argparse.ArgumentParser(
        prog="job-scraper",
        description="Job Scraper Tool by Firas Lamouchi",
    )
    p.add_argument("--config", default=os.environ.get("CONFIG_DIR", "./config"))
    p.add_argument("--data", default=os.environ.get("DATA_DIR", "./data"))

    sub = p.add_subparsers(dest="cmd", required=True)

    run = sub.add_parser("run")
    run.add_argument("--api-key", default=os.environ.get("GROQ_API_KEY", ""))
    run.add_argument("--lite", action="store_true")

    export = sub.add_parser("export")
    export.add_argument("--format", choices=["json", "csv"], default="json")
    export.add_argument("--limit", type=int, default=200)
    export.add_argument("--out", default="-")

    return p.parse_args(argv)


def write_json(rows: list[dict], out_path: str):
    payload = json.dumps(rows, ensure_ascii=False, indent=2)
    if out_path == "-":
        sys.stdout.write(payload)
        sys.stdout.write("\n")
        return
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(payload)
        f.write("\n")


def write_csv(rows: list[dict], out_path: str):
    import csv

    fieldnames = []
    for r in rows:
        for k in r.keys():
            if k not in fieldnames:
                fieldnames.append(k)

    if out_path == "-":
        w = csv.DictWriter(sys.stdout, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)
        return

    with open(out_path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def main(argv: list[str] | None = None):
    args = parse_args(sys.argv[1:] if argv is None else argv)
    os.environ["CONFIG_DIR"] = args.config
    os.environ["DATA_DIR"] = args.data

    if args.cmd == "run":
        scraper.run_scrape(args.api_key or "", bool(args.lite))
        return 0

    if args.cmd == "export":
        db.init()
        rows = db.list_jobs(limit=args.limit)
        if args.format == "json":
            write_json(rows, args.out)
        else:
            write_csv(rows, args.out)
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
