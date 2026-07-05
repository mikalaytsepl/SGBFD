#!/bin/bash

set -e 

echo "=== INSTALLING DEPENDENCIES ===" 
apt-get update && \
apt-get install build-essential python3-pip cmake python3.12-venv git -y

echo "=== CLONING OFIQ ==="
git clone "https://github.com/BSI-OFIQ/OFIQ-Project"

echo "=== CREATING VENV AND INSTALLING CONAN 2.18.1 ==="
python3 -m venv py_ofiq_env && \
py_ofiq_env/bin/pip install --upgrade pip && \
py_ofiq_env/bin/pip install conan==2.18.1 # as there's no source command in this ubuntu image, that's what i have to resort to

echo "=== Addinig env bin to the path and bypassing abscence of source for venv ===" 
./py_ofiq_env/bin/conan profile detect --force
export PATH="$(pwd)/py_ofiq_env/bin:$PATH"

echo "=== Installing required packages and building ==" 
# source /path/to/py_ofiq_env/bin/activate  i guess we don't need it right now as we had already activated it 1 time
cd OFIQ-Project/scripts && \
if [ -e "build.sh" ]; then
    sh build.sh
else 
    echo "FATAL: build file not found, exiting"
    exit 1
fi 
