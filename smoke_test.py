from tempfile import TemporaryDirectory
from pathlib import Path
from database import initialize_database, add_entry, list_entries, delete_entry


def main() -> None:
    with TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "smoke_test.db"
        initialize_database(db_path)

        first_id = add_entry("Feature A", "Initial notes", db_path)
        second_id = add_entry("Feature B", "", db_path)

        entries = list_entries(db_path)
        assert [entry["id"] for entry in entries] == [second_id, first_id]
        assert entries[0]["title"] == "Feature B"
        assert entries[1]["details"] == "Initial notes"

        assert delete_entry(first_id, db_path) is True
        assert len(list_entries(db_path)) == 1

    print("Smoke test passed.")


if __name__ == "__main__":
    main()
