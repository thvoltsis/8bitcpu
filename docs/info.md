## How it works

This is a custom single-cycle 8-bit CPU. It features an ALU with 14 operations, a 16-byte synchronous RAM, and a Control Unit Finite State Machine (FSM). It operates in two modes: "Live Mode" for manual input testing and "Program Mode" for executing instructions from the internal RAM.

## How to test

Set the Live Mode pin (uio_in[0]) to 1 to manually feed opcodes and operands via the input pins and observe the accumulator on the output LEDs. Set it to 0 to allow the FSM to fetch and execute instructions directly from the internal RAM on every clock cycle.

## External hardware

No external hardware is required.
