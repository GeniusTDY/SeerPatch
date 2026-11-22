#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""反汇编 FightAnimTrimApplier 的关键方法（ARM64）。"""
import sys, struct
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_ARM

SO = '/workspace/work/apkx/libil2cpp.so'
data = open(SO, 'rb').read()
assert data[:4] == b'\x7fELF'
is64 = data[4] == 2
e_phoff = struct.unpack_from('<Q', data, 0x20)[0]
e_phentsize = struct.unpack_from('<H', data, 0x36)[0]
e_phnum = struct.unpack_from('<H', data, 0x38)[0]
segs = []
for i in range(e_phnum):
    o = e_phoff + i * e_phentsize
    p_type = struct.unpack_from('<I', data, o)[0]
    if p_type != 1:
        continue
    p_offset, p_vaddr, p_paddr, p_filesz = struct.unpack_from('<QQQQ', data, o + 8)
    segs.append((p_vaddr, p_offset, p_filesz))
print('LOAD segments', [(hex(a), hex(b), hex(c)) for a, b, c in segs])


def f2v(vaddr):
    for va, off, sz in segs:
        if va <= vaddr < va + sz:
            return off + (vaddr - va)
    raise KeyError(hex(vaddr))


RVA = {
    'Awake': 0x160F88C,
    'SetBaseAnchoredPosition': 0x160F9C0,
    'ClearTrimData': 0x160FC2C,
    'SetAnimKey': 0x160FC5C,
    'LateUpdate': 0x1610858,
    'ApplyCurrent': 0x160F9D0,
    'GetSourcePixelsPerUIUnit': 0x16102E0,
    'GetOffsetPivotCenter': 0x16109E8,
    'GetOffsetForPivot': 0x161035C,
}
md = Cs(CS_ARCH_ARM64, CS_MODE_ARM)
md.detail = True
which = sys.argv[1:] or list(RVA)
for name in which:
    rva = RVA[name]
    off = f2v(rva)
    print('\n===== %s @ RVA %s file %s' % (name, hex(rva), hex(off)))
    n = 0
    for ins in md.disasm(data[off:off + 900], rva):
        print('  %08x  %-8s %s' % (ins.address, ins.mnemonic, ins.op_str))
        n += 1
        if ins.mnemonic == 'ret' and n > 4:
            break
        if n > 150:
            print('  ...')
            break
