# 2GIS GIT Hooks

![GitHub License](https://img.shields.io/github/license/sadads1337/dgis_hooks)
![GitHub Release](https://img.shields.io/github/v/release/sadads1337/dgis_hooks?include_prereleases)
![Build and test](https://github.com/sadads1337/dgis_hooks/actions/workflows/python-package.yml/badge.svg)

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

## Run

There are 2 entry points:
- `dgis-pre-receive` - entry point to execute pre receive checks 
- `dgis-clang-format-diff` - entry point to execute clang-format

Execute script with `--help` argument to get all available parameters.

## Plugins

This package has some built in checks which can be disabled (see positional arguments of `dgis-pre-receive`).

By default, all checks with module placed in namespace `dgis.hooks.plugins` executed (enabled) while running `dgis-pre-receive`.

**But it's possible to**
1. Select only necessary by passing positional argument with **plugin class name** to `dgis-pre-receive`.
2. Add user-side checks by implementing class in a module placed in namespace `dgis.hooks.plugins`.
