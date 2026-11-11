module ram (
input logic clk,
input logic we,
    input logic [3:0] addr,
    input logic signed [7:0] data_in,
    output logic signed [7:0] data_out
);
logic signed [7:0] memory [15:0];
always_ff@(posedge clk) begin
    if (we) begin
        memory[addr]<=data_in;
    end
end
    assign data_out=memory[addr];
endmodule
