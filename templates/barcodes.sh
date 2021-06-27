#!/bin/bash

# requires barcode
# Generate simple 1D barcodes for controlling scanner behavior.
# These could also be QR codes.

barcode -b "kommt"  -b "gast" -b "geht"  -b "band" -b "reserviert" -b "crew" \
	-o status.ps -t 2x3 -m 50x60

echo "Fertig"
