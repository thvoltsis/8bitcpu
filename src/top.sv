`default_nettype none

// Συνδέουμε ΜΟΝΟ τα 3 βασικά αρχεία
`include "alu.sv"
`include "ram.sv"
`include "controler.sv" 

module top(
    input  logic [7:0] ui_in,    // 8 Διακόπτες (sw_addr & sw_data)
    output logic [7:0] uo_out,   // 8 LEDs (Accumulator)
    input  logic [7:0] uio_in,   // Αμφίδρομα (Είσοδοι: Opcode, Live)
    output logic [7:0] uio_out,  // Αμφίδρομα (Έξοδοι: Overflow flag)
    output logic [7:0] uio_oe,   // Output Enable
    input  logic       ena,      
    input  logic       clk,      // Το ρολόι (Ελέγχεται απόλυτα από την πλακέτα / κουμπί)
    input  logic       rst_n     // Το Reset
);

    // Το uio[7] ρυθμίζεται ως έξοδος (για το Overflow). Τα υπόλοιπα uio[6:0] είναι είσοδοι.
    assign uio_oe = 8'b10000000; 

    // --- Καλωδίωση Εσωτερικών Σημάτων ---
    logic signed [7:0] sw_data;
    logic [3:0]        sw_opcode;
    logic [3:0]        sw_addr;
    logic              live_mode;
    
    // --- Καλώδια ALU & RAM ---
    logic [3:0]        alu_op_wire;
    logic signed [7:0] alu_operand_wire;
    logic signed [7:0] alu_result_wire;
    logic              overflow_wire;
    
    logic [3:0]        ram_addr_wire;
    logic              ram_we_wire;
    logic signed [7:0] ram_data_out_wire;
    
    logic signed [7:0] accumulator_wire;
    logic              overflow_flag_wire;

    // --- Ανάθεση Εξωτερικών Pins (I/O Mapping) ---
    assign sw_data   = ui_in[7:0];  
    assign sw_addr   = ui_in[3:0];  
    
    assign sw_opcode = uio_in[6:3]; 
    assign live_mode = uio_in[0];    // 0 = Εκτέλεση προγράμματος (RAM), 1 = Χειροκίνητη λειτουργία
    
    assign uo_out    = accumulator_wire;                         
    assign uio_out   = {overflow_flag_wire, 7'b0000000};         

    // --- Instantiations (Το Μοντάρισμα) ---
    ram u_ram (
        .clk      (clk),
        .we       (ram_we_wire),
        .addr     (ram_addr_wire),
        .data_in  (accumulator_wire),
        .data_out (ram_data_out_wire)
    );

    alu u_alu (
        .a        (accumulator_wire),
        .b        (alu_operand_wire),
        .opcode   (alu_op_wire),
        .a_out    (alu_result_wire),
        .overflow (overflow_wire)
    );

    controler u_controler (
        .clk          (clk),
        .rst_n        (rst_n),
        .run_cycle    (1'b1),            // <--- ΠΑΝΤΑ ΣΤΟ 1! Δεν χρειάζεται πλέον "πάγωμα" από εμάς.
        .live         (live_mode),       
        .opcode       (sw_opcode),       
        .add          (sw_addr),         
        .data         (sw_data),         
        .a_result     (alu_result_wire), 
        .a_overflow   (overflow_wire),   
        .ram_data     (ram_data_out_wire),
        
        .a_opcode     (alu_op_wire),     
        .ram_add      (ram_addr_wire),   
        .ram_we       (ram_we_wire),     
        .a            (accumulator_wire),
        .overflow     (overflow_flag_wire),
        .alu_b        (alu_operand_wire) 
    );

endmodule