from app import build_demo_items


def main() -> None:
    items = build_demo_items()
    assert len(items) == 3
    assert items[0] == "Python virtual environment"
    assert "Streamlit" in items[1]
    print("Smoke test passed.")


if __name__ == "__main__":
    main()
