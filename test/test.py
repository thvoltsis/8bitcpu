import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, FallingEdge, ClockCycles

@cocotb.test()
async def test_full_cpu(dut):
    dut._log.info("--- Εκκίνηση Πλήρους Ελέγχου (Gate-Level Safe) ---")

    # 1. Πιο αργό ρολόι (100ns / 10 MHz) για να προλαβαίνουν τα ρεύματα
    clock = Clock(dut.clk, 100, units="ns")
    cocotb.start_soon(clock.start())

    # Αρχικοποίηση
    dut.ena.value = 1
    dut.ui_in.value = 0
    dut.uio_in.value = 0
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 3)

    await FallingEdge(dut.clk)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 2)

    async def send_live(opcode, ui_data):
        await FallingEdge(dut.clk)
        dut.ui_in.value = ui_data
        dut.uio_in.value = (opcode << 3) | 1
        await RisingEdge(dut.clk)
        await RisingEdge(dut.clk)

    dut._log.info("ΦΑΣΗ 1: Reset και δοκιμή ALU...")
    await FallingEdge(dut.clk) # Πάντα διαβάζουμε στο Falling Edge!
    assert dut.uo_out.value == 0, f"Σφάλμα Reset: {dut.uo_out.value}"

    await send_live(5, 10)
    await FallingEdge(dut.clk)
    assert dut.uo_out.value == 10, f"Σφάλμα ALU LOAD: {dut.uo_out.value}"
    
    await send_live(1, 15)
    await FallingEdge(dut.clk)
    assert dut.uo_out.value == 25, f"Σφάλμα ALU ADD: {dut.uo_out.value}"

    dut._log.info("ΦΑΣΗ 2: Φόρτωση προγράμματος στη RAM...")
    await send_live(5, 0x52)
    await send_live(6, 0x00)

    await send_live(5, 0xF0)
    await send_live(6, 0x01)

    await send_live(5, 42)
    await send_live(6, 0x02)

    dut._log.info("ΦΑΣΗ 3: Εκτέλεση προγράμματος...")
    await FallingEdge(dut.clk)
    dut.ui_in.value = 0
    dut.uio_in.value = 0
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 2)
    
    await FallingEdge(dut.clk)
    dut.rst_n.value = 1
    
    await ClockCycles(dut.clk, 5)
    
    # Το κρίσιμο σημείο: Περιμένουμε το Falling Edge για να ηρεμήσει το ρεύμα 
    # πριν διαβάσουμε τον Accumulator
    await FallingEdge(dut.clk)
    assert dut.uo_out.value == 42, f"Σφάλμα Program Mode: {dut.uo_out.value}"
    
    dut._log.info("--- ΟΛΑ ΤΕΛΕΙΑ! Η CPU ΕΙΝΑΙ ΕΤΟΙΜΗ ΓΙΑ ΚΑΤΑΣΚΕΥΗ! ---")
