#!/usr/bin/env python
from PyPDF2 import PdfReader
from enum import Enum
import functools
import re
import datetime
import csv
import argparse

"""
Vendor

Hold vendor-specific information about how to find vendor invoice items and their respective names, units, and costs.

__init__: 
    name (Str): The plaintext name of the vendor.
    dateFormat (Str): A string representation of the vendor-specific date format e.g. DD-MM-YYYY
    itemRegex (Str): A regular expression to match with vendor-specific item codes.
    itemNameOffsetIndex (Int): The index offset from the end of a vendor invoice text line which marks the index of an item's name. 
    unitsOffsetIndex (Int): The index offset from the end of a vendor invoice text line which marks the index of the number of units purchashed for an item. 
    unitCostOffsetIndex (Int): The index offset from the end of a vendor invoice text line which marks the index of an item's unit cost. 

"""


class Vendor:
    def __init__(
        self,
        name,
        dateFormat,
        itemRegex,
        itemNameOffsetIndex,
        unitsOffsetIndex,
        unitCostOffsetIndex,
    ):
        self.name = name
        self.dateFormat = dateFormat
        self.itemRegex = itemRegex
        self.itemNameOffsetIndex = itemNameOffsetIndex
        self.unitsOffsetIndex = unitsOffsetIndex
        self.unitCostOffsetIndex = unitCostOffsetIndex

    def __str__(self):
        return f"{self.name}, {self.dateFormat}, {self.itemRegex}, {self.itemNameOffsetIndex}, {self.unitsOffsetIndex}, {self.unitCostOffsetIndex}"


"""
Item

Hold information about an item. 

__init__: 
    name (Str): The plaintext name of an item.
    units (Int): How many of an item have been purchased. 
    unitCost (Int): The cost of a single unit. 
"""


class Item:
    def __init__(self, name, units, unitCost):
        self.name = name
        self.units = int(units)
        self.unitCost = float(unitCost)

        """ The grand total for an item is it's unit cost multiplied by the number of units purchased. """
        self.total = self.units * self.unitCost

    def __str__(self):
        return f"{self.name}, {self.units}x, £{self.unitCost}, £{self.total}"


"""
Order

Given a spefic vendor and a path to a PDF file, extract and normalise a series of items and related metadata. 

__init__: 
    vendor (Vendor): The vendor which issued the order invoice. 
    pdfPath (Str): The path of the PDF file of an order invoice for a given vendor. 
"""


class Order:
    def __init__(self, vendor, pdfPath):
        self.date = None
        self.items = []
        self.textLines = []

        self.vendor = vendor
        self.pfdPath = pdfPath

        self.readPDF()

        self.extractDate()

        self.extractItems()

    def __str__(self):
        orderString = (
            f"Vendor: {self.vendor} \n\nDate: {self.date} \n\n--------------------\n\n"
        )

        for item in self.items:
            orderString += " - " + str(item) + "\n"

        return orderString

    """
    Given a PDF path, extract lines of text from a PDF and save to self.

    The function splits PDF file text by lines, as each item on an order invoice is usually stored in a table-like structure with one item 
    corresponding to one row. 

    TODO: Accept a wider format of PDF structures to ensure all items are captured from various vendors. 
    """

    def readPDF(self):
        reader = PdfReader(self.pfdPath)

        for i in range(len(reader.pages)):
            self.textLines += reader.pages[i].extract_text().splitlines()

    """
    Given a list of strings (lines from a PDF), use a regular expression to extract lines based on item codes. 

    Check to see that the match is a valid match that specific vendor. 

    Apply normalistation to the item values to give a regular shape to the Item object.

    Store a list of Items in self. 

    """

    def extractItems(self):
        for i in range(len(self.textLines)):
            match = re.search(self.vendor.itemRegex, self.textLines[i])

            if match:
                words = self.textLines[i].split(" ")

                """
                Read from the end of the array backwards, since we dont know how long
                the name of each item is, but we know the relative positions of all other item data
                """
                offsetStart = len(words) - 1

                if self.isValidItem(offsetStart):
                    name = " ".join(
                        words[1 : offsetStart + self.vendor.itemNameOffsetIndex]
                    )

                    units = words[offsetStart + self.vendor.unitsOffsetIndex]

                    unitCostParts = words[
                        offsetStart + self.vendor.unitCostOffsetIndex
                    ].split(".")

                    """Enforce a strict cost shape of *.00"""
                    if len(unitCostParts) > 1:
                        unitCost = unitCostParts[0] + "." + unitCostParts[1][0:2]

                        self.items.append(Item(name, units, unitCost))

    """
    Given a date format, extract and normalise the date of the order. 

    Any date format with D or DD, M or MM, and YY or YYYY is supported in any order. 
    
    '/', '-', or '.' delimiting characters is supported. 
    """

    def extractDate(self):
        dates = []
        yearPrefix = ""

        dateDelim = re.search("[\/\-\.]", self.vendor.dateFormat).group()

        """Transform the format string into a series of regex parts, then reduce to a single string"""
        regexParts = map(
            lambda char: "\d" if char != dateDelim else f"\{dateDelim}",
            self.vendor.dateFormat,
        )
        regex = functools.reduce(lambda s, c: s + c, regexParts)

        iD = self.vendor.dateFormat.find("D")
        iM = self.vendor.dateFormat.find("M")
        iY = self.vendor.dateFormat.find("Y")

        numD = len(self.vendor.dateFormat.split("D")) - 1
        numM = len(self.vendor.dateFormat.split("M")) - 1
        numY = len(self.vendor.dateFormat.split("Y")) - 1

        """If a YY only year is provided, add the start of the year back to get YYYY"""
        if numY == 2:
            yearPrefix = str(datetime.datetime.now().year)[0:2]

        """
        Generated an array of datetime objects based on a regex search for the given date format 
        for all lines
        """
        for line in self.textLines:
            dates += map(
                lambda d: datetime.datetime(
                    int(yearPrefix + d[iY : iY + numY]),
                    int(d[iM : iM + numM]),
                    int(d[iD : iD + numD]),
                ),
                re.findall(regex, line),
            )

        self.date = max(dates)

    """
    Use a vendor's specific PDF layout and the number of words in a matching PDF line to make a good-faith guess as to wether a 
    real item has been matched by the item regular expression. 

    Given we expect an extracted line to have a known number of words in a vendor-specific fashion, we can use the offset values to 
    attempt to verify the validity of the extracted line. 

    TODO: Update this function to give a more concrete check of validity. 
    """

    def isValidItem(self, offsetStart):
        if (offsetStart + self.vendor.itemNameOffsetIndex) < 0:
            return False

        if (offsetStart + self.vendor.itemNameOffsetIndex) > offsetStart:
            return False

        if (offsetStart + self.vendor.unitsOffsetIndex) < 0:
            return False

        if (offsetStart + self.vendor.unitsOffsetIndex) > offsetStart:
            return False

        if (offsetStart + self.vendor.unitCostOffsetIndex) < 0:
            return False

        if (offsetStart + self.vendor.unitCostOffsetIndex) > offsetStart:
            return False

        return True

    """
    Add extracted order items to a given CSV, appending to the file. 

    The format of each row is defined to allow copy-paste to a personal spreadsheet, but 
    the format can be easily adjusted to suit.

    """

    def appendItemsToCSV(self, csvPath):
        with open(csvPath, "a", newline="") as file:
            writer = csv.writer(file)

            for item in self.items:
                writer.writerow(
                    [
                        self.vendor.name,
                        "",
                        self.date.strftime("%d/%m/%Y"),
                        item.name,
                        item.units,
                        item.unitCost,
                    ]
                )


"""
VendorList (Enum)

A list of possible vendors accepted, and a Vendor definition for each. 
"""


class VendorList(Enum):
    SCREWFIX = Vendor(
        "Screwfix", "DD/MM/YYYY", "(?=^\d{3}.{2}\ )(?!.*03330 112 999)", -8, -8, -7
    )
    TOOLSTATION = Vendor(
        "Toolstation", "YYYY-MM-DD", "(?=^\d{5}\ )(?!.*00006)(?!.*00037)", -1, -1, 0
    )


"""
PDFFileType

Defines and enforces a .pdf file extension as an argument type. 
"""


def PDFFileType(v):
    if re.search("\.pdf$", v) is None:
        raise argparse.ArgumentTypeError(f"{v} must be a .pdf file.")

    return v


"""
CSVFileType

Defines and enforces a .csv file extension as an argument type.
"""


def CSVFileType(v):
    if re.search("\.csv$", v) is None:
        raise argparse.ArgumentTypeError(f"{v} must be a .csv file.")

    return v


"""
Main - trade-invoice-extractor.py

Define and parse a vendor, input_pdf, and output_csv arguments. 

Then, for the given vendor, instantiate a new Order from the provided PDF and append the 
Order to a CSV file.

"""

argParser = argparse.ArgumentParser()

argParser.add_argument(
    "-v",
    "--vendor",
    type=str,
    required=True,
    choices=["SCREWFIX", "TOOLSTATION"],
    help="The vendor of the invoice. Defines the search and structure of the item extraction.",
)

argParser.add_argument(
    "-i",
    "--input_pdf",
    type=PDFFileType,
    required=True,
    help="The path to the input PDF file.",
)

argParser.add_argument(
    "-o",
    "--output_csv",
    type=CSVFileType,
    required=True,
    help="The path to the output CSV file",
)

args = argParser.parse_args()

vendor = VendorList[args.vendor].value

order = Order(vendor, args.input_pdf)

order.appendItemsToCSV(args.output_csv)
