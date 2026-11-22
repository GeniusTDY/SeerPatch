import struct, os

SRC = '/workspace/work/pd/lib/arm64-v8a/libil2cpp.so'
OUT = '/workspace/work/pd/patched/libil2cpp.so'
os.makedirs(os.path.dirname(OUT), exist_ok=True)

ENC_ENTRY = 0x16F8EC0   # GameDataManager.EncryptString
DEC_ENTRY = 0x16F8FE8   # GameDataManager.DecryptString
RESUME    = 0x16F8FEC   # DecryptString + 4

STUB_VA   = 0x3820000   # first free 0x4000 page after .bss end (0x38165e0)
STUB_OFF  = 0x3600000   # page-aligned, past original EOF
FILE_VA_DELTA = 0x4000  # VA = file offset + 0x4000 for exec segment


def enc_b(pc, tgt):
    imm = (tgt - pc) >> 2
    assert -0x2000000 <= imm < 0x2000000
    return 0x14000000 | (imm & 0x3FFFFFF)


def enc_cbz_x(pc, tgt, rt=1):
    imm = (tgt - pc) >> 2
    return 0xB4000000 | ((imm & 0x7FFFF) << 5) | rt


def enc_cbz_w(pc, tgt, rt=9):
    imm = (tgt - pc) >> 2
    return 0x34000000 | ((imm & 0x7FFFF) << 5) | rt


def enc_bne(pc, tgt):
    imm = (tgt - pc) >> 2
    return 0x54000000 | ((imm & 0x7FFFF) << 5) | 1


FB = STUB_VA + 32
stub = [
    enc_cbz_x(STUB_VA + 0, FB),    # cbz  x1, fallback
    0xB9401029,                    # ldr  w9, [x1, #0x10]  (string length)
    enc_cbz_w(STUB_VA + 8, FB),    # cbz  w9, fallback
    0x79402828,                    # ldrh w8, [x1, #0x14]  (first char)
    0x7101ED08,                    # cmp  w8, #0x7b '{'
    enc_bne(STUB_VA + 20, FB),     # b.ne fallback
    0xAA0103E0,                    # mov  x0, x1
    0xD65F03C0,                    # ret
    0xF81D0FFE,                    # str  x30, [sp, #-0x30]!
    enc_b(STUB_VA + 36, RESUME),   # b    DecryptString+4
]
assert len(stub) == 10
code = struct.pack('<10I', *stub) + b'\x00' * (0x40 - 40)

d = bytearray(open(SRC, 'rb').read())

# EncryptString -> return plainText unchanged
off_enc = ENC_ENTRY - FILE_VA_DELTA
d[off_enc:off_enc + 8] = struct.pack('<2I', 0xAA0103E0, 0xD65F03C0)

# DecryptString -> branch to stub
off_dec = DEC_ENTRY - FILE_VA_DELTA
d[off_dec:off_dec + 4] = struct.pack('<I', enc_b(DEC_ENTRY, STUB_VA))

# append stub at page aligned offset
if len(d) < STUB_OFF:
    d += b'\x00' * (STUB_OFF - len(d))
d += code

# replace program header #9 (PT_NOTE / build-id) with a new executable PT_LOAD
PHDR_OFF = 0x40
IDX = 9
ph = PHDR_OFF + IDX * 56
p_type, p_flags, p_offset, p_vaddr, p_paddr, p_filesz, p_memsz, p_align = struct.unpack_from('<IIQQQQQQ', d, ph)
assert p_type == 4, ('expected PT_NOTE, got', p_type)
struct.pack_into('<IIQQQQQQ', d, ph,
                 1,                     # PT_LOAD
                 5,                     # R | X
                 STUB_OFF,
                 STUB_VA,
                 STUB_VA,
                 len(code),
                 len(code),
                 0x4000)

open(OUT, 'wb').write(d)
print('entry patches:', hex(off_enc), hex(off_dec))
print('stub appended:', len(code), 'bytes at', hex(STUB_OFF), '->', hex(STUB_VA))
print('size', len(d), '(orig', os.path.getsize(SRC), ')')
