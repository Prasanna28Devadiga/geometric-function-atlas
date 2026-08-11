from __future__ import annotations

import json
import sqlite3
import subprocess
import sys

from test_snapshot import make_snapshot

from geometric_function_atlas import RegistrySnapshot


def test_snapshot_exposes_website_paper_facets_and_explicit_legacy_tables(tmp_path) -> None:
    database, _manifest = make_snapshot(tmp_path)
    connection = sqlite3.connect(database)
    connection.executescript(
        """
        INSERT INTO functions VALUES
          (1, 'legacy-sine', 'Legacy sine', 'special', 'DLMF 4',
           '[1,0,-1/6]', 'legacy record', 'fixture', 'paper.pdf', NULL);
        INSERT INTO tags VALUES (1, 'image_processing', 'application');
        INSERT INTO function_tags VALUES (1, 1);
        INSERT INTO paper_tags VALUES (1, 1);
        """
    )
    connection.commit()
    connection.close()
    unverified = tmp_path / "unverified.sqlite"
    database.rename(unverified)

    with RegistrySnapshot.open(unverified) as snapshot:
        papers = snapshot.papers(decade=2020, has_theorems=False, tag="image_processing")
        assert papers[0].id == 1
        assert papers[0].theorem_count == 0
        assert snapshot.papers(msc="30C") == ()

        facets = snapshot.paper_facets()
        assert facets["decades"]["2020"] == 1
        assert facets["tags"]["image_processing"] == 1

        legacy = snapshot.legacy_functions(tag="image_processing")
        assert legacy[0].name == "legacy-sine"
        assert legacy[0].tags == ("image_processing",)
        assert snapshot.function("legacy-sine").dlmf_ref == "DLMF 4"

        tags = snapshot.tags(category="application")
        assert tags[0].name == "image_processing"
        assert tags[0].function_count == 1
        assert tags[0].paper_count == 1


def test_snapshot_facet_and_legacy_cli_paths_are_available(tmp_path) -> None:
    database, _manifest = make_snapshot(tmp_path)
    connection = sqlite3.connect(database)
    connection.executescript(
        """
        INSERT INTO functions VALUES
          (1, 'legacy-sine', 'Legacy sine', 'special', 'DLMF 4',
           '[1,0,-1/6]', 'legacy record', 'fixture', 'paper.pdf', NULL);
        INSERT INTO tags VALUES (1, 'image_processing', 'application');
        INSERT INTO function_tags VALUES (1, 1);
        INSERT INTO paper_tags VALUES (1, 1);
        """
    )
    connection.commit()
    connection.close()
    unverified = tmp_path / "cli-unverified.sqlite"
    database.rename(unverified)
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "geometric_function_atlas",
            "functions",
            "--snapshot",
            str(unverified),
            "--tag",
            "image_processing",
            "--json",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout)[0]["name"] == "legacy-sine"

    facets = subprocess.run(
        [
            sys.executable,
            "-m",
            "geometric_function_atlas",
            "paper-facets",
            "--snapshot",
            str(unverified),
            "--json",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert facets.returncode == 0, facets.stderr
    assert "decades" in json.loads(facets.stdout)
