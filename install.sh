#!/bin/bash

python3 -m pip install protobuf
git submodule init
git submodule update
cd hatchet
git apply ../hatchet.diff
source ./install.sh
