"""Turn moment-map signals into editable, source-aware visual briefs."""
from __future__ import annotations

import argparse, json, re
from pathlib import Path
from typing import Any
from src.longform_ingest import PROJECTS

ENTITY_PATTERNS = {
    "football": r"\b(match|season|goal|defen[cs]e|back line|defender|striker|manager|team|club|league|ninety|90)\b",
    "stats": r"\b(\d+(?:\.\d+)?%?|\d+\s*(?:minutes?|goals?|shots?|points?))\b",
    "reporting": r"\b(said|says|according|report|article|post|tweet|comment|quote|press conference)\b",
    "reaction": r"\b(what|wow|crazy|ridiculous|awful|brilliant|unbelievable|fuming|love|hate|funny|insane|disaster|terrible|heck)\b",
}

def classify(text: str, visual_reference: bool) -> tuple[list[str], str, str]:
    low = text.lower()
    entities = [name for name, pattern in ENTITY_PATTERNS.items() if re.search(pattern, low, re.I)]
    if "reporting" in entities:
        source_type, purpose = "exact_reference", "show the referenced post, quote, report, or press clip"
    elif "stats" in entities:
        source_type, purpose = "stat_card", "show the number beside the subject it describes"
    elif visual_reference:
        source_type, purpose = "event_reference", "use the exact referenced event or source visual"
    elif "reaction" in entities:
        source_type, purpose = "reaction_support", "punctuate the reaction with a meme or expressive graphic"
    else:
        source_type, purpose = "host_primary", "keep the talking head primary and add restrained emphasis"
    return entities, source_type, purpose

def build_briefs(moment_map: dict[str, Any]) -> list[dict[str, Any]]:
    briefs = []
    for moment in moment_map.get("moments", []):
        entities, source_type, purpose = classify(moment["text"], moment["signals"].get("visual_reference", False))
        query = " ".join(moment["text"].split())
        if source_type == "exact_reference":
            fallback = "If unavailable: capture the exact page or use a text quote card with source and date."
        elif source_type == "stat_card":
            fallback = "If unavailable: create a clean stat card and label the source for later verification."
        elif source_type == "event_reference":
            fallback = "If unavailable: use a clearly labeled still, then leave a replacement note."
        elif source_type == "reaction_support":
            fallback = "If unavailable: use a simple reaction card or keep host full-frame."
        else:
            fallback = "No external asset required; use crop, punch-in, caption emphasis, or sound accent."
        briefs.append({
            "brief_id": f"brief_{moment['moment_id'].split('_')[-1]}",
            "moment_id": moment["moment_id"], "start": moment["start"], "end": moment["end"],
            "source_type": source_type, "entities": entities, "purpose": purpose,
            "search_query": query, "preferred_asset": "exact source first; preserve any useful source visual",
            "fallback": fallback, "rights_review": "LOCAL_REFERENCE_REVIEW",
            "editable": True, "locked": False,
        })
    return briefs

def process(project_id: str, projects: Path = PROJECTS) -> dict[str, Any]:
    project = projects / project_id
    moment_path = project / "analysis" / "moment_map.json"
    data = json.loads(moment_path.read_text(encoding="utf-8"))
    briefs = build_briefs(data)
    out = project / "analysis" / "visual_briefs.json"
    out.write_text(json.dumps({"schema": "crimson.longform.visual_briefs.v1", "briefs": briefs}, indent=2), encoding="utf-8")
    manifest_path = project / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["processing"]["visual_briefs"] = {"status": "complete", "path": str(out), "count": len(briefs)}
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return {"visual_briefs": str(out), "brief_count": len(briefs)}

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("project_id")
    parser.add_argument("--projects", type=Path, default=PROJECTS)
    args = parser.parse_args()
    print(json.dumps(process(args.project_id, args.projects), indent=2))

if __name__ == "__main__": main()
