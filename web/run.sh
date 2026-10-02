#!/bin/sh
# Double-click (or ./run.sh from a terminal) to build and open the web version.
# Equivalent to: python3 web/serve.py
cd "$(dirname "$0")" || exit 1
python3 serve.py
# keep the window open if double-clicked and something went wrong
if [ $? -ne 0 ]; then
    printf '\nSomething went wrong (see above). Press Enter to close.'
    read -r _
fi
