import json
import os
from pathlib import Path

import pytest

DATA_DIR = Path("data")
REQUIRED_WORD_FIELDS = {"word", "uzbek", "description", "example"}
LEVEL_BUTTON_TO_FILE = {
    "📗 Elementary": "elementary.json",
    "📘 Pre-intermediate & Intermediate": "preintermediateintermediate.json",
}


@pytest.fixture(params=list(LEVEL_BUTTON_TO_FILE.values()))
def data_file(request):
    return DATA_DIR / request.param


def test_data_files_exist():
    for filename in LEVEL_BUTTON_TO_FILE.values():
        path = DATA_DIR / filename
        assert path.exists(), f"Data fayl topilmadi: {path}"


def test_data_file_valid_json(data_file):
    with open(data_file, encoding="utf-8") as f:
        data = json.load(f)
    assert "units" in data
    assert isinstance(data["units"], list)
    assert len(data["units"]) > 0


def test_data_file_units_structure(data_file):
    with open(data_file, encoding="utf-8") as f:
        data = json.load(f)

    seen_units = set()
    for unit in data["units"]:
        assert "unit" in unit
        assert "title" in unit
        assert "words" in unit

        unit_num = unit["unit"]
        assert isinstance(unit_num, int)
        assert unit_num not in seen_units, f"Takroriy unit: {unit_num}"
        seen_units.add(unit_num)

        words = unit["words"]
        assert isinstance(words, list)
        assert len(words) >= 1, f"Unit {unit_num} bo'sh"

        for word in words:
            missing = REQUIRED_WORD_FIELDS - word.keys()
            assert not missing, (
                f"{data_file.name} unit {unit_num}: "
                f"yetishmayotgan maydonlar {missing}"
            )
            assert word["word"].strip(), f"Unit {unit_num}: bo'sh 'word'"
            assert word["uzbek"].strip(), f"Unit {unit_num}: bo'sh 'uzbek'"


def test_level_name_maps_to_existing_file():
    for level_button, filename in LEVEL_BUTTON_TO_FILE.items():
        clean = "".join(filter(str.isalnum, level_button)).lower()
        expected_path = DATA_DIR / f"{clean}.json"
        assert os.path.exists(expected_path), (
            f"Level '{level_button}' → {expected_path} topilmadi"
        )
        assert expected_path.name == filename
