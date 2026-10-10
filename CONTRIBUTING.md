# Contributing

Contributions are welcome through focused issues and pull requests.

## Before opening a pull request

1. Keep changes small and explain the behavior they change.
2. Run `python3 -m unittest -v` with Python 3.10 or newer.
3. Update the README when CSV validation or command-line behavior changes.
4. Do not add runtime dependencies without a clear need.

## Location-data privacy

GNSS logs can disclose sensitive locations and routines. Never attach real logs, coordinates, timestamps, or identifying device data to an issue or pull request. Use synthetic test rows instead. Generated reports and local files should remain outside version control unless they are intentionally created as clearly synthetic fixtures.
