module controler(
input logic clk, //clock by tiny tapeout
input logic rst_n, //reset 
input logic run_cycle,//take step
input logic live, //enable live inputs mode
input logic [3:0] opcode,
input logic [3:0] add, //address for input ram
input logic signed [7:0] data,
input logic signed [7:0] a_result,// alu result
input logic a_overflow,// alu overflow flag
input logic signed [7:0] ram_data,// data from ram

output logic [3:0] a_opcode,
output logic [3:0] ram_add,// the ram add that goes to alu
output logic ram_we,// enable write on ram
output logic signed [7:0] a,// accumulator
output logic overflow,// overflow ff out
output logic signed [7:0] alu_b// data that goes on the alu depending on what the programm says
);
 localparam FETCH   = 1'b0;//fetch state
    localparam EXECUTE = 1'b1;//execute state
    
    logic state; // 1-bit ff for state, fetch or execyte
    
    logic [3:0] pc;
    logic [7:0] instruction_reg;
    assign ram_add=live ? add:(state==FETCH?pc:instruction_reg[3:0]);
    assign a_opcode=live?opcode:(state==EXECUTE ? instruction_reg[7:4]:4'b0000);
    assign alu_b=live?data:ram_data;
    logic we;
    assign we=live ? (opcode==4'b0110):(state==EXECUTE && instruction_reg[7:4]==4'b0110);
    assign ram_we=we && run_cycle;
    always_ff @(posedge clk) begin
        if(!rst_n)begin
        state<=FETCH;
        pc<=4'b0000;
        a <=8'b00000000;
        overflow <=1'b0;
        instruction_reg <=8'b00000000;
    end else 
        if(run_cycle)begin
if(live) begin
    if (opcode != 4'b0110) begin
    a<=a_result;
    overflow<=a_overflow;
end
        end else begin
case(state)
FETCH:begin 
    instruction_reg<=ram_data;
    state<=EXECUTE;
end
EXECUTE:begin
    if(instruction_reg[7:4]==4'b1111)begin
        state<=EXECUTE;
    end
    else begin
        if(instruction_reg[7:4]!==4'b0110)begin
            a<=a_result;
            overflow<=a_overflow;
        end
        pc<=pc+4'b0001;
        state<=FETCH;
    end
end
endcase
        end
    end
        end
endmodule