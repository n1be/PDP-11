#!/usr/bin/python3
# -*- encoding: utf-8 -*-
"List all the files in an ODS-1 disk"

import copy, hashlib, io, sys
import rad50
from ods1_fields import fmt_char, fmt_datim, fmt_protection, fmt_ratt, fmt_uic

_debug = False

# Block IO between a disk image file and a user's buffer
Block_SZ = 512 # length of a disk block in bytes

def dump_buf( nam, buf):
    "Print out buffer content for diagnostic purposes"
    if not _debug:
        return
    print( "\nDUMP of buffer", nam)
    off = 0
    while off < len( buf):
        if buf[ off] or buf[ off + 1] or buf[ off + 2] or buf[ off + 3]:
          print( ("{0:03o}:  {1:03o}={1:03d}., {2:03o}={2:03d}. {3:06o}={3:06d}.;  "
              + "{4:03o}={4:03d}., {5:03o}={5:03d}. {6:06o}={6:06d}.").format(
                off, buf[ off], buf[ off + 1], buf[ off] + 256 * buf[ off + 1],
                buf[ off + 2], buf[ off + 3], buf[ off + 2] + 256 * buf[ off + 3]))
        off += 4

def dump_object( obj):
    "Print out the attributes of an object for diagnostic purposes"
    for ident in obj.__dict__:
        if not ident.startswith( '__'):
            print( '{}: {}'.format( ident, obj.__dict__[ ident]))

def read_lbn( f, lbn):
    "Read the selected logical block from an opened virtual disk file"
    f.seek( Block_SZ * lbn)
    buf = f.read( Block_SZ)
    if( len(buf) != Block_SZ):
        raise OSError( "Incomplete block: read {} bytes of LBN {}".format( len(buf), lbn))
    return buf

def checksum( buf, offset):
    "Validate checksum of the words in the buffer"
    csum = 0
    for i in range( 0, offset, 2):
        csum = ( csum + w2( buf[ i:]))
    csum &= 0x0FFFF
    if csum != w2( buf[ offset:]):
        raise( Invalid_Block( "Not a valid home block - checksum"))
    return csum

def w2( buf):
    "extract a word of 2 bytes from beginning of the buf"
    return buf[ 0] + ( buf[ 1] << 8)

def w4( buf):
    "extract a double word from High, Low words at the start of buf"
    return ( w2( buf) << 16) + w2( buf[ 2:])

def wstr( buf, maxlen):
    "extract null terminated string from the buffer, convert to ASCII char string"
    tmp = buf[ : maxlen]
    end = tmp.find( b'\x00')
    if end >= 0:
        tmp = tmp[ : end]
    return tmp.decode( encoding='ascii')
 
class Invalid_Block( ValueError):
    pass

class Home_Block:
    "Home Block"
    def __init__( self, f):
        "Read the home block on this volume"
        self.f = f
        self.lbn = 1
        mult = 0
        while True:
            buf = read_lbn( self.f, self.lbn)
            try:
                self.get_hb( buf)
                return
            except Invalid_Block:
                # Retry with next alternate home block
                mult += 1
                self.lbn = 256 * mult

    def get_hb( self, buf):
        "Populate self with home block info"
        offset = 0
        # number of blocks in the index file bitmap
        self.IBSZ = w2( buf[ offset:]); offset += 2
        # Index File Bitmap LBN  - high, low word
        self.IBLB = w4( buf[ offset:]); offset += 4
        # Maximum Number of Files 
        self.FMAX = w2( buf[ offset:]); offset += 2
        # Storage Bitmap Cluster Factor - Not implemented in ODS-1; must = 1
        self.SBCL = w2( buf[ offset:]); offset += 2
        # Disk Device Type - not used; always contains 0
        self.DVTY = w2( buf[ offset:]); offset += 2
        # Volume Structure Level - 
        self.VLEV = w2( buf[ offset:]); offset += 2
        # Volume Name - 12 ASCII bytes with null padding
        self.VNAM = wstr( buf[ offset:], 12); offset += 12
        # 4 bytes Unused
        offset += 4
        # Volume Owner UIC - Programmer (Member), Project (Group)
        self.VOWN = w2( buf[ offset:]); offset += 2
        self.PROG = self.VOWN & 0xFF
        self.PROJ = self.VOWN >> 8
        # Volume Protection Code
        self.VPRO = w2( buf[ offset:]); offset += 2
        self.VPRO_STR = fmt_protection( self.VPRO)
        # Volume Characteristics
        self.VCHA = w2( buf[ offset:]); offset += 2
        # Default File Protection
        self.DFPR = w2( buf[ offset:]); offset += 2
        self.DFPR_STR = fmt_protection( self.DFPR)
        # 6 bytes Unused
        offset += 6
        # Default Window Size in retrieval pointers
        self.WISZ = buf[ offset]; offset += 1
        # Default File Extend in blocks
        self.FIEX = buf[ offset]; offset += 1
        # Directory Pre-Access Limit
        self.LRUC = buf[ offset]; offset += 1
        # Date of Last Home Block Revision - ASCII: DDMMMYY
        self.REVD = buf[ offset: offset + 7].decode( encoding='ascii'); offset += 7
        # Count of Home Block Revisions
        self.REVC = w2( buf[ offset:]); offset += 2
        # 2 bytes Unused
        offset += 2
        # First Checksum (of all preceding words)
        self.CHK1 = checksum( buf, offset); offset += 2
        # Volume Creation Date - 14 ASCII bytes "DDMMMYYHHMMSS" null padded
        self.VDAT = wstr( buf[ offset:], 14); offset += 14
        # 382 bytes Unused
        offset += 382
        # Pack Serial Number - manufacturer supplied
        self.PKSR = w4( buf[ offset:]); offset += 4
        # 12 bytes Unused
        offset += 12
        # Volume Name (Identity) - 12 ASCII bytes, space padded
        self.INDN = wstr( buf[ offset:], 12); offset += 12
        # Volume Owner (Name) - 12 ASCII bytes, space padded
        self.INDO = wstr( buf[ offset:], 12); offset += 12
        # Format Type - 12 ASCII bytes, space padded
        self.INDF = wstr( buf[ offset:], 12); offset += 12
        # 2 bytes Unused
        offset += 2
        # Second Checksum (of all preceding words)
        self.CHK2 = checksum( buf, offset); offset += 2
 
        # Home block validation
        if self.IBSZ == 0 or \
           self.IBLB == 0 or \
           self.FMAX == 0 or \
           self.SBCL != 1 or \
           self.DVTY != 0 or \
           ( self.VLEV != 0o401 and self.VLEV != 0o402):
            raise( Invalid_Block( "Not a valid home block"))

    def __str__( self):
        "Provide a string representation of this object"
        if _debug:
            fmt= '''Home Block: "{INDF}"  Pack_ID="{INDN}" Owner="{INDO}"
Home_LBN={lbn} Vol_Name={VNAM} UIC=[{PROJ:o},{PROG:o}] Max_Files={FMAX}. Struct=0o{VLEV:o}
Vol_SerNo=0x{PKSR:X} Vol_Char=0x{VCHA:X} Vol_Prot={VPRO_STR}
Create_Date={VDAT} Rev_Cnt={REVC} Revision_Date={REVD}
Defaults: LRU={LRUC} EXT={FIEX} WIN={WISZ} F_Prot={DFPR_STR}'''
        else:
            fmt = "Volume={VNAM} UIC=[{PROJ:o},{PROG:o}] Max_Files={FMAX}."
        return fmt.format( **self.__dict__)

class File_Header:
    "File Header"

    def __init__( self, buf):
        "Populate self with file header info"
        dump_buf( 'fh', buf)
        offset = 0
        # Ident Area Offset in 16-bit words
        self.IDOF = buf[ offset]; offset += 1
        # Map Area Offset in 16-bit words
        self.MPOF = buf[ offset]; offset += 1
        # File Number
        self.FNUM = w2( buf[ offset:]); offset += 2
        # File Sequence Number
        self.FSEQ = w2( buf[ offset:]); offset += 2
        # File Structure Level
        self.FLEV = w2( buf[ offset:]); offset += 2
        if self.FLEV != 0o401:
            raise( Invalid_Block( "Not a valid file header FLEV"))
        # File Owner UIC - Programmer (Member), Project (Group)
        self.FOWN = w2( buf[ offset:]); offset += 2
        self.PROG = self.FOWN & 0xFF
        self.PROJ = self.FOWN >> 8
        # File Protection Code
        self.FPRO = w2( buf[ offset:]); offset += 2
        self.FPRO_STR = fmt_protection( self.FPRO)
        # File Characteristics - 2 bytes
        # User Controlled Characteristics
        self.UCHA = buf[ offset]; offset += 1
        # System Controlled Characteristics
        self.SCHA = buf[ offset]; offset += 1
        # User Attribute Area - 32 bytes
        self.UFAT = buf[ offset: offset + 32]; offset += 32

        # get FCS attributes
        offset = 0
        # Record Type
        self.RTYP = self.UFAT[ offset]; offset += 1
        # Record Attributes
        self.RATT = self.UFAT[ offset]; offset += 1
        # Record Size
        self.RSIZ = w2( self.UFAT[ offset:]); offset += 2
        # Highest VBN Allocated
        self.HIBK = w4( self.UFAT[ offset:]); offset += 4
        # End of File Block
        self.EFBK = w4( self.UFAT[ offset:]); offset += 4
        # First Free Byte
        self.FFBY = w2( self.UFAT[ offset:]); offset += 2

        # 3.4.1.10  S.HDHD  46 bytes  Size of Header Area  - 
        # 3.4.2  Ident Area Description  - 
        offset = 2 * self.IDOF
        # File Name
        self.FNAM = rad50.decode_words( [
            w2( buf[ offset:]), w2( buf[ offset + 2:]), w2( buf[ offset + 4:])])
        offset += 6
        # File Type
        self.FTYP = rad50.decode_words( [ w2( buf[ offset:])]); offset += 2
        # Version Number
        self.FVER = w2( buf[ offset:]); offset += 2
        # Revision Number
        self.RVNO = w2( buf[ offset:]); offset += 2
        # Revision Date - 7 ASCII bytes
        self.RVDT = wstr( buf[ offset:], 7); offset += 7
        # Revision Time - 6 ASCII bytes
        self.RVTI = wstr( buf[ offset:], 6); offset += 6
        # Creation Date - 7 ASCII bytes
        self.CRDT = wstr( buf[ offset:], 7); offset += 7
        # Creation Time - 6 ASCII bytes
        self.CRTI = wstr( buf[ offset:], 6); offset += 6
        # Expiration Date - 7 ASCII bytes
        self.EXDT = wstr( buf[ offset:], 7); offset += 7
        # Unused 1 byte
        offset += 1

        # 3.4.2.11  S.IDHD  46 bytes  Size of Ident Area
        # 3.4.3  Map Area -
        offset = 2 * self.MPOF
        # Extension Segment Number
        self.ESQN = buf[ offset]; offset += 1
        # Extension Relative Volume Number
        self.ERVN = buf[ offset]; offset += 1
        # Extension File Number
        self.EFNU = w2( buf[ offset:]); offset += 2
        # Extension File Sequence Number
        self.EFSQ = w2( buf[ offset:]); offset += 2
        # Block Count Field Size
        self.CTSZ = buf[ offset]; offset += 1
        # LBN Field Size
        self.LBSZ = buf[ offset]; offset += 1
        if ( self.CTSZ + self.LBSZ) & 1:
            raise( Invalid_Block( "Not a valid file header CTSZ+LBSZ"))
        # Map Words in Use
        self.USE = buf[ offset]; offset += 1
        # Map Words Available
        self.MAX = buf[ offset]; offset += 1
        assert self.MAX == ( Block_SZ - ( offset + 2)) / 2
        assert self.USE <= self.MAX and self.USE >= 0

        # 3.4.3.9  M.RTRV  Retrieval Pointers  -
        assert self.CTSZ == 1 and self.LBSZ == 3
        self.RTRV = []
        i = self.USE
        while i > 0:
            lbn = buf[ offset]; offset += 1
            cnt = buf[ offset]; offset += 1
            lbn = ( lbn << 16) + w2( buf[ offset:]); offset += 2
            i -= 2
            self.RTRV.extend( [ ( cnt + 1, lbn)])
        assert i == 0
        assert offset <= Block_SZ - 2

        # End Checksum
        offset = Block_SZ - 2
        self.CKSM = checksum( buf, offset); offset += 2

        if _debug:
            #dump_object( self)
            print( ' ', self)

    def __str__( self):
        "Provide a string representation of this object"
        return '''FH[{FNUM},{FSEQ}]({ESQN}) {FNAM}.{FTYP};{FVER} UIC=[{PROJ:o},{PROG:o}] FProt={FPRO_STR}
Record: TYP={RTYP} ATTR={RATT} Size={RSIZ} Highest_VBN={HIBK} EOF_VBN={EFBK} FFBY={FFBY}
Created: {CRDT} {CRTI}   Revised: {RVDT} {RVTI}   Expires: {EXDT}
Ret_Ptrs: {RTRV}'''.format( **self.__dict__)

class Index_File:
    "Index file contains all the file headers on this disk"

    def __init__( self, hb):
        "Populate self from home block on this disk"
        self.f = hb.f
        self.fh_base_vbn = 2 + hb.IBSZ # VBN for file header [0,0]
        # Get first header for index file
        h = File_Header( read_lbn( self.f, hb.IBLB + hb.IBSZ))
        assert h.FNUM == 1
        self.RTRV = h.RTRV # Retrieval Pointers
        # get any additional headers
        while h.EFNU != 0:
            h = self.fh( h.EFNU)
            self.RTRV.append( h.RTRV)

    def fh_lbn( self, fileno):
        "Get LBN of the file header for a given file number"
        vbn = fileno + self.fh_base_vbn
        ret_ptrs = copy.copy( self.RTRV)
        cnt, lbn = ret_ptrs.pop(0)
        while vbn > cnt:
            vbn -= cnt
            cnt, lbn = ret_ptrs.pop(0)
        return lbn + vbn - 1

    def fh( self, fileno):
        "Get file header for a given file number"
        h = File_Header( read_lbn( self.f, self.fh_lbn( fileno)))
        assert h.FNUM == fileno
        return h

class File:
    "A file including the data from all extension headers"

    def __init__( self, idxf, fileno):
        "populate self from given file number of the index file"
        self.f = idxf.f
        self.fh = idxf.fh( fileno)
        self.RTRV = self.fh.RTRV # Retrieval Pointers
        efnu = self.fh.EFNU
        # get any additional headers and retrieval pointers
        while efnu != 0:
            h = idxf.fh( h.EFNU)
            self.RTRV.append( h.RTRV)
            efnu = h.EFNU
            # verify attributes of extension header
            for id in ( 'CRDT', 'CRTI', 'EFBK', 'EXDT', 'UCHA', 'SCHA', 'FFBY',
                        'FLEV', 'FNAM', 'FNUM', 'FOWN', 'FPRO', 'FSEQ', 'FTYP',
                        'FVER', 'HIBK', 'PROG', 'PROJ', 'RATT', 'RSIZ', 'RTYP',
                        'RVDT', 'RVNO', 'RVTI', 'UFAT'):
                assert self.fh.__dict__[ id] == h.__dict__[ id]

    def is_dir( self):
        "Predicate indicating whether this file is a directory"
        return self.fh.FTYP == 'DIR' and self.fh.FVER == 1

    def read_vb( self, vbn):
        "Return a buffer containing the selected VBN of this file"
        ret_ptrs = copy.copy( self.RTRV)
        cnt, lbn = ret_ptrs.pop(0)
        while vbn > cnt:
            vbn -= cnt
            cnt, lbn = ret_ptrs.pop(0)
        return( read_lbn( self.f, lbn + vbn - 1))

    def enumerate_dirent( self):
        "Iterator to enumerate all the directory entries in this file"
        try:
            assert self.is_dir()
        except:
            dump_object( self)
            dump_object( self.fh)
        last_vbn_used = self.fh.EFBK
        if self.fh.FFBY == 0:
            last_vbn_used -= 1
        for vbn in range( 1, last_vbn_used + 1):
            vb = self.read_vb( vbn)
            for offset in range( 0, Block_SZ, self.fh.RSIZ):
                if vbn == self.fh.EFBK and offset >= self.fh.FFBY:
                    break
                de = Dir_Ent( vb[ offset: ])
                if de.is_valid():
                    yield de

    def data_hash( self):
        "SHA sum all the data in this file"
        length = 0
        m = hashlib.sha256()
        last_vbn_used = self.fh.EFBK
        if self.fh.FFBY == 0:
            last_vbn_used -= 1
        for vbn in range( 1, last_vbn_used + 1):
            vb = self.read_vb( vbn)
            if vbn == self.fh.EFBK:
                vb = vb[ : self.fh.FFBY]
                length += self.fh.FFBY
            else:
                length += Block_SZ
            m.update( vb)
        return length, m.hexdigest()

class Dir_Ent:
    "A Directory Entry"

    def __init__( self, buf):
        "populate self from a buffer"
        offset = 0
        # File Number
        self.FNUM = w2( buf[ offset:]); offset += 2
        # File Sequence Number
        self.FSEQ = w2( buf[ offset:]); offset += 2
        # File Relative Volume Number
        self.FRVN = w2( buf[ offset:]); offset += 2
        # File Name
        self.FNAM = rad50.decode_words( [
            w2( buf[ offset:]), w2( buf[ offset + 2:]), w2( buf[ offset + 4:])])
        offset += 6
        # File Type
        self.FTYP = rad50.decode_words( [ w2( buf[ offset:])]); offset += 2
        # Version Number
        self.FVER = w2( buf[ offset:]); offset += 2

    def is_valid( self):
        "Predicate indicating whether this is a valid directory entry"
        return self.FNUM != 0

    def __str__( self):
        "Provide a string representation of this object"
        nte = "{}.{};{}".format( self.FNAM.strip(), self.FTYP.strip(), self.FVER)
        if _debug:
            return "{:19} {:>5},{:<5}".format( nte, self.FNUM, self.FSEQ)
        else:
            return "{:19}".format( nte)

def recursive_listing( idxf, dir_name='000000', file_num=4):
    "Recursively list all files on this disk below the given directory"
    d = File( idxf, file_num)
    for de in d.enumerate_dirent():
        f = File( idxf, de.FNUM)
        l, h = f.data_hash()
        print( '[{}]{} {} {:19} {:4} {} {} {}. {}'.format( dir_name, de, fmt_uic( f.fh), fmt_protection( f.fh.FPRO), fmt_char( f.fh), fmt_ratt( f.fh), fmt_datim( f.fh), l, h))
        if f.is_dir() and de.FNUM != file_num: # NOTE: MFD appears in the MFD
            # List contents of this UFD
            recursive_listing( idxf, de.FNAM.strip(), de.FNUM)

def list_disk( filepath):
    "List contents of the virtual disk in the specified file path"
    with open( filepath, 'rb') as f:
        hb = Home_Block( f)
        print( '\nFile:', filepath, hb)
        recursive_listing( Index_File( hb))

def main( args=sys.argv[ 1:]):
    "List contents of the given virtual disk files"
    if len( args) < 1:
        print( "  Usage: ods1_lister.py <virtual_disk_file> ...")
        return "Virtual disk files must be provided on the command line."
    for virtual_disk_file in args:
        list_disk( virtual_disk_file)

if __name__ == "__main__":
    # execute only if run as a script
    sys.exit( main())

