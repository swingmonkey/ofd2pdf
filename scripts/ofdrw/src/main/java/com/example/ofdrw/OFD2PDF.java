package com.example.ofdrw;

import org.ofdrw.converter.ConvertHelper;
import org.ofdrw.converter.GeneralConvertException;
import org.ofdrw.reader.OFDReader;

import java.io.IOException;
import java.nio.file.Path;
import java.nio.file.Paths;

/**
 * Minimal OFD to PDF converter using ofdrw.
 * Usage: java -jar ofdrw-converter-cli.jar <input.ofd> <output.pdf>
 */
public class OFD2PDF {
    public static void main(String[] args) throws IOException, GeneralConvertException {
        if (args.length != 2) {
            System.err.println("Usage: java -jar ofdrw-converter-cli.jar <input.ofd> <output.pdf>");
            System.exit(1);
        }
        Path input = Paths.get(args[0]);
        Path output = Paths.get(args[1]);
        try (OFDReader reader = new OFDReader(input)) {
            ConvertHelper.toPdf(reader, output);
        }
        System.out.println("Converted: " + output.toAbsolutePath());
    }
}
