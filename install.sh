#!/bin/sh

git submodule init
cd hatchet
git apply ../hatchet.diff
source ./install.sh