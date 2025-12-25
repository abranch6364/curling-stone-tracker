import React from 'react';

import './MatrixDisplay.css';

function MatrixDisplay({ matrix }) {
  return (
    <div className="matrix-container">
      {matrix.map((row, rowIndex) => (
        <div key={rowIndex} className="matrix-row">
          {row.map((cell, colIndex) => (
            <span key={colIndex} className="matrix-cell">
              {cell.toFixed(2)}
            </span>
          ))}
        </div>
      ))}
    </div>
  );
}

export default MatrixDisplay;