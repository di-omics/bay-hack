# Presence of this file at the repo root puts the root on sys.path during test
# collection, so the bare `pytest` console script (as CI runs it) can import the
# `bayhack` package the same way `python -m pytest` does -- no editable install,
# keeping the sim path dependency-free.
