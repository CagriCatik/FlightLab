window.MathJax = {
  tex: {
    inlineMath: [["$", "$"], ["\\(", "\\)"]],
    displayMath: [["$$", "$$"], ["\\[", "\\]"]],
    processEscapes: true,
    processEnvironments: true,
    tags: "ams",
    packages: { "[+]": ["noerrors"] }
  },
  options: {
    renderActions: {
      addMenu: []
    }
  },
  loader: {
    load: ["[tex]/noerrors"]
  }
};
