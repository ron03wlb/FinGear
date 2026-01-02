({
  katexConfig: {
    "macros": {}
  },
  mathjaxConfig: {
    "tex": {},
    "options": {},
    "loader": {}
  },
  mermaidConfig: {
    theme: 'dark',
    // 强制深色主题配置
    themeVariables: {
      primaryColor: '#1e3a5f',
      primaryTextColor: '#e0e0e0',
      primaryBorderColor: '#4ec9b0',
      lineColor: '#4ec9b0',
      secondaryColor: '#2d2d2d',
      tertiaryColor: '#404040',
      textColor: '#e0e0e0',
      mainBkg: '#1e1e1e',
      secondBkg: '#2d2d2d',
      border1: '#404040',
      border2: '#4ec9b0',
      arrowheadColor: '#4ec9b0',
      fontFamily: '"Segoe UI", Tahoma, Geneva, Verdana, sans-serif',
      fontSize: '16px',
      labelBackground: '#2d2d2d',
      nodeBorder: '#4ec9b0',
      clusterBkg: '#252525',
      clusterBorder: '#404040',
      defaultLinkColor: '#4ec9b0',
      titleColor: '#ffffff',
      edgeLabelBackground: '#1e1e1e',
      actorBorder: '#4ec9b0',
      actorBkg: '#2d2d2d',
      actorTextColor: '#e0e0e0',
      actorLineColor: '#4ec9b0',
      signalColor: '#e0e0e0',
      signalTextColor: '#e0e0e0',
      labelBoxBkgColor: '#2d2d2d',
      labelBoxBorderColor: '#4ec9b0',
      labelTextColor: '#e0e0e0',
      loopTextColor: '#e0e0e0',
      noteBorderColor: '#4ec9b0',
      noteBkgColor: '#2d2d2d',
      noteTextColor: '#e0e0e0',
      activationBorderColor: '#4ec9b0',
      activationBkgColor: '#404040',
      sequenceNumberColor: '#ffffff'
    }
  },
  parserConfig: {
    onDidParseMarkdown: async function(html) {
      return html
    },
    onWillParseMarkdown: async function(markdown) {
      return markdown
    },
    onWillTransformMarkdown: async function(markdown) {
      return markdown
    },
    onDidTransformMarkdown: async function(markdown) {
      return markdown
    }
  },
  revealjsTheme: 'black.css',
  mermaidTheme: 'dark',
  codeBlockTheme: 'monokai.css',
  previewTheme: 'github-dark.css',
  enableScriptExecution: false,
  scrollSync: true,
  liveUpdate: true,
  breakOnSingleNewLine: true,
  enableTypographer: false,
  enableWikiLinkSyntax: true,
  wikiLinkFileExtension: '.md',
  enableLinkify: true,
  useGitHubStyle: false,
  openPreviewToTheSide: true,
  automaticallyShowPreviewOfMarkdownBeingEdited: false,
  enableHTML5Embed: false,
  HTML5EmbedUseImageSyntax: true,
  HTML5EmbedUseLinkSyntax: false,
  HTML5EmbedIsAllowedHttp: false,
  HTML5EmbedAudioAttributes: 'controls preload="metadata"',
  HTML5EmbedVideoAttributes: 'controls preload="metadata"',
  puppeteerWaitForTimeout: 0,
  usePuppeteerCore: true,
  puppeteerArgs: [],
  alwaysShowBacklinksInPreview: false,
  imageFolderPath: '/assets',
  imageUploader: 'imgur',
  printBackground: true,
  chromePath: '',
  imageMagickPath: '',
  pandocPath: 'pandoc',
  pandocMarkdownFlavor: 'markdown-raw_tex+tex_math_single_backslash',
  pandocArguments: [],
  latexEngine: 'pdflatex',
  enableExtendedTableSyntax: false,
  enableCriticMarkupSyntax: false,
  frontMatterRenderingOption: 'none',
  mathRenderingOption: 'KaTeX',
  mathInlineDelimiters: [["$", "$"], ["\\(", "\\)"]],
  mathBlockDelimiters: [["$$", "$$"], ["\\[", "\\]"]],
  mathRenderingOnlineService: 'https://latex.codecogs.com/gif.latex',
  codeChunksExecutionEngine: 'node'
})
