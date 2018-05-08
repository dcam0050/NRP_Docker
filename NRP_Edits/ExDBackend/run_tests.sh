#!/bin/bash
# This script is designed for local usage.

# Code coverage does not seem work without /nfs4 or /gpfs access
export VIRTUAL_ENV=$NRP_VIRTUAL_ENV

make test-nocover
RET=$?


if [ $RET == 0 ]; then
    echo -e "\033[32mTest sucessfull.\e[0m"
else
    echo -e "\033[31mTest failed.\e[0m See errors above."
fi

exit $RET
