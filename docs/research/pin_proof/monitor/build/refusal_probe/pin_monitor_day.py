#!/usr/bin/env python3
import pathlib,sys
pathlib.Path("MEASURED_MARKER").write_text("the reader ran with argv %s\n" % (sys.argv[1:],))
print("stub reader: ran")
