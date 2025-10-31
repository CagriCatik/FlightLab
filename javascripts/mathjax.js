// Simple initialization wrapper for MathJax
document.addEventListener("DOMContentLoaded", function() {
  if (typeof MathJax !== "undefined") {
    MathJax.typesetPromise();
  }
});
