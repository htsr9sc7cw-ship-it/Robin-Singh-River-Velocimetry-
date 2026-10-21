#!/bin/bash
# Double-click this file: draws all diagrams of the thesis and compares them with the thesis pictures.
cd "$(dirname "$0")"
/opt/anaconda3/bin/python3 run_all_diagrams.py
echo
read -n 1 -s -r -p "Done. Press any key to close."
