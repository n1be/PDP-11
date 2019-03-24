#!/usr/bin/python3
# -*- encoding: utf-8 -*-

"""Conversions between PDP-11 RAD50 and ASCII.
   Note that on 18/36 bit systems DEC used a different ordering of the
   characters in the RAD50 alphabet array."""

import io

alphabet = " ABCDEFGHIJKLMNOPQRSTUVWXYZ$.%0123456789"
radix = len( alphabet)
char_per_wd = 3

def decode_wd( buf, wd):
    "Convert 16 bit word to 3 ASCII characters, appended to the supplied buffer"
    divisor = radix * radix
    for i in range( char_per_wd):
        buf.write( alphabet[ wd // divisor % radix])
        divisor //= radix

def decode_words( iterable):
    "Convert sequence of words into a string"
    buf = io.StringIO()
    for wd in iterable:
        decode_wd( buf, wd)
    result = buf.getvalue()
    buf.close()
    return result

def encode_wd( chars):
    "Convert up to 3 chars into a rad50 word"
    result = 0
    for i in range( char_per_wd):
        result *= radix
        result += alphabet.casefold().index( chars[ i:i+1].casefold())
    return result

def encode_string( strng):
    "encode ASCII string into list of RAD50 words"
    result = []
    s = strng
    while s:
        result.append( encode_wd( s[ :3]))
        s = s[ 3:]
    return result

def test():
    print( repr( decode_words( [ 1683, 6606])))
    print( encode_string( 'abcdef '))

if __name__ == "__main__":
    test()

