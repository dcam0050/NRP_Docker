#!/usr/bin/env bash

# Usage ./restart-server
# The script restarts a localhost backend

shopt -s expand_aliases
source $HBP/user-scripts/nrp_aliases
cle_restart_backend
