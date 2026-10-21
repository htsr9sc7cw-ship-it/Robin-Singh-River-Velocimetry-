# Thesis build scripts

Scripts that assemble the thesis document from its chapter sources, format it, and check it. They are included for completeness and contain the paths of the original project folder.

| Script | Job |
|---|---|
| `build_thesis2.py` | Assembles the chapters, tables, figures and references and calls the formatter. |
| `format_thesis.py` | Formats the Word document: styles, equations, table layout, appendix page layout. |
| `assemble2.py`, `build_appendix.py`, `appendix_post.py`, `source_appendix.py`, `print_clean.py` | Assemble the appendix and the printed source code. |
| `omml.py` | Builds the native Word equations. |
| `pagemap.py`, `rebuild.sh`, `export_pdf.sh` | Page numbers for the contents and the two-pass build with PDF export. |
| `comment_scan.py`, `number_audit.py`, `preserve_check2.py`, `capkeys.py`, `secmap.py`, `renumber.py`, `regroup5.py` | Wording scan, number audit, and numbering helpers. |
