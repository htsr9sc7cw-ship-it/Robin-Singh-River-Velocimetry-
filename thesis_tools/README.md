# Thesis tools

Scripts that recompute and check the numbers of the thesis from the stored result files.

| Script | Job |
|---|---|
| `recompute_headlines.py` | Recomputes the headline numbers of the thesis from the result tables with code independent of the table generator (80 checks). |
| `make_tables.py` | Builds the result tables of Chapter 5 and the appendix from the result files. |
| `verify_thesis.py` | Runs 20 consistency checks over the finished thesis (numbering, references, citations, numbers, figures, scripts). |
| `check_refs.py` | Checks that every section, table and figure reference in the text resolves. |

These tools were written for the project folder layout of the study and contain its paths; adapt the path constants at the top of each script to run them elsewhere.
