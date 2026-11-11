module alu(
    input logic signed [7:0] a,
    input logic signed [7:0] b,
    input logic [3:0] opcode,
    output logic signed [7:0] a_out,
    output logic overflow
);
always_comb begin
overflow = 1'b0;
case (opcode)
4'b0000: a_out=8'b00000000;
4'b0001: begin
a_out = a + b;
if ((a[7]==b[7])&&(a_out[7]!=a[7]))
overflow = 1'b1;
end
4'b0010: begin
a_out = a - b;
if ((a[7]!=b[7])&&(a[7]!=a_out[7]))
overflow =1'b1;
end
4'b0011: begin
a_out = a + 8'sd1;
if (a==8'sb01111111)
overflow = 1'b1;
end
4'b0100: begin 
a_out=a-8'sd1;
if (a==8'sb10000000)
overflow=1'b1;
end
4'b0101:a_out= b;
4'b0110:a_out=a;
4'b0111:a_out=a & b;
4'b1000:a_out=a|b;
4'b1001:a_out=a^b;
4'b1010:a_out=~a;
4'b1011:a_out=a<<1;
4'b1100:a_out=a>>>1;
4'b1101:a_out = a;         // NOP
default:a_out=8'b00000000;
endcase
end
endmodule