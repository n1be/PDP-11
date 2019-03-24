#!/usr/bin/python3
# -*- encoding: utf-8 -*-

"""Decoding various ODS-1 data fields to ASCII for humans"""

import io

# ODS-1 File Header bits

# file protection bits = 1 to deny access:
FP_RDV = 0o01 # FP.RDV - deny Read
FP_WRV = 0o02 # FP.WRV - deny Write
FP_EXT = 0o04 # FP.EXT - deny Extend
FP_DEL = 0o10 # FP.DEL - deny Delete
# File Accessor class:
FP_Accessors = (
                'S',  # System: bits 0-3
                'O',  # Owner:  bits 4-7
                'G',  # Group:  bits 8-11
                'W',  # World   bits 12-15
                )

# User Controlled file characteristics in H.UCHA
UC_DLK = 0o100 # UC.DLK Deaccess Locked
UC_CON = 0o200 # UC.CON Contiguous

# System Controlled file characteristics in H.SCHA
SC_BAD = 0o100 # SC.BAD Set if file contains bad blocks.
SC_MDL = 0o200 # SC.MDL Set if the file is marked for delete.

# Record Types
R_FIX = 1
R_VAR = 2
R_SEQ = 3

# Record Attributes
FD_FTN = 0o01
FD_CR  = 0o02
FD_PRN = 0o04
FD_BLK = 0o10

def fmt_char( fh):
    "format file characteristics in a file header"
    result = ''
    if fh.UCHA & UC_CON:
        result += 'C'
    if fh.UCHA & UC_DLK:
        result += 'L'
    if fh.SCHA & SC_MDL:
        result += 'D'
    if fh.SCHA & SC_BAD:
        result += 'B'
    return result

def fmt_datim( fh):
    "format last modification date/time in a file header"
    if fh.RVDT.strip():
        # use the last revision date/time if any is present
        dat = fh.RVDT
        tim = fh.RVTI
    else:
        # use the creation date/time
        dat = fh.CRDT
        tim = fh.CRTI
    return '{}-{}-{}'.format(
        dat[:2], dat[2:5], dat[5:])
#   return '{}-{}-{} {}:{}:{}'.format(
#       dat[:2], dat[2:5], dat[5:], tim[:2], tim[ 2:4], tim[4:])

def fmt_protection( wd):
    "format SOGW protection from given word"
    buf = io.StringIO()
    w = wd
    for accessor in FP_Accessors:  #'System', 'Owner', 'Group', 'World'
        if not w & FP_RDV:
            buf.write( 'R')
        if not w & FP_WRV:
            buf.write( 'W')
        if not w & FP_EXT:
            buf.write( 'E')
        if not w & FP_DEL:
            buf.write( 'D')
        w >>= 4
        buf.write( ',')
    result = buf.getvalue()[ :-1]
    buf.close()
    return result

def fmt_ratt( fh):
    "format the record attributes from beginning of fh.UFAT"
    RTYP = fh.UFAT[ 0]
    RATT = fh.UFAT[ 1]
    RSIZ = fh.UFAT[ 2] + 256 * fh.UFAT[ 3]
    try:
        result = { R_FIX:'Fix', R_VAR:'Var', R_SEQ:'Seq'}[ RTYP]
    except:
        result = '???'
    if RATT & FD_FTN:
        result += ',FTN'
    if RATT & FD_CR:
        result += ',CR'
    if RATT & FD_PRN:
        result += ',PRN'
    if RATT & FD_BLK:
        result += ',BLK'
    result += '({}.)'.format( RSIZ)
    return result

def fmt_uic( fh):
    "format the UIC within a file header"
    return '[{PROJ:03o},{PROG:03o}]'.format( **fh.__dict__)

