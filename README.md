# Keepsake UI
Out of the box web UI to visualize machine learning experiments versioned
by [keepsake](https://github.com/replicate/keepsake). Supports listing experiments,
experiment deletion and comparison.

## Installation
You can install the tool via pip
```
pip install keepsake_ui
```

## Usage
If you have `keepsake.yaml` in your current directory you can run
```
keepsake-ui
```
and open http://localhost:8080 in your web browser to see the
experiments and checkpoints.

Alternatively, you can manually specify the repository via `-r` option
```
keepsake-ui -r "<repository>"
```
