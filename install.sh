#!/bin/bash

git submodule init
git submodule update
cd hatchet
git apply ../hatchet.diff
source ./install.sh
