# 2GIS GIT Hooks

![GitHub License](https://img.shields.io/github/license/sadads1337/dgis_hooks)
![GitHub Release](https://img.shields.io/github/v/release/sadads1337/dgis_hooks?include_prereleases)
![Build and test](https://github.com/sadads1337/dgis_hooks/actions/workflows/python-package.yml/badge.svg)
![MyPy and audit](https://github.com/sadads1337/dgis_hooks/actions/workflows/mypy-audit.yml/badge.svg)

Small lightweight package for GIT hooks management.

## Dependencies

All deps listed in `requirements.txt` and `pyproject.toml`.

### Build & run

- At least python 3.8 to build.
- At least python 3.6 to install and run.

### Packages

| Package            | Version |
|--------------------|---------|
| GitPython          | >=3.1   |
| pytest             | >=8.1   |
| simplejson         | >=3.19  |
| importlib-metadata | >=7.0   |
| dataclasses        | >=0.6   |
| colorama           | >=0.4   |
| black              | >=24.3  |
| types-simplejson   | >=3.19  |
| requests           | >=2.28  |


## Build

### Release

Execute in project root dir to make local package installation:
```bash
pip3 install .
```

Or execute to build a wheel
```bash
python3 -m build
```

### Debug (dev)

Execute in project root dir
```bash
pip3 install -e .
```

To run all tests call 
```bash
pytest .
```

### Code style

We use Black to format project code. Install dependencies (or at least Black) and run:

```bash
black . # or black <path_to_file_or_dir> to format specific file or dir
```

Black configuration is available in `pyproject.toml`.

## Run

There are 3 entry points:
- `dgis-pre-receive` - entry point to execute pre receive checks
- `dgis-gitlab-ci-run` - entry point to execute checks on gitlab CI/CD
- `dgis-clang-format-diff` - entry point to execute clang-format

Execute script with `--help` argument to get all available parameters.

## Plugins

This package has some built in checks which can be disabled (see positional arguments of `dgis-pre-receive`).

By default, all checks with module placed in namespace `dgis.hooks.plugins` executed (enabled) while running `dgis-pre-receive`.

**But it's possible to**
1. Select only necessary by passing positional argument with **plugin class name** to `dgis-pre-receive`.
2. Add user-side checks by implementing class in a module placed in namespace `dgis.hooks.plugins`.

## GitLab reporter (CI integration)

The project includes a GitLab reporter used in `dgis-gitlab-ci-run` to post inline comments (discussions) to Merge Requests.

Key behavior and environment variables:

- Required CI environment variables (set by GitLab CI or override locally when testing):
  - `CI_API_V4_URL` — base API URL, e.g. `https://gitlab.example/api/v4`
  - `CI_PROJECT_ID` — numeric project id
  - `CI_MERGE_REQUEST_IID` — MR internal id (IID)
  - `LINT_REVIEW_PERSONAL_ACCESS_TOKEN` — personal token or private token used to post comments (if not set, posting is skipped)

- Dedupe strategy implemented (default):
  1. Reporter fetches existing discussions for the target MR (handles pagination).
  2. Each published comment includes an invisible HTML marker `<!-- lint-review -->` to identify comments created by this tool.
  3. Before posting, reporter compares the exact comment body (after strip) with existing bodies for the same file path. If an identical body exists, posting for that file is skipped (to avoid duplicates on repeated CI runs).
  4. Local cache is updated after a successful post within the same run to prevent duplicate posts during one execution.

- Notes / limitations:
  - Deduplication is based on exact body equality (after trimming). If the formatted content changes (even slightly), it will be considered a different comment and posted again.
  - If you prefer an "update in-place" behaviour (single comment is updated rather than skipped or duplicated), that can be implemented: reporter should store/obtain `discussion_id`/`note_id` for the bot's comments (by marker) and perform an update request instead of POST. This requires additional API calls and tests; ask if you want this behaviour.

## Contributing

PRs, issues and suggestions welcome. Please follow the existing style and run tests (`pytest`) before pushing changes.
