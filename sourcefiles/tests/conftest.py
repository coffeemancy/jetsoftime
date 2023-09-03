import sys

from pathlib import Path

# HACK: add sourcefiles to import search path
# In future, probably makes sense to convert repo to python package format
# and update ctjot_web_generator accordingly
sys.path.append(str(Path(__file__).parent.parent))
