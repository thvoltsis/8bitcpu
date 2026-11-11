module ram (
input logic clk,
input logic we,
input logic [3:0] add,
input logic signed [7:0] in,
output logic signed [7:0] out
);
logic signed [7:0] memory [15:0];
always_ff@(posedge clk) begin
    if (we) begin
        memory[add]<=in;
    end
end
assign out=memory[add];
endmodule