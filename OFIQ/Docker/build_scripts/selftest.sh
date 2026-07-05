#!/bin/bash

sh "$HOME/OFIQ-Project/scripts/conformance_tests.sh"
rc=$?

if [ $rc -eq 0 ]; then
    echo "conformance tests passed, container is ready" 
    exit 0
else
    echo "FATAL: cofnormance tests failed, contanier can not be used"
    exit 1
fi