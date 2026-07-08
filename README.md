# CEN3031 Group Project

Minimal Python + Streamlit + SQLite starter environment.

## What is included

- `app.py`: Streamlit frontend for creating and viewing records
- `database.py`: SQLite helper functions for initializing and managing data
- `smoke_test.py`: quick backend and template validation
- `requirements.txt`: Python dependencies for the project

SQLite is included with Python, so no extra database package is required.

## Setup

```zsh
cd /Users/joeyd/Desktop/School/COP4020/CEN3031_GroupProject
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Run the app

```zsh
streamlit run app.py
```

The first time you save a record, the app will create a local SQLite database file named `app.db` in the project directory.

## Run the smoke test

```zsh
python smoke_test.py
```

## Run the tests

`unit_tests.py` and `test_app.py` are `pytest` test suites, so run them with `pytest` from the project root:

```zsh
python3 -m pip install -r requirements.txt
python3 -m pytest -q unit_tests.py test_app.py
```

If you run either test file with `streamlit run`, Streamlit will open a browser tab, but the page will be blank because those files only define tests—they are not Streamlit apps. Use `streamlit run app.py` only for the actual application.

## Suggested next steps

- Add more tables and database functions in `database.py`
- Replace the starter form with your real application fields
- Split the UI into additional Streamlit pages as the app grows

