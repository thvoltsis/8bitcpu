import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer

@cocotb.test()
async def test_full_cpu(dut):
    dut._log.info("--- Ξεκινάει ο ΠΛΗΡΗΣ έλεγχος της 8-bit CPU ---")

    # 1. Εκκίνηση Ρολογιού (100 MHz)
    clock = Clock(dut.clk, 10, units="ns")
    cocotb.start_soon(clock.start())

    # Βοηθητική συνάρτηση για Live Mode
    async def send_live(opcode, ui_data):
        dut.ui_in.value = ui_data
        dut.uio_in.value = (opcode << 3) | 1  # uio_in[6:3] = opcode, uio_in[0] = 1 (Live)
        await RisingEdge(dut.clk) # Περιμένουμε 1 κύκλο για να ενημερωθεί ο Accumulator

    # =========================================================================
    # ΦΑΣΗ 1: RESET ΚΑΙ ΕΛΕΓΧΟΣ ALU (LIVE MODE)
    # =========================================================================
    dut._log.info("ΦΑΣΗ 1: Reset και δοκιμή ALU...")
    dut.ena.value = 1
    dut.ui_in.value = 0
    dut.uio_in.value = 0
    
    # Κάνουμε Reset
    dut.rst_n.value = 0
    await Timer(20, units="ns")
    dut.rst_n.value = 1
    await RisingEdge(dut.clk)
    
    assert dut.uo_out.value == 0, "Σφάλμα: O Accumulator δεν μηδενίστηκε μετά το Reset!"

    # Δοκιμή LOAD (Opcode 5: a_out = b) -> Φορτώνουμε το 10
    await send_live(5, 10)
    assert dut.uo_out.value == 10, f"Σφάλμα ALU LOAD: Περίμενα 10, πήρα {dut.uo_out.value.integer}"
    
    # Δοκιμή ADD (Opcode 1: a_out = a + b) -> 10 + 15 = 25
    await send_live(1, 15)
    assert dut.uo_out.value == 25, f"Σφάλμα ALU ADD: Περίμενα 25, πήρα {dut.uo_out.value.integer}"

    # =========================================================================
    # ΦΑΣΗ 2: ΕΓΓΡΑΦΗ ΜΙΚΡΟΥ ΠΡΟΓΡΑΜΜΑΤΟΣ ΣΤΗ RAM (Μέσω Live Mode)
    # =========================================================================
    dut._log.info("ΦΑΣΗ 2: Φόρτωση προγράμματος στη RAM...")
    
    # ΠΡΟΓΡΑΜΜΑ:
    # RAM[0] = 0x52 (Opcode 5 = LOAD, Operand Addr = 2). Φόρτωσε στον Accumulator τα δεδομένα της RAM[2].
    # RAM[1] = 0xF0 (Opcode 15 = HALT, Operand Addr = 0). Σταμάτα.
    # RAM[2] = 42   (Τα δεδομένα μας)

    # Γράφουμε το 0x52 στη διεύθυνση 0
    await send_live(5, 0x52) # Accumulator = 0x52
    await send_live(6, 0x00) # Write RAM(addr=0) = Accumulator

    # Γράφουμε το 0xF0 στη διεύθυνση 1
    await send_live(5, 0xF0) # Accumulator = 0xF0
    await send_live(6, 0x01) # Write RAM(addr=1) = Accumulator

    # Γράφουμε το 42 στη διεύθυνση 2
    await send_live(5, 42)   # Accumulator = 42
    await send_live(6, 0x02) # Write RAM(addr=2) = Accumulator

    # =========================================================================
    # ΦΑΣΗ 3: ΕΚΤΕΛΕΣΗ ΠΡΟΓΡΑΜΜΑΤΟΣ (PROGRAM MODE)
    # =========================================================================
    dut._log.info("ΦΑΣΗ 3: Εκτέλεση προγράμματος από τη μνήμη...")
    
    # Κάνουμε ξανά Reset για να πάει ο Program Counter (pc) στο 0
    dut.rst_n.value = 0
    await Timer(20, units="ns")
    dut.rst_n.value = 1
    
    # Κλείνουμε το Live Mode (uio_in[0] = 0)
    dut.ui_in.value = 0
    dut.uio_in.value = 0
    
    # Το πρόγραμμα χρειάζεται 4 κύκλους ρολογιού για να τρέξει:
    # 1. FETCH RAM[0]
    # 2. EXECUTE RAM[0] (Βάζει το 42 στον Accumulator)
    # 3. FETCH RAM[1]
    # 4. EXECUTE RAM[1] (Βλέπει HALT, παγώνει)
    for _ in range(5):
        await RisingEdge(dut.clk)
        
    # Έλεγχος τελικού αποτελέσματος: 
    # Αν η CPU δουλεύει σωστά, διάβασε το 42 από τη RAM και το έβαλε στα LEDs
    assert dut.uo_out.value == 42, f"Σφάλμα Program Mode: Περίμενα 42, πήρα {dut.uo_out.value.integer}"

    dut._log.info("--- ΟΛΑ ΤΕΛΕΙΑ! Η CPU ΕΙΝΑΙ ΕΤΟΙΜΗ ΓΙΑ ΚΑΤΑΣΚΕΥΗ! ---")
