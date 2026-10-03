"""CLI:  python main.py --story "As a user, I want ..."   |   python main.py --file stories.json"""
import argparse
from pathlib import Path

from tcgen import export
from tcgen.preprocess import load_stories
from tcgen.service import run_generation


def main():
    p = argparse.ArgumentParser(description="Generate test cases from user stories")
    p.add_argument("--story", help="user story text")
    p.add_argument("--file", help=".txt or .json file with one or more stories")
    p.add_argument("--out", default="output", help="output folder")
    p.add_argument("--no-save", action="store_true", help="do not write to SQLite")
    args = p.parse_args()

    stories = [args.story] if args.story else []
    if args.file:
        path = Path(args.file)
        stories += load_stories(path.name, path.read_bytes())
    if not stories:
        p.error("provide --story or --file")

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for i, story in enumerate(stories, 1):
        r = run_generation(story, persist=not args.no_save)
        m, c = r["metrics"], r["classification"]
        print(f"\n[{i}] {story[:90]}")
        print(f"    category={c['category']} quality={c['quality']} | cases={m['total']} "
              f"coverage={m['coverage_percent']}% relevance={m['relevance_percent']}% (LLM: {r['llm_status']})")
        for t in r["trace"]:
            print(f"      {t['step']:>2}. {t['action']:<22} {t['observation']}")
        (out / f"story{i}.json").write_text(export.to_json_str(r), encoding="utf-8")
        (out / f"story{i}.csv").write_bytes(export.to_csv_bytes(r["test_cases"]))
        (out / f"story{i}.xlsx").write_bytes(export.to_excel_bytes(r))
    print(f"\nFiles written to {out.resolve()}")


if __name__ == "__main__":
    main()
