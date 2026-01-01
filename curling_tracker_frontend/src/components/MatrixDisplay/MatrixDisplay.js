import { Box, HStack, VStack } from "@chakra-ui/react";

function MatrixDisplay({ matrix }) {
  return (
    <VStack>
      {matrix.map((row, rowIndex) => (
        <HStack key={rowIndex}>
          {row.map((cell, colIndex) => (
            <Box
              key={colIndex}
              display="flex"
              justifyContent="center"
              alignItems="center"
              border="1px solid #eee"
              margin="2px"
              width="90px"
              height="30px"
            >
              {cell.toFixed(2)}
            </Box>
          ))}
        </HStack>
      ))}
    </VStack>
  );
}

export default MatrixDisplay;
