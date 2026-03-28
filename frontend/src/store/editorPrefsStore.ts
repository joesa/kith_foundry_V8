import { create } from 'zustand';

export type EditorColorTheme =
  | 'forge-dark'
  | 'forge-obsidian'
  | 'forge-midnight'
  | 'forge-nord'
  | 'forge-dracula'
  | 'forge-monokai'
  | 'forge-solarized-dark'
  | 'forge-gruvbox'
  | 'forge-tokyo-night'
  | 'forge-catppuccin'
  | 'forge-one-dark'
  | 'forge-synthwave'
  | 'forge-github-dark'
  | 'forge-ayu-dark'
  | 'forge-rose-pine'
  | 'forge-light'
  | 'forge-solarized-light';

export type FileIconTheme = 'material' | 'minimal' | 'colorful' | 'monochrome';

export interface EditorColorThemeDef {
  id: EditorColorTheme;
  label: string;
  group: 'dark' | 'light';
  preview: { bg: string; fg: string; accent: string; comment: string; keyword: string; string: string };
  statusBar: string;
  activityBar: string;
  sidebarBg: string;
  editorBg: string;
  tabBarBg: string;
  toolbarBg: string;
  bottomPanelBg: string;
  borderColor: string;
  monacoBase: 'vs-dark' | 'vs';
  monacoRules: Array<{ token: string; foreground: string; fontStyle?: string }>;
  monacoColors: Record<string, string>;
}

export const EDITOR_THEMES: EditorColorThemeDef[] = [
  {
    id: 'forge-dark', label: 'Forge Dark', group: 'dark',
    preview: { bg: '#1e1e1e', fg: '#d4d4d4', accent: '#569cd6', comment: '#6a9955', keyword: '#c586c0', string: '#ce9178' },
    statusBar: '#1e1e1e', activityBar: '#1e1e1e', sidebarBg: '#252526', editorBg: '#1e1e1e', tabBarBg: '#252526', toolbarBg: '#2d2d2d', bottomPanelBg: '#1e1e1e', borderColor: '#3c3c3c',
    monacoBase: 'vs-dark',
    monacoRules: [
      { token: 'comment', foreground: '6a9955', fontStyle: 'italic' },
      { token: 'keyword', foreground: 'c586c0' },
      { token: 'string', foreground: 'ce9178' },
      { token: 'number', foreground: 'b5cea8' },
      { token: 'type', foreground: '4ec9b0' },
      { token: 'variable', foreground: '9cdcfe' },
    ],
    monacoColors: { 'editor.background': '#1e1e1e', 'editor.foreground': '#d4d4d4' },
  },
  {
    id: 'forge-obsidian', label: 'Obsidian', group: 'dark',
    preview: { bg: '#0c0f16', fg: '#e8e9f0', accent: '#7ec8ef', comment: '#5a6577', keyword: '#f4a58a', string: '#a8ddf7' },
    statusBar: '#0c0f16', activityBar: '#070a10', sidebarBg: '#0c0f16', editorBg: '#0c0f16', tabBarBg: '#12151d', toolbarBg: '#181b23', bottomPanelBg: '#0c0f16', borderColor: '#1f222b',
    monacoBase: 'vs-dark',
    monacoRules: [
      { token: 'comment', foreground: '5a6577', fontStyle: 'italic' },
      { token: 'keyword', foreground: 'f4a58a' },
      { token: 'string', foreground: 'a8ddf7' },
      { token: 'number', foreground: 'd4a853' },
      { token: 'type', foreground: '7ec8ef' },
      { token: 'variable', foreground: 'e8e9f0' },
    ],
    monacoColors: { 'editor.background': '#0c0f16', 'editor.foreground': '#e8e9f0', 'editor.lineHighlightBackground': '#12151d', 'editor.selectionBackground': '#1f222b' },
  },
  {
    id: 'forge-midnight', label: 'Midnight Blue', group: 'dark',
    preview: { bg: '#0d1117', fg: '#c9d1d9', accent: '#79c0ff', comment: '#8b949e', keyword: '#ff7b72', string: '#a5d6ff' },
    statusBar: '#1f6feb', activityBar: '#0d1117', sidebarBg: '#161b22', editorBg: '#0d1117', tabBarBg: '#161b22', toolbarBg: '#1c2128', bottomPanelBg: '#0d1117', borderColor: '#30363d',
    monacoBase: 'vs-dark',
    monacoRules: [
      { token: 'comment', foreground: '8b949e', fontStyle: 'italic' },
      { token: 'keyword', foreground: 'ff7b72' },
      { token: 'string', foreground: 'a5d6ff' },
      { token: 'number', foreground: '79c0ff' },
      { token: 'type', foreground: 'ffa657' },
      { token: 'variable', foreground: 'c9d1d9' },
    ],
    monacoColors: { 'editor.background': '#0d1117', 'editor.foreground': '#c9d1d9', 'editor.lineHighlightBackground': '#161b22' },
  },
  {
    id: 'forge-nord', label: 'Nord', group: 'dark',
    preview: { bg: '#2e3440', fg: '#d8dee9', accent: '#88c0d0', comment: '#616e88', keyword: '#81a1c1', string: '#a3be8c' },
    statusBar: '#2e3440', activityBar: '#2e3440', sidebarBg: '#2e3440', editorBg: '#2e3440', tabBarBg: '#3b4252', toolbarBg: '#3b4252', bottomPanelBg: '#2e3440', borderColor: '#3b4252',
    monacoBase: 'vs-dark',
    monacoRules: [
      { token: 'comment', foreground: '616e88', fontStyle: 'italic' },
      { token: 'keyword', foreground: '81a1c1' },
      { token: 'string', foreground: 'a3be8c' },
      { token: 'number', foreground: 'b48ead' },
      { token: 'type', foreground: '8fbcbb' },
      { token: 'variable', foreground: 'd8dee9' },
    ],
    monacoColors: { 'editor.background': '#2e3440', 'editor.foreground': '#d8dee9', 'editor.lineHighlightBackground': '#3b4252', 'editor.selectionBackground': '#434c5e' },
  },
  {
    id: 'forge-dracula', label: 'Dracula', group: 'dark',
    preview: { bg: '#282a36', fg: '#f8f8f2', accent: '#bd93f9', comment: '#6272a4', keyword: '#ff79c6', string: '#f1fa8c' },
    statusBar: '#21222c', activityBar: '#21222c', sidebarBg: '#282a36', editorBg: '#282a36', tabBarBg: '#21222c', toolbarBg: '#343746', bottomPanelBg: '#21222c', borderColor: '#44475a',
    monacoBase: 'vs-dark',
    monacoRules: [
      { token: 'comment', foreground: '6272a4', fontStyle: 'italic' },
      { token: 'keyword', foreground: 'ff79c6' },
      { token: 'string', foreground: 'f1fa8c' },
      { token: 'number', foreground: 'bd93f9' },
      { token: 'type', foreground: '8be9fd', fontStyle: 'italic' },
      { token: 'variable', foreground: 'f8f8f2' },
    ],
    monacoColors: { 'editor.background': '#282a36', 'editor.foreground': '#f8f8f2', 'editor.lineHighlightBackground': '#44475a55', 'editor.selectionBackground': '#44475a' },
  },
  {
    id: 'forge-monokai', label: 'Monokai', group: 'dark',
    preview: { bg: '#272822', fg: '#f8f8f2', accent: '#66d9ef', comment: '#75715e', keyword: '#f92672', string: '#e6db74' },
    statusBar: '#414339', activityBar: '#1e1f1c', sidebarBg: '#272822', editorBg: '#272822', tabBarBg: '#1e1f1c', toolbarBg: '#2d2e27', bottomPanelBg: '#1e1f1c', borderColor: '#3e3d32',
    monacoBase: 'vs-dark',
    monacoRules: [
      { token: 'comment', foreground: '75715e', fontStyle: 'italic' },
      { token: 'keyword', foreground: 'f92672' },
      { token: 'string', foreground: 'e6db74' },
      { token: 'number', foreground: 'ae81ff' },
      { token: 'type', foreground: '66d9ef', fontStyle: 'italic' },
      { token: 'variable', foreground: 'f8f8f2' },
    ],
    monacoColors: { 'editor.background': '#272822', 'editor.foreground': '#f8f8f2', 'editor.lineHighlightBackground': '#3e3d3250' },
  },
  {
    id: 'forge-solarized-dark', label: 'Solarized Dark', group: 'dark',
    preview: { bg: '#002b36', fg: '#839496', accent: '#268bd2', comment: '#586e75', keyword: '#859900', string: '#2aa198' },
    statusBar: '#073642', activityBar: '#002b36', sidebarBg: '#002b36', editorBg: '#002b36', tabBarBg: '#073642', toolbarBg: '#073642', bottomPanelBg: '#002b36', borderColor: '#073642',
    monacoBase: 'vs-dark',
    monacoRules: [
      { token: 'comment', foreground: '586e75', fontStyle: 'italic' },
      { token: 'keyword', foreground: '859900' },
      { token: 'string', foreground: '2aa198' },
      { token: 'number', foreground: 'd33682' },
      { token: 'type', foreground: '268bd2' },
      { token: 'variable', foreground: '839496' },
    ],
    monacoColors: { 'editor.background': '#002b36', 'editor.foreground': '#839496', 'editor.lineHighlightBackground': '#073642' },
  },
  {
    id: 'forge-gruvbox', label: 'Gruvbox Dark', group: 'dark',
    preview: { bg: '#282828', fg: '#ebdbb2', accent: '#83a598', comment: '#928374', keyword: '#fb4934', string: '#b8bb26' },
    statusBar: '#3c3836', activityBar: '#1d2021', sidebarBg: '#282828', editorBg: '#282828', tabBarBg: '#1d2021', toolbarBg: '#3c3836', bottomPanelBg: '#1d2021', borderColor: '#3c3836',
    monacoBase: 'vs-dark',
    monacoRules: [
      { token: 'comment', foreground: '928374', fontStyle: 'italic' },
      { token: 'keyword', foreground: 'fb4934' },
      { token: 'string', foreground: 'b8bb26' },
      { token: 'number', foreground: 'd3869b' },
      { token: 'type', foreground: '83a598' },
      { token: 'variable', foreground: 'ebdbb2' },
    ],
    monacoColors: { 'editor.background': '#282828', 'editor.foreground': '#ebdbb2', 'editor.lineHighlightBackground': '#3c383650' },
  },
  {
    id: 'forge-tokyo-night', label: 'Tokyo Night', group: 'dark',
    preview: { bg: '#1a1b26', fg: '#a9b1d6', accent: '#7aa2f7', comment: '#565f89', keyword: '#bb9af7', string: '#9ece6a' },
    statusBar: '#16161e', activityBar: '#16161e', sidebarBg: '#1a1b26', editorBg: '#1a1b26', tabBarBg: '#16161e', toolbarBg: '#1f2335', bottomPanelBg: '#16161e', borderColor: '#27293a',
    monacoBase: 'vs-dark',
    monacoRules: [
      { token: 'comment', foreground: '565f89', fontStyle: 'italic' },
      { token: 'keyword', foreground: 'bb9af7' },
      { token: 'string', foreground: '9ece6a' },
      { token: 'number', foreground: 'ff9e64' },
      { token: 'type', foreground: '2ac3de' },
      { token: 'variable', foreground: 'a9b1d6' },
    ],
    monacoColors: { 'editor.background': '#1a1b26', 'editor.foreground': '#a9b1d6', 'editor.lineHighlightBackground': '#1f2335' },
  },
  {
    id: 'forge-catppuccin', label: 'Catppuccin Mocha', group: 'dark',
    preview: { bg: '#1e1e2e', fg: '#cdd6f4', accent: '#89b4fa', comment: '#6c7086', keyword: '#cba6f7', string: '#a6e3a1' },
    statusBar: '#181825', activityBar: '#181825', sidebarBg: '#1e1e2e', editorBg: '#1e1e2e', tabBarBg: '#181825', toolbarBg: '#313244', bottomPanelBg: '#181825', borderColor: '#313244',
    monacoBase: 'vs-dark',
    monacoRules: [
      { token: 'comment', foreground: '6c7086', fontStyle: 'italic' },
      { token: 'keyword', foreground: 'cba6f7' },
      { token: 'string', foreground: 'a6e3a1' },
      { token: 'number', foreground: 'fab387' },
      { token: 'type', foreground: '89dceb' },
      { token: 'variable', foreground: 'cdd6f4' },
    ],
    monacoColors: { 'editor.background': '#1e1e2e', 'editor.foreground': '#cdd6f4', 'editor.lineHighlightBackground': '#313244', 'editor.selectionBackground': '#45475a' },
  },
  {
    id: 'forge-one-dark', label: 'One Dark Pro', group: 'dark',
    preview: { bg: '#282c34', fg: '#abb2bf', accent: '#61afef', comment: '#5c6370', keyword: '#c678dd', string: '#98c379' },
    statusBar: '#21252b', activityBar: '#21252b', sidebarBg: '#21252b', editorBg: '#282c34', tabBarBg: '#21252b', toolbarBg: '#2c313a', bottomPanelBg: '#21252b', borderColor: '#181a1f',
    monacoBase: 'vs-dark',
    monacoRules: [
      { token: 'comment', foreground: '5c6370', fontStyle: 'italic' },
      { token: 'keyword', foreground: 'c678dd' },
      { token: 'string', foreground: '98c379' },
      { token: 'number', foreground: 'd19a66' },
      { token: 'type', foreground: 'e5c07b' },
      { token: 'variable', foreground: 'e06c75' },
    ],
    monacoColors: { 'editor.background': '#282c34', 'editor.foreground': '#abb2bf', 'editor.lineHighlightBackground': '#2c313c' },
  },
  {
    id: 'forge-synthwave', label: 'Synthwave 84', group: 'dark',
    preview: { bg: '#262335', fg: '#ffffff', accent: '#36f9f6', comment: '#848bbd', keyword: '#fede5d', string: '#ff7edb' },
    statusBar: '#241b2f', activityBar: '#1a1229', sidebarBg: '#262335', editorBg: '#262335', tabBarBg: '#1a1229', toolbarBg: '#2a2139', bottomPanelBg: '#1a1229', borderColor: '#34294f',
    monacoBase: 'vs-dark',
    monacoRules: [
      { token: 'comment', foreground: '848bbd', fontStyle: 'italic' },
      { token: 'keyword', foreground: 'fede5d' },
      { token: 'string', foreground: 'ff7edb' },
      { token: 'number', foreground: 'f97e72' },
      { token: 'type', foreground: '36f9f6' },
      { token: 'variable', foreground: 'ffffff' },
    ],
    monacoColors: { 'editor.background': '#262335', 'editor.foreground': '#ffffff', 'editor.lineHighlightBackground': '#34294f50' },
  },
  {
    id: 'forge-github-dark', label: 'GitHub Dark', group: 'dark',
    preview: { bg: '#24292e', fg: '#e1e4e8', accent: '#79b8ff', comment: '#6a737d', keyword: '#f97583', string: '#9ecbff' },
    statusBar: '#24292e', activityBar: '#1f2428', sidebarBg: '#1f2428', editorBg: '#24292e', tabBarBg: '#1f2428', toolbarBg: '#2f363d', bottomPanelBg: '#1f2428', borderColor: '#444d56',
    monacoBase: 'vs-dark',
    monacoRules: [
      { token: 'comment', foreground: '6a737d', fontStyle: 'italic' },
      { token: 'keyword', foreground: 'f97583' },
      { token: 'string', foreground: '9ecbff' },
      { token: 'number', foreground: '79b8ff' },
      { token: 'type', foreground: 'b392f0' },
      { token: 'variable', foreground: 'e1e4e8' },
    ],
    monacoColors: { 'editor.background': '#24292e', 'editor.foreground': '#e1e4e8' },
  },
  {
    id: 'forge-ayu-dark', label: 'Ayu Dark', group: 'dark',
    preview: { bg: '#0a0e14', fg: '#b3b1ad', accent: '#39bae6', comment: '#626a73', keyword: '#ff8f40', string: '#c2d94c' },
    statusBar: '#0a0e14', activityBar: '#07090d', sidebarBg: '#0a0e14', editorBg: '#0a0e14', tabBarBg: '#0d1016', toolbarBg: '#0f131a', bottomPanelBg: '#0a0e14', borderColor: '#1c2029',
    monacoBase: 'vs-dark',
    monacoRules: [
      { token: 'comment', foreground: '626a73', fontStyle: 'italic' },
      { token: 'keyword', foreground: 'ff8f40' },
      { token: 'string', foreground: 'c2d94c' },
      { token: 'number', foreground: 'e6b450' },
      { token: 'type', foreground: '59c2ff' },
      { token: 'variable', foreground: 'b3b1ad' },
    ],
    monacoColors: { 'editor.background': '#0a0e14', 'editor.foreground': '#b3b1ad', 'editor.lineHighlightBackground': '#0f131a' },
  },
  {
    id: 'forge-rose-pine', label: 'Rose Pine', group: 'dark',
    preview: { bg: '#191724', fg: '#e0def4', accent: '#c4a7e7', comment: '#6e6a86', keyword: '#eb6f92', string: '#f6c177' },
    statusBar: '#1f1d2e', activityBar: '#1f1d2e', sidebarBg: '#1f1d2e', editorBg: '#191724', tabBarBg: '#1f1d2e', toolbarBg: '#26233a', bottomPanelBg: '#1f1d2e', borderColor: '#26233a',
    monacoBase: 'vs-dark',
    monacoRules: [
      { token: 'comment', foreground: '6e6a86', fontStyle: 'italic' },
      { token: 'keyword', foreground: 'eb6f92' },
      { token: 'string', foreground: 'f6c177' },
      { token: 'number', foreground: 'ebbcba' },
      { token: 'type', foreground: '9ccfd8' },
      { token: 'variable', foreground: 'e0def4' },
    ],
    monacoColors: { 'editor.background': '#191724', 'editor.foreground': '#e0def4', 'editor.lineHighlightBackground': '#26233a' },
  },
  {
    id: 'forge-light', label: 'Forge Light', group: 'light',
    preview: { bg: '#ffffff', fg: '#24292e', accent: '#0366d6', comment: '#6a737d', keyword: '#d73a49', string: '#032f62' },
    statusBar: '#f3f3f3', activityBar: '#f3f3f3', sidebarBg: '#f3f3f3', editorBg: '#ffffff', tabBarBg: '#ececec', toolbarBg: '#f3f3f3', bottomPanelBg: '#f3f3f3', borderColor: '#e1e4e8',
    monacoBase: 'vs',
    monacoRules: [
      { token: 'comment', foreground: '6a737d', fontStyle: 'italic' },
      { token: 'keyword', foreground: 'd73a49' },
      { token: 'string', foreground: '032f62' },
      { token: 'number', foreground: '005cc5' },
      { token: 'type', foreground: '6f42c1' },
      { token: 'variable', foreground: '24292e' },
    ],
    monacoColors: { 'editor.background': '#ffffff', 'editor.foreground': '#24292e' },
  },
  {
    id: 'forge-solarized-light', label: 'Solarized Light', group: 'light',
    preview: { bg: '#fdf6e3', fg: '#657b83', accent: '#268bd2', comment: '#93a1a1', keyword: '#859900', string: '#2aa198' },
    statusBar: '#eee8d5', activityBar: '#eee8d5', sidebarBg: '#eee8d5', editorBg: '#fdf6e3', tabBarBg: '#eee8d5', toolbarBg: '#eee8d5', bottomPanelBg: '#eee8d5', borderColor: '#d6cdb8',
    monacoBase: 'vs',
    monacoRules: [
      { token: 'comment', foreground: '93a1a1', fontStyle: 'italic' },
      { token: 'keyword', foreground: '859900' },
      { token: 'string', foreground: '2aa198' },
      { token: 'number', foreground: 'd33682' },
      { token: 'type', foreground: '268bd2' },
      { token: 'variable', foreground: '657b83' },
    ],
    monacoColors: { 'editor.background': '#fdf6e3', 'editor.foreground': '#657b83' },
  },
];

export const FILE_ICON_THEMES: { id: FileIconTheme; label: string }[] = [
  { id: 'material', label: 'Material Icons' },
  { id: 'minimal', label: 'Minimal' },
  { id: 'colorful', label: 'Colorful' },
  { id: 'monochrome', label: 'Monochrome' },
];

export const MATERIAL_FILE_ICONS: Record<string, { icon: string; color: string }> = {
  '.tsx': { icon: 'code', color: '#3178c6' },
  '.jsx': { icon: 'code', color: '#61dafb' },
  '.ts': { icon: 'data_object', color: '#3178c6' },
  '.js': { icon: 'data_object', color: '#f7df1e' },
  '.mjs': { icon: 'data_object', color: '#f7df1e' },
  '.css': { icon: 'palette', color: '#563d7c' },
  '.scss': { icon: 'palette', color: '#cd6799' },
  '.json': { icon: 'settings', color: '#f5a623' },
  '.md': { icon: 'article', color: '#519aba' },
  '.html': { icon: 'language', color: '#e34f26' },
  '.svg': { icon: 'image', color: '#f89820' },
  '.png': { icon: 'image', color: '#a074c4' },
  '.yaml': { icon: 'settings', color: '#cb171e' },
  '.yml': { icon: 'settings', color: '#cb171e' },
  '.env': { icon: 'key', color: '#ecd53f' },
  '.sh': { icon: 'terminal', color: '#89e051' },
  '.gitignore': { icon: 'visibility_off', color: '#f05032' },
  'package.json': { icon: 'inventory_2', color: '#cb3837' },
  'tsconfig.json': { icon: 'settings', color: '#3178c6' },
  'vite.config.ts': { icon: 'bolt', color: '#646cff' },
  'README.md': { icon: 'menu_book', color: '#519aba' },
};

export const MINIMAL_FILE_ICONS: Record<string, { icon: string; color: string }> = {
  '.tsx': { icon: 'description', color: '#888' },
  '.jsx': { icon: 'description', color: '#888' },
  '.ts': { icon: 'description', color: '#888' },
  '.js': { icon: 'description', color: '#888' },
  '.css': { icon: 'description', color: '#888' },
  '.json': { icon: 'description', color: '#888' },
  '.html': { icon: 'description', color: '#888' },
  '.md': { icon: 'description', color: '#888' },
};

export const COLORFUL_FILE_ICONS: Record<string, { icon: string; color: string }> = {
  '.tsx': { icon: 'code', color: '#61dafb' },
  '.jsx': { icon: 'code', color: '#61dafb' },
  '.ts': { icon: 'data_object', color: '#3178c6' },
  '.js': { icon: 'javascript', color: '#f7df1e' },
  '.css': { icon: 'brush', color: '#ff79c6' },
  '.scss': { icon: 'brush', color: '#cd6799' },
  '.json': { icon: 'data_array', color: '#ffa657' },
  '.md': { icon: 'edit_note', color: '#42b883' },
  '.html': { icon: 'html', color: '#e34f26' },
  '.svg': { icon: 'draw', color: '#ffb300' },
  '.env': { icon: 'lock', color: '#ecd53f' },
};

interface EditorPrefsState {
  fontSize: number;
  fontFamily: string;
  colorTheme: EditorColorTheme;
  fileIconTheme: FileIconTheme;
  minimap: boolean;
  wordWrap: boolean;
  lineNumbers: boolean;
  bracketPairColorization: boolean;
  renderWhitespace: 'none' | 'boundary' | 'all';
  cursorBlinking: 'blink' | 'smooth' | 'expand' | 'phase';
  cursorStyle: 'line' | 'block' | 'underline';
  smoothScrolling: boolean;
  tabSize: number;
  stickyScroll: boolean;
  settingsOpen: boolean;

  setFontSize: (size: number) => void;
  increaseFontSize: () => void;
  decreaseFontSize: () => void;
  setFontFamily: (family: string) => void;
  setColorTheme: (theme: EditorColorTheme) => void;
  setFileIconTheme: (theme: FileIconTheme) => void;
  setMinimap: (enabled: boolean) => void;
  setWordWrap: (enabled: boolean) => void;
  setLineNumbers: (enabled: boolean) => void;
  setBracketPairColorization: (enabled: boolean) => void;
  setRenderWhitespace: (mode: 'none' | 'boundary' | 'all') => void;
  setCursorBlinking: (mode: 'blink' | 'smooth' | 'expand' | 'phase') => void;
  setCursorStyle: (style: 'line' | 'block' | 'underline') => void;
  setSmoothScrolling: (enabled: boolean) => void;
  setTabSize: (size: number) => void;
  setStickyScroll: (enabled: boolean) => void;
  setSettingsOpen: (open: boolean) => void;
}

const loadPref = <T>(key: string, fallback: T): T => {
  if (typeof window === 'undefined') return fallback;
  try {
    const v = localStorage.getItem(`forge-editor-${key}`);
    if (v === null) return fallback;
    return JSON.parse(v) as T;
  } catch { return fallback; }
};

const savePref = (key: string, value: unknown) => {
  if (typeof window !== 'undefined') {
    localStorage.setItem(`forge-editor-${key}`, JSON.stringify(value));
  }
};

export const useEditorPrefsStore = create<EditorPrefsState>((set) => ({
  fontSize: loadPref('fontSize', 13),
  fontFamily: loadPref('fontFamily', "'JetBrains Mono', 'Fira Code', monospace"),
  colorTheme: loadPref('colorTheme', 'forge-dark'),
  fileIconTheme: loadPref('fileIconTheme', 'material'),
  minimap: loadPref('minimap', false),
  wordWrap: loadPref('wordWrap', false),
  lineNumbers: loadPref('lineNumbers', true),
  bracketPairColorization: loadPref('bracketPairColorization', true),
  renderWhitespace: loadPref('renderWhitespace', 'none'),
  cursorBlinking: loadPref('cursorBlinking', 'smooth'),
  cursorStyle: loadPref('cursorStyle', 'line'),
  smoothScrolling: loadPref('smoothScrolling', true),
  tabSize: loadPref('tabSize', 2),
  stickyScroll: loadPref('stickyScroll', false),
  settingsOpen: false,

  setFontSize: (size) => { savePref('fontSize', size); set({ fontSize: size }); },
  increaseFontSize: () => set((s) => { const n = Math.min(s.fontSize + 1, 28); savePref('fontSize', n); return { fontSize: n }; }),
  decreaseFontSize: () => set((s) => { const n = Math.max(s.fontSize - 1, 8); savePref('fontSize', n); return { fontSize: n }; }),
  setFontFamily: (family) => { savePref('fontFamily', family); set({ fontFamily: family }); },
  setColorTheme: (theme) => { savePref('colorTheme', theme); set({ colorTheme: theme }); },
  setFileIconTheme: (theme) => { savePref('fileIconTheme', theme); set({ fileIconTheme: theme }); },
  setMinimap: (enabled) => { savePref('minimap', enabled); set({ minimap: enabled }); },
  setWordWrap: (enabled) => { savePref('wordWrap', enabled); set({ wordWrap: enabled }); },
  setLineNumbers: (enabled) => { savePref('lineNumbers', enabled); set({ lineNumbers: enabled }); },
  setBracketPairColorization: (enabled) => { savePref('bracketPairColorization', enabled); set({ bracketPairColorization: enabled }); },
  setRenderWhitespace: (mode) => { savePref('renderWhitespace', mode); set({ renderWhitespace: mode }); },
  setCursorBlinking: (mode) => { savePref('cursorBlinking', mode); set({ cursorBlinking: mode }); },
  setCursorStyle: (style) => { savePref('cursorStyle', style); set({ cursorStyle: style }); },
  setSmoothScrolling: (enabled) => { savePref('smoothScrolling', enabled); set({ smoothScrolling: enabled }); },
  setTabSize: (size) => { savePref('tabSize', size); set({ tabSize: size }); },
  setStickyScroll: (enabled) => { savePref('stickyScroll', enabled); set({ stickyScroll: enabled }); },
  setSettingsOpen: (open) => set({ settingsOpen: open }),
}));

export function getFileIcon(fileName: string, theme: FileIconTheme): { icon: string; color: string } {
  const iconSets: Record<FileIconTheme, Record<string, { icon: string; color: string }>> = {
    material: MATERIAL_FILE_ICONS,
    minimal: MINIMAL_FILE_ICONS,
    colorful: COLORFUL_FILE_ICONS,
    monochrome: MINIMAL_FILE_ICONS,
  };
  const icons = iconSets[theme];
  if (icons[fileName]) return icons[fileName];
  const ext = '.' + fileName.split('.').pop();
  if (icons[ext]) return icons[ext];
  return { icon: 'description', color: theme === 'monochrome' ? '#888' : '#9e9e9e' };
}

export function getThemeDef(id: EditorColorTheme): EditorColorThemeDef {
  return EDITOR_THEMES.find((t) => t.id === id) ?? EDITOR_THEMES[0];
}
