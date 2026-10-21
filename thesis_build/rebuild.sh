#!/bin/bash
# two-pass build so that the contents page numbers are stable
cd "$(dirname "$0")"
# nA_appendix.md is edited directly; build_appendix.py no longer regenerates it
rm -f pagemap.json
python3 build_thesis2.py >/dev/null 2>&1 && bash export_pdf.sh >/dev/null 2>&1 && python3 pagemap.py
python3 build_thesis2.py >/dev/null 2>&1 && bash export_pdf.sh >/dev/null 2>&1; cp pagemap.json /tmp/pm_prev.json
python3 pagemap.py; cmp pagemap.json /tmp/pm_prev.json && echo STABLE || { python3 build_thesis2.py >/dev/null 2>&1 && bash export_pdf.sh >/dev/null 2>&1; python3 pagemap.py; }
