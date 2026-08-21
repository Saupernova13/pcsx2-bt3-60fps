// Dump decompiled C and the disassembly listing for functions at given addresses.
//
// Driven by tools/decomp.py via analyzeHeadless -postScript. Each argument is a
// hex EE address; the enclosing function is resolved, decompiled, and written to
// stdout between markers the caller parses.
//
// Passing "-xrefs" as the first argument also lists callers and callees.
//
//@category PS2.BT3

import java.util.ArrayList;
import java.util.List;

import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileOptions;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.CodeUnit;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.Listing;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceIterator;

public class DumpFunction extends GhidraScript {

    private static final int TIMEOUT_SECONDS = 120;

    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length == 0) {
            println("DumpFunction: no addresses given");
            return;
        }

        boolean wantXrefs = false;
        List<String> targets = new ArrayList<>();
        for (String arg : args) {
            if (arg.equals("-xrefs")) {
                wantXrefs = true;
            } else {
                targets.add(arg);
            }
        }

        DecompInterface decompiler = new DecompInterface();
        decompiler.setOptions(new DecompileOptions());
        if (!decompiler.openProgram(currentProgram)) {
            println("DumpFunction: could not open program for decompilation");
            return;
        }

        try {
            for (String target : targets) {
                dumpOne(decompiler, target, wantXrefs);
            }
        } finally {
            decompiler.dispose();
        }
    }

    private void dumpOne(DecompInterface decompiler, String target, boolean wantXrefs) {
        Address addr;
        try {
            addr = currentProgram.getAddressFactory()
                    .getDefaultAddressSpace()
                    .getAddress(Long.parseLong(target.replace("0x", ""), 16));
        } catch (Exception e) {
            println("###BEGIN " + target);
            println("error: cannot parse address '" + target + "'");
            println("###END " + target);
            return;
        }

        println("###BEGIN " + target);

        Function function = getFunctionContaining(addr);
        if (function == null) {
            println("no function contains " + addr + "; disassembling raw instead");
            printListing(addr, addr.add(0x80));
            println("###END " + target);
            return;
        }

        println("### function " + function.getName()
                + " @ " + function.getEntryPoint()
                + "  body " + function.getBody().getMinAddress()
                + "-" + function.getBody().getMaxAddress()
                + "  marked " + addr);
        println("### signature " + function.getPrototypeString(true, true));

        println("### DECOMPILED");
        DecompileResults results =
                decompiler.decompileFunction(function, TIMEOUT_SECONDS, monitor);
        if (results != null && results.decompileCompleted()) {
            println(results.getDecompiledFunction().getC());
        } else {
            String why = results == null ? "no result" : results.getErrorMessage();
            println("// decompilation failed: " + why);
        }

        println("### LISTING");
        printListing(function.getBody().getMinAddress(), function.getBody().getMaxAddress());

        if (wantXrefs) {
            println("### CALLERS");
            for (Function caller : function.getCallingFunctions(monitor)) {
                println("  " + caller.getEntryPoint() + "  " + caller.getName());
            }
            println("### CALLEES");
            for (Function callee : function.getCalledFunctions(monitor)) {
                println("  " + callee.getEntryPoint() + "  " + callee.getName());
            }
            println("### REFERENCES TO ENTRY");
            ReferenceIterator refs = currentProgram.getReferenceManager()
                    .getReferencesTo(function.getEntryPoint());
            while (refs.hasNext()) {
                Reference ref = refs.next();
                println("  " + ref.getFromAddress() + "  " + ref.getReferenceType());
            }
        }

        println("###END " + target);
    }

    private void printListing(Address from, Address to) {
        Listing listing = currentProgram.getListing();
        for (Instruction insn : listing.getInstructions(from, true)) {
            if (insn.getAddress().compareTo(to) > 0) {
                break;
            }
            StringBuilder bytes = new StringBuilder();
            try {
                for (byte b : insn.getBytes()) {
                    bytes.insert(0, String.format("%02X", b));  // little-endian word
                }
            } catch (Exception e) {
                bytes.append("????????");
            }
            String comment = listing.getComment(CodeUnit.EOL_COMMENT, insn.getAddress());
            println(String.format("  %s  %-8s  %-40s%s",
                    insn.getAddress(),
                    bytes,
                    insn.toString(),
                    comment == null ? "" : "   ; " + comment));
        }
    }
}
