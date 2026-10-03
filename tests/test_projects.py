"""Tests for saving and loading projects."""

import json
import os
from dataclasses import replace

import pytest

from patent_assistant import projects


@pytest.fixture(autouse=True)
def temp_projects_dir(tmp_path, monkeypatch):
    """Redirect the projects folder to a temporary directory."""
    monkeypatch.setattr(projects, "settings", replace(projects.settings, projects_dir=tmp_path))
    return tmp_path


def test_save_and_load_roundtrip():
    data = projects.empty_project() | {"project_name": "Test", "claims": "1. Anspruch."}
    projects.save_project("Test", data)
    assert projects.load_project("Test") == data


def test_saved_file_contains_format_version(temp_projects_dir):
    projects.save_project("Test", projects.empty_project())
    content = json.loads((temp_projects_dir / "Test.json").read_text(encoding="utf-8"))
    assert content["format_version"] == projects.FORMAT_VERSION


def test_legacy_german_keys_are_converted(temp_projects_dir):
    legacy = {"projektname": "Alt", "erfindung": "Ein Sensor.", "ansprueche": "1. X."}
    (temp_projects_dir / "Alt.json").write_text(json.dumps(legacy), encoding="utf-8")
    loaded = projects.load_project("Alt")
    assert loaded["project_name"] == "Alt"
    assert loaded["invention"] == "Ein Sensor."
    assert loaded["claims"] == "1. X."


def test_unknown_keys_are_ignored(temp_projects_dir):
    (temp_projects_dir / "X.json").write_text(json.dumps({"unbekannt": "x"}), encoding="utf-8")
    assert projects.load_project("X") == projects.empty_project()


def test_projects_sorted_by_last_modification(temp_projects_dir):
    for name, timestamp in [("Alt", 1_000), ("Neu", 3_000), ("Mitte", 2_000)]:
        projects.save_project(name, projects.empty_project())
        os.utime(temp_projects_dir / f"{name}.json", (timestamp, timestamp))
    assert projects.list_projects() == ["Neu", "Mitte", "Alt"]


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("Autonomer Mähroboter", "Autonomer_Mähroboter"),
        ("a/b\\c:d", "a_b_c_d"),
        ("   ", "projekt"),
    ],
)
def test_safe_filename(name, expected):
    assert projects.safe_filename(name) == expected
