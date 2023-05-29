#!/bin/bash

###
#
# Bash Batch Processing script for item extraction
#
# Usage: ./process-batch.sh DIR VENDOR_STRING CSV_PATH
#
###

echo ""
echo "Batch Processing PDF invoices using $2 vendor profile."
echo ""
echo ""

cd $1

files=$(ls | grep .pdf)

for file in $files
do
	echo "Extracting $file items to $3"
	trade-invoice-extractor.py -v $2 -i $file -o ../CSV/$3
done
