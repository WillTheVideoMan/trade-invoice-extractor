#!/usr/bin/env python
from PyPDF2 import PdfWriter, PdfReader
import argparse

argParser = argparse.ArgumentParser()

argParser.add_argument(
    "-i",
    "--input_pdf_path",
    type=str,
    required=True,
    help="The path of the PDF file to split",
)

args = argParser.parse_args()

inputpdf = PdfReader(open(args.input_pdf_path, "rb"))

for i in range(len(inputpdf.pages)):
    output = PdfWriter()
    output.add_page(inputpdf.pages[i])
    with open(f"{args.input_pdf_path}-{i}", "wb") as outputStream:
        output.write(outputStream)
