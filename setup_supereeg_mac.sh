#!/usr/bin/env bash

ENV_NAME="supereeg_env"
YML_FILE="create_supereeg_env_mac.yml"
REQ_FILE="requirements-mac.txt"

echo "🔹 Creating conda environment: $ENV_NAME"
conda env create -f "$YML_FILE"

echo "🔹 Activating environment"
# This is the *correct* way to activate conda inside scripts
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate "$ENV_NAME"

echo "🔹 Upgrading pip"
python -m pip install --upgrade pip

echo "🔹 Installing pip packages (NO dependency resolution)"
python -m pip install --no-deps -r "$REQ_FILE"

echo "🔹 Running sanity checks"

python - <<'PY'
import numpy as np
print("numpy:", np.__version__)
assert np.__version__.startswith("1.26"), "NumPy version is wrong!"

import deepdish
print("deepdish ok")

import hypertools
print("hypertools ok")

import torch
print("torch:", torch.__version__)

import gpytorch
print("gpytorch:", gpytorch.__version__)

import supereeg
print("supereeg ok")
PY

echo "✅ Supereeg environment setup complete!"
