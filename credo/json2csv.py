#!/usr/bin/env python3

import pandas as pd
import sys
import json

data = json.load(sys.stdin)
df = pd.DataFrame(data)
df.to_csv(sys.stdout, index=False)
