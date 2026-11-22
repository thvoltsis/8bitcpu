import random
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles

# Opcodes της CPU
OP_CLR   = 0b0000
OP_ADD   = 0b0001
OP_SUB   = 0b0010
OP_INC   = 0b0011
OP_DEC   = 0b0100
OP_LOAD  = 0b0101
OP_STORE = 0b0110
OP_AND   = 0b0111
OP_OR    = 0b1000
OP_XOR   = 0b1001
OP_NOT   = 0b1010
OP_SHL   = 0b1011
OP_SHR   = 0b1100
OP_JMP   = 0b1101
OP_JZ    = 0b1110
OP_HALT  = 0b1111


def to_signed8(val: int) -> int:
    val &= 0xFF
    return val - 256 if val >= 128 else val


def to_unsigned8(val: int) -> int:
    return val & 0xFF


def make_uio_in(opcode: int, live: int = 1, extra: int = 0) -> int:
    """uio_in[0] = live, uio_in[6:3] = opcode"""
    return ((opcode & 0xF) << 3) | ((extra & 0x3) << 1) | (live & 0x1)


async def reset_cpu(dut):
    dut.ena.value = 1
    dut.ui_in.value = 0
    dut.uio_in.value = make_uio_in(OP_JMP, live=1)
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 1)


async def exec_live(dut, opcode: int, data: int = 0):
    """Εκτελεί 1 εντολή σε Live mode και επιστρέφει (signed_a, overflow)."""
    dut.uio_in.value = make_uio_in(opcode, live=1)
    dut.ui_in.value = to_unsigned8(data)
    await ClockCycles(dut.clk, 1)
    a_val = to_signed8(int(dut.uo_out.value))
    ovf = (int(dut.uio_out.value) >> 7) & 1
    return a_val, ovf


async def write_ram_live(dut, addr: int, value: int):
    """Γράφει το value στη RAM[addr] μέσω Live mode (LOAD -> STORE)."""
    await exec_live(dut, OP_LOAD, value)
    await exec_live(dut, OP_STORE, addr & 0xF)


def golden_step(a: int, ovf: int, opcode: int, b: int):
    """Golden reference model για Live mode (alu.sv + controler.sv)."""
    b = to_signed8(b)
    if opcode in (OP_STORE, OP_JMP, OP_JZ):
        # Σε Live mode δεν ενημερώνονται a και overflow
        return a, ovf

    new_ovf = 0
    if opcode == OP_CLR:
        res = 0
    elif opcode == OP_ADD:
        res = to_signed8(a + b)
        if (a >= 0 and b >= 0 and res < 0) or (a < 0 and b < 0 and res >= 0):
            new_ovf = 1
    elif opcode == OP_SUB:
        res = to_signed8(a - b)
        if (a >= 0 and b < 0 and res < 0) or (a < 0 and b >= 0 and res >= 0):
            new_ovf = 1
    elif opcode == OP_INC:
        res = to_signed8(a + 1)
        if a == 127:
            new_ovf = 1
    elif opcode == OP_DEC:
        res = to_signed8(a - 1)
        if a == -128:
            new_ovf = 1
    elif opcode == OP_LOAD:
        res = b
    elif opcode == OP_AND:
        res = to_signed8((a & 0xFF) & (b & 0xFF))
    elif opcode == OP_OR:
        res = to_signed8((a & 0xFF) | (b & 0xFF))
    elif opcode == OP_XOR:
        res = to_signed8((a & 0xFF) ^ (b & 0xFF))
    elif opcode == OP_NOT:
        res = to_signed8(~(a & 0xFF))
    elif opcode == OP_SHL:
        res = to_signed8(((a & 0xFF) << 1) & 0xFF)
    elif opcode == OP_SHR:
        res = a >> 1  # Arithmetic right shift (διατηρεί το πρόσημο)
    else:
        res = 0

    return res, new_ovf


@cocotb.test()
async def test_reset(dut):
    """1. Έλεγχος Reset."""
    cocotb.start_soon(Clock(dut.clk, 20, unit="ns").start())
    await reset_cpu(dut)

    assert int(dut.uo_out.value) == 0, f"Αναμενόταν uo_out=0 μετά το reset, πήρα {int(dut.uo_out.value)}"
    ovf = (int(dut.uio_out.value) >> 7) & 1
    assert ovf == 0, f"Αναμενόταν overflow=0 μετά το reset, πήρα {ovf}"


@cocotb.test()
async def test_all_alu_ops(dut):
    """2. Συστηματικός έλεγχος όλων των εντολών της ALU σε Live mode."""
    cocotb.start_soon(Clock(dut.clk, 20, unit="ns").start())
    await reset_cpu(dut)

    sequence = [
        (OP_LOAD,  12,   12,  0, "LOAD 12"),
        (OP_ADD,    8,   20,  0, "ADD 8"),
        (OP_SUB,    5,   15,  0, "SUB 5"),
        (OP_INC,    0,   16,  0, "INC"),
        (OP_DEC,    0,   15,  0, "DEC"),
        (OP_SHL,    0,   30,  0, "SHL (15 << 1)"),
        (OP_SHR,    0,   15,  0, "SHR (30 >>> 1)"),
        (OP_OR,  0x50,   95,  0, "OR 0x50"),
        (OP_AND, 0x0F,   15,  0, "AND 0x0F"),
        (OP_XOR, 0x0A,    5,  0, "XOR 0x0A"),
        (OP_NOT,    0,   -6,  0, "NOT 5 -> -6"),
        (OP_SHR,    0,   -3,  0, "Arithmetic SHR (-6 >>> 1 = -3)"),
        (OP_JMP,   99,   -3,  0, "JMP σε Live mode (κρατάει το -3)"),
        (OP_JZ,    99,   -3,  0, "JZ σε Live mode (κρατάει το -3)"),
        (OP_STORE, 42,   -3,  0, "STORE (δεν αλλάζει τον Accumulator)"),
        (OP_CLR,    0,    0,  0, "CLR"),
    ]

    for op, data, exp_a, exp_ovf, desc in sequence:
        a_val, ovf = await exec_live(dut, op, data)
        assert a_val == exp_a and ovf == exp_ovf, (
            f"[{desc}] Αναμενόταν a={exp_a}, ovf={exp_ovf} | Πήρα a={a_val}, ovf={ovf}"
        )


@cocotb.test()
async def test_overflow_edge_cases(dut):
    """3. Έλεγχος όλων των περιπτώσεων Signed Overflow."""
    cocotb.start_soon(Clock(dut.clk, 20, unit="ns").start())
    await reset_cpu(dut)

    await exec_live(dut, OP_LOAD, 100)
    a_val, ovf = await exec_live(dut, OP_ADD, 50)
    assert a_val == -106 and ovf == 1, f"ADD +ovf fail: a={a_val}, ovf={ovf}"

    await exec_live(dut, OP_LOAD, -100)
    a_val, ovf = await exec_live(dut, OP_ADD, -50)
    assert a_val == 106 and ovf == 1, f"ADD -ovf fail: a={a_val}, ovf={ovf}"

    await exec_live(dut, OP_LOAD, 100)
    a_val, ovf = await exec_live(dut, OP_SUB, -50)
    assert a_val == -106 and ovf == 1, f"SUB +ovf fail: a={a_val}, ovf={ovf}"

    await exec_live(dut, OP_LOAD, 127)
    a_val, ovf = await exec_live(dut, OP_INC, 0)
    assert a_val == -128 and ovf == 1, f"INC ovf fail: a={a_val}, ovf={ovf}"

    a_val, ovf = await exec_live(dut, OP_DEC, 0)
    assert a_val == 127 and ovf == 1, f"DEC ovf fail: a={a_val}, ovf={ovf}"


@cocotb.test()
async def test_random_stress(dut):
    """4. Randomized Stress Test (100 τυχαίες εντολές vs Golden Model)."""
    cocotb.start_soon(Clock(dut.clk, 20, unit="ns").start())
    await reset_cpu(dut)

    rng = random.Random(42)
    valid_ops = [
        OP_CLR, OP_ADD, OP_SUB, OP_INC, OP_DEC, OP_LOAD,
        OP_STORE, OP_AND, OP_OR, OP_XOR, OP_NOT, OP_SHL, OP_SHR, OP_JMP, OP_JZ
    ]

    ref_a = 0
    ref_ovf = 0

    for step in range(100):
        op = rng.choice(valid_ops)
        data = rng.randint(-128, 127)

        ref_a, ref_ovf = golden_step(ref_a, ref_ovf, op, data)
        a_val, ovf = await exec_live(dut, op, data)

        assert a_val == ref_a and ovf == ref_ovf, (
            f"Step {step} (op={op:04b}, data={data}): "
            f"Αναμενόταν a={ref_a}, ovf={ref_ovf} | Πήρα a={a_val}, ovf={ovf}"
        )


@cocotb.test()
async def test_program_mode_ram(dut):
    """5. Γραμμικό πρόγραμμα στη RAM (LOAD, ADD, SUB, STORE, CLR, LOAD, HALT)."""
    cocotb.start_soon(Clock(dut.clk, 20, unit="ns").start())
    await reset_cpu(dut)

    program = {
        0: (OP_LOAD  << 4) | 10,   # LOAD  RAM[10] (25)
        1: (OP_ADD   << 4) | 11,   # ADD   RAM[11] (+17 = 42)
        2: (OP_SUB   << 4) | 12,   # SUB   RAM[12] (-10 = 32)
        3: (OP_STORE << 4) | 13,   # STORE RAM[13]
        4: (OP_CLR   << 4) | 0,    # CLR
        5: (OP_LOAD  << 4) | 13,   # LOAD  RAM[13] (32)
        6: (OP_HALT  << 4) | 0,    # HALT
        10: 25,
        11: 17,
        12: 10,
    }

    for addr, byte_val in program.items():
        await write_ram_live(dut, addr, byte_val)

    await exec_live(dut, OP_CLR, 0)

    # Μετάβαση σε Program Mode (live = 0)
    dut.uio_in.value = 0
    dut.ui_in.value = 0

    await ClockCycles(dut.clk, 16)

    a_val = to_signed8(int(dut.uo_out.value))
    ovf = (int(dut.uio_out.value) >> 7) & 1
    assert a_val == 32 and ovf == 0, f"Program Mode fail: αναμενόταν a=32, ovf=0 | πήρα a={a_val}, ovf={ovf}"

    await ClockCycles(dut.clk, 10)
    assert to_signed8(int(dut.uo_out.value)) == 32, "HALT fail: ο Accumulator άλλαξε μετά το HALT"


@cocotb.test()
async def test_program_mode_loop_jmp_jz(dut):
    """6. Loop στη RAM με JMP και JZ: υπολογίζει 5 * 4 = 20 με επαναληπτική πρόσθεση."""
    cocotb.start_soon(Clock(dut.clk, 20, unit="ns").start())
    await reset_cpu(dut)

    program = {
        # Loop: όσο count (RAM[14]) != 0, πρόσθεσε val (RAM[15]) στο sum (RAM[13])
        0: (OP_LOAD  << 4) | 14,   # A = count
        1: (OP_JZ    << 4) | 9,    # αν count == 0 -> πήγαινε στο 9 (τέλος)
        2: (OP_DEC   << 4) | 0,    # count = count - 1
        3: (OP_STORE << 4) | 14,   # αποθήκευσε count
        4: (OP_LOAD  << 4) | 13,   # A = sum
        5: (OP_ADD   << 4) | 15,   # A = sum + val
        6: (OP_STORE << 4) | 13,   # αποθήκευσε sum
        7: (OP_JMP   << 4) | 0,    # πίσω στην αρχή του loop (0)
        9: (OP_LOAD  << 4) | 13,   # φόρτωσε το τελικό sum στον Accumulator
        10: (OP_HALT << 4) | 0,    # HALT
        # Δεδομένα
        13: 0,                     # sum = 0
        14: 4,                     # count = 4
        15: 5,                     # val = 5
    }

    for addr, byte_val in program.items():
        await write_ram_live(dut, addr, byte_val)

    await exec_live(dut, OP_CLR, 0)

    # Μετάβαση σε Program Mode (live = 0)
    dut.uio_in.value = 0
    dut.ui_in.value = 0

    # 4 επαναλήψεις * 8 εντολές * 2 κύκλοι = 64 κύκλοι + 8 κύκλοι εξόδου = 72 κύκλοι
    await ClockCycles(dut.clk, 80)

    a_val = to_signed8(int(dut.uo_out.value))
    ovf = (int(dut.uio_out.value) >> 7) & 1
    assert a_val == 20 and ovf == 0, f"Loop JMP/JZ fail: αναμενόταν a=20, ovf=0 | πήρα a={a_val}, ovf={ovf}"

    # Επιβεβαίωση ότι σταμάτησε όντως στο HALT
    await ClockCycles(dut.clk, 10)
    assert to_signed8(int(dut.uo_out.value)) == 20, "HALT fail μετά το loop"
