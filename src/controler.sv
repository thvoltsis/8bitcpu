module controler (
    input logic clk,//clock
    input logic rst_n,//reset normal high
    input logic live,//enables live mode
    input logic [3:0] opcode ,//opcode
    input logic [3:0] add,//mem address
    input logic signed [7:0] data,
    input logic signed [7:0] a_result,//alu result
    input logic a_overflow,//alu overflow
    input logic signed [7:0] ram_data ,//data from ram either opcode either number

    output logic signed [7:0]  a,//accumulator
    output logic  [3:0] a_opcode,
    output logic we,//write enable in ram
    output logic [3:0] ram_add,
    output logic overflow,
    output logic signed [7:0] alu_b//data that goes to alu
);
typedef enum logic { FETCH = 1'b0, EXECUTE = 1'b1 } fsm;
fsm state;
logic [3:0] pc;//program counter
logic [7:0] instruction_reg;


assign ram_add=live?add:(state==FETCH?pc:instruction_reg[3:0]);
assign a_opcode=live?opcode:(state==EXECUTE?instruction_reg[7:4]:4'b0000);
assign we=live?(opcode==4'b0110):(state==EXECUTE && instruction_reg[7:4]==4'b0110);
assign alu_b=live?data:ram_data;


always_ff @ (posedge clk) begin
    if(!rst_n)begin
        pc<=4'b0000;
        a<=8'b00000000;
        overflow<=1'b0;
        state<=FETCH;
        instruction_reg<=8'b00000000; 
    end else 
        if(live) begin
            if(opcode!=4'b0110&&opcode!=4'b1101&&opcode!=4'b1110&& opcode != 4'b1111) begin
                overflow<=a_overflow;
                a<=a_result;
            end
        end else begin
            case(state)
            FETCH:begin
            instruction_reg<=ram_data;
            
            state<=EXECUTE;
        end
            EXECUTE:begin
                if(instruction_reg[7:4]==4'b1111)
                state<=EXECUTE;
                else if(instruction_reg[7:4]==4'b1101)begin
                    pc<=instruction_reg[3:0];//JUMP OPERATION
                    state<=FETCH;
                end else if(instruction_reg[7:4]==4'b1110) begin
                    pc<=(a==8'sd0)?instruction_reg[3:0]:(pc+4'b0001);//JUMP IF ACC=0
                    state<=FETCH;
                end else begin
                    if(instruction_reg[7:4]!=4'b0110)begin
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
endmodule
