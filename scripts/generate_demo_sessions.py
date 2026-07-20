"""Rebuild the three sanitized demo sessions through the public workflow."""

from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

from decision_architect.engine import analyze_file
from decision_architect.reporting import generate_report
from decision_architect.result_serialization import write_result_json
from decision_architect.session_state import (
    SESSION_FILES,
    finalize_session,
    initialize_session,
    record_model_review,
    stage_proposed_model,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


DEMOS = (
    (
        "job-choice-demo",
        "job-choice.json",
        "job-choice-source-map.json",
    ),
    (
        "feynman-restaurant-8-visits-demo",
        "feynman-restaurant.json",
        "feynman-restaurant-8-visits-source-map.json",
    ),
    (
        "feynman-restaurant-2-visits-demo",
        "feynman-restaurant-short-horizon.json",
        "feynman-restaurant-2-visits-source-map.json",
    ),
)


def generate(destination_root: Path | None = None, project_root: Path = PROJECT_ROOT) -> None:
    sessions_root = destination_root or project_root / "demo_sessions"
    sessions_root.mkdir(parents=True, exist_ok=True)
    examples = project_root / "examples"
    source_maps = examples / "source-maps"
    with tempfile.TemporaryDirectory(prefix="decision-architect-demo-") as temporary:
        temporary_root = Path(temporary)
        for slug, model_name, source_map_name in DEMOS:
            model = json.loads((examples / model_name).read_text(encoding="utf-8"))
            model["confirmed_by_user"] = False
            source_types = json.loads((source_maps / source_map_name).read_text(encoding="utf-8"))

            directory = initialize_session(slug, sessions_root=temporary_root)
            stage_proposed_model(
                directory,
                model,
                default_source_type="system_proposal",
                source_types=source_types,
            )
            record_model_review(directory)
            confirmed = finalize_session(directory, confirmation="CONFIRM")
            result_path = directory / SESSION_FILES["result"]
            report_path = directory / SESSION_FILES["report"]
            write_result_json(analyze_file(confirmed), result_path)
            generate_report(result_path, report_path)

            target = sessions_root / slug
            target.mkdir(exist_ok=True)
            unexpected = {
                path.name for path in target.iterdir() if path.name not in SESSION_FILES.values()
            }
            if unexpected:
                raise RuntimeError(
                    f"Refusing to overwrite {target}: unexpected files {sorted(unexpected)}"
                )
            for filename in SESSION_FILES.values():
                shutil.copyfile(directory / filename, target / filename)


if __name__ == "__main__":
    generate()
