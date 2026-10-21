"""Start here:  python run.py list     |     python run.py demo     |     python run.py <script name>
(forwards to XY_Validation/run.py, where the scripts are)"""
import os
import runpy
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.argv[0] = os.path.join(HERE, 'XY_Validation', 'run.py')
runpy.run_path(sys.argv[0], run_name='__main__')
