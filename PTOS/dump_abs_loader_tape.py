#!/usr/bin/python3
# -*- encoding: utf-8 -*-
"""Print to stdout the contents of a papertape in absolute loader format.
This format consists of variable length records composed of bytes as follows.
  1     Record Header
  0     (Ignored by absolute loader)
  low   Record Length
  high     "     "
  low   Address
  high     "
  ???   (<Record Length> - 6) Data Bytes
  sum   Checksum byte (not part of record length)

The absolute loader verifies the checksum of every record, halting at xxx610
if the 8-bit sum of all the bytes in the record is non-zero.

The Record Length field does not count the checksum byte.  When the Record
Length is greater than 6, the absolute loader will load the Data Bytes into
memory starting at the Address in the record (plus an optional relocation
factor).

The last record has a length == 6.  If the Address in that record is even,
the absolute loader jumps to that address (plus optional relocation factor);
otherwise the absolute loader halts at xxx710.
"""
import sys

verbose = False

ASCII = ("." * 32) + " !\"#$%&'()*+,-./0123456789:;<=>?" + \
        "@ABCSEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`abcdefghijklmnopqrstuvwxyz{|}~." + \
        ( "." * 128)

class Dump_Absolute_Loader_File():
    def __init__(self, infile):
        self._infile = infile
        self._address = 0
        self._record_length = 0
        self._record_number = 0
        self._sum = 0
        self._vm = {}

    def read_frame(self):
        "read one byte from the input tape"
        try:
            frame = self._infile.read(1)[0]   # zero length at EOF
        except IndexError:
            raise EOFError("Reading PT beyond EOF")
        self._sum += frame
        self._record_length -= 1
        # debug print( f"{self._record_length}, frame= {frame:02X}
        # debug         sum= {self._sum:02X}")
        return frame

    def read_word(self):
        "read one 16-bit word from the input tape"
        return self.read_frame() + 256 * self.read_frame()

    def dump_rec(self):
        "read  & process a record, return bool whether to continue"
        self._record_number += 1
        frame = 0
        while frame != 1:
            self._sum = 0
            frame = self.read_frame()
        frame = self.read_frame() # ignored
        self._record_length = self.read_word() - 4
        old_addr = self._address
        self._address = self.read_word()
        if verbose and self._address != old_addr:
            print(" --- Address discontinuity")
        next_addr = self._address + self._record_length
        if verbose:
            print("Record {: 3d}:  Address {:06o}; Data Len={:06o}  Next:{:06o}".
                format(self._record_number, self._address, self._record_length,
                        next_addr))
        if self._record_length == 0:
            self.read_frame()
            if self._sum & 0xFF:
                print("*** CHECKSUM ERROR")
            elif self._address & 1:
                print("Odd Transfer Address - Loader would halt")
            else:
                print(f"Jump to Transfer Address: {self._address:06o}")
        else:
            for indx in range( self._record_length):
                self._vm[self._address] = self.read_frame()
                self._address += 1
            self.read_frame()
            if self._sum & 0xFF:
                print("*** CHECKSUM ERROR")
            else:
                return True
        return False

    def print_range(self,low,high):
        print(f"\nContiguous addr range {low:06o} thru {high:06o}")
        bpl = 16 # bytes per line
        for addr in range( low - low % bpl, high, bpl):
            lb = "" # octal words
            lt = "" # ASCII chars
            for offset in range(0, bpl, 2):
                try:
                    wd = self._vm[addr + offset]
                except KeyError:
                    wd = None
                try:
                    high_bits = self._vm[addr + offset + 1] << 8
                    wd += high_bits
                except KeyError:
                    pass
                except TypeError:
                    wd = high_bits
                if wd is None:
                    lb += "       "
                    lt += "  "
                else:
                    lb += f" {wd:06o}"
                    lt += ASCII[ wd & 0xFF] + ASCII [ wd >> 8 ]
            print(f"{addr:06o}:{lb} {lt}")

    def dump_tape(self):
        while self.dump_rec():
            pass
        if len(self._vm) > 0:
            prev_addr = None
            for addr in sorted(self._vm):
                if prev_addr is None:
                    # starting the first contiguous range of addresses
                    low_addr = prev_addr = addr
                elif prev_addr + 1 == addr:
                    # continuing within a contiguous range of addresses
                    prev_addr = addr
                else:
                    # finish one range and start the next
                    self.print_range(low_addr, prev_addr)
                    low_addr = prev_addr = addr
            self.print_range(low_addr, prev_addr)

def main( argv):
    "Process multiple files"
    if len( argv) < 2:
        print( f"  Usage: {argv[0]} <virtual_tape_file> ...\n")
        return "Virtual paper tape files must be provided on the command line."
    for virtual_file in argv[1:]:
        print(f"\nFile: {virtual_file}")
        with open(virtual_file, "rb") as f:
            try:
                Dump_Absolute_Loader_File(f).dump_tape()
            except EOFError:
                pass

if __name__ == "__main__":
    # execute only if run as a script
    try:
        rc = main(sys.argv)
    except BrokenPipeError:
        rc = 0
    sys.exit( rc)

