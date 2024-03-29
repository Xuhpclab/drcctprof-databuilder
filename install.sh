#!/bin/bash

echo "install dependencies"
PYTHON_BIN=$(which python3)
${PYTHON_BIN} -m pip install --user protobuf==3.20.3
git submodule init
git submodule update
cd hatchet
${PYTHON_BIN} -m pip install --user --upgrade -r requirements.txt
git apply ../hatchet.diff
source ./install.sh
