import React, { useState, useRef, useEffect, useMemo } from 'react';
import * as math from 'mathjs';
import Papa from 'papaparse';
import * as XLSX from 'xlsx';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import {
  FileText, Table2, Presentation, Mail as MailIcon, Cloud, Bold, Italic,
  Underline, Strikethrough, List, ListOrdered, Heading1, Heading2, Heading3,
  Plus, Trash2, Send, Star, Search, Moon, Sun, Reply, Forward, Download,
  X, Upload, Lock, AlignLeft, AlignCenter, AlignRight, AlignJustify, Link2,
  Image as ImageIcon, Table as TableIcon, Undo2, Redo2, MessageSquare,
  Quote, Code, Printer, History, Command, Palette, ChevronUp, ChevronDown,
  Copy, Play, StickyNote, Tag, Archive, Paperclip, Clock, Settings,
  CheckSquare, Square, RotateCcw, FileSpreadsheet, BarChart3,
} from 'lucide-react';

// ============================================================================
// DESIGN TOKENS — "Vault Ledger" identity
// ============================================================================
const FONT_STYLE = `
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=Source+Serif+4:wght@400;600&family=JetBrains+Mono:wght@500&display=swap');
.ov-display { font-family: 'Space Grotesk', sans-serif; }
.ov-serif { font-family: 'Source Serif 4', Georgia, serif; }
.ov-mono { font-family: 'JetBrains Mono', monospace; }
.ov-seal { filter: drop-shadow(0 1px 1px rgba(0,0,0,0.25)); }
[contenteditable]:focus { outline: none; }
.ov-scrollbar::-webkit-scrollbar { width: 8px; height: 8px; }
.ov-scrollbar::-webkit-scrollbar-thumb { background: #a1a1aa; border-radius: 8px; }
mark.ov-comment-mark { background: rgba(201,154,58,0.28); border-bottom: 2px solid #C99A3A; cursor: pointer; }
`;

const BRASS = '#C99A3A';
const BRASS_DARK = '#A87F2A';

function VaultSeal({ size = 26, color = BRASS }) {
  return (
    <svg width={size} height={size} viewBox="0 0 40 40" className="ov-seal">
      <circle cx="20" cy="20" r="18" fill="none" stroke={color} strokeWidth="2.5" />
      <circle cx="20" cy="20" r="11" fill="none" stroke={color} strokeWidth="1.5" />
      {[...Array(8)].map((_, i) => {
        const a = (i * Math.PI) / 4;
        const x1 = 20 + Math.cos(a) * 14, y1 = 20 + Math.sin(a) * 14;
        const x2 = 20 + Math.cos(a) * 17, y2 = 20 + Math.sin(a) * 17;
        return <line key={i} x1={x1} y1={y1} x2={x2} y2={y2} stroke={color} strokeWidth="1.5" />;
      })}
      <circle cx="20" cy="20" r="3.2" fill={color} />
    </svg>
  );
}

const uid = (p) => `${p}${Math.random().toString(36).slice(2, 8)}`;

// ============================================================================
// SAFE FORMULA ENGINE — range functions + cell refs, evaluated by mathjs
// (a sandboxed expression parser; never raw JS eval()).
// ============================================================================
function colToNum(col) { let n = 0; for (let i = 0; i < col.length; i++) n = n * 26 + (col.charCodeAt(i) - 64); return n; }
function numToCol(n) { let s = ''; while (n > 0) { const r = (n - 1) % 26; s = String.fromCharCode(65 + r) + s; n = Math.floor((n - 1) / 26); } return s; }
function parseRef(ref) { const m = ref.match(/^([A-Z]+)(\d+)$/); return m ? { col: m[1], row: parseInt(m[2], 10) } : null; }
function expandRange(start, end) {
  const s = parseRef(start), e = parseRef(end);
  if (!s || !e) return [];
  const c1 = colToNum(s.col), c2 = colToNum(e.col);
  const cells = [];
  for (let r = Math.min(s.row, e.row); r <= Math.max(s.row, e.row); r++) {
    for (let c = Math.min(c1, c2); c <= Math.max(c1, c2); c++) cells.push(numToCol(c) + r);
  }
  return cells;
}

function resolveCell(ref, grid, seen) {
  if (seen.has(ref)) return 0;
  const raw = grid[ref];
  if (raw === undefined || raw === '') return 0;
  if (typeof raw === 'string' && raw.startsWith('=')) {
    const nextSeen = new Set(seen); nextSeen.add(ref);
    const r = evaluateFormula(raw, grid, nextSeen);
    const n = parseFloat(r);
    return isNaN(n) ? 0 : n;
  }
  const n = parseFloat(raw);
  return isNaN(n) ? 0 : n;
}

function rangeFn(fn, cells, grid, seen) {
  const nums = cells.map((c) => resolveCell(c, grid, seen));
  const f = fn.toUpperCase();
  if (f === 'SUM') return nums.reduce((a, b) => a + b, 0);
  if (f === 'AVERAGE' || f === 'AVG') return nums.length ? nums.reduce((a, b) => a + b, 0) / nums.length : 0;
  if (f === 'MIN') return nums.length ? Math.min(...nums) : 0;
  if (f === 'MAX') return nums.length ? Math.max(...nums) : 0;
  if (f === 'COUNT') return nums.filter((n) => !isNaN(n)).length;
  return 0;
}

function evaluateFormula(raw, grid, seen = new Set()) {
  if (typeof raw !== 'string' || !raw.startsWith('=')) return raw;
  let expr = raw.slice(1);
  // 1. range functions: SUM(A1:A5), AVERAGE(B2:B9), etc.
  expr = expr.replace(/(SUM|AVERAGE|AVG|MIN|MAX|COUNT)\(\s*([A-Z]+\d+)\s*:\s*([A-Z]+\d+)\s*\)/gi,
    (m, fn, a, b) => String(rangeFn(fn, expandRange(a.toUpperCase(), b.toUpperCase()), grid, seen)));
  // 2. plain single-cell refs
  expr = expr.replace(/[A-Z]+[0-9]+/g, (ref) => String(resolveCell(ref, grid, seen)));
  // 3. IF(cond, a, b) -> ternary (no nested parens inside args, by design)
  expr = expr.replace(/IF\(([^()]*)\)/gi, (m, inner) => {
    const parts = inner.split(',');
    return parts.length === 3 ? `(${parts[0]}) ? (${parts[1]}) : (${parts[2]})` : m;
  });
  try {
    const result = math.evaluate(expr);
    if (typeof result === 'number') return isFinite(result) ? Math.round(result * 10000) / 10000 : '#ERR';
    return result;
  } catch { return '#ERR'; }
}

function formatValue(val, fmt) {
  const n = parseFloat(val);
  if (fmt === 'currency' && !isNaN(n)) return `$${n.toFixed(2)}`;
  if (fmt === 'percent' && !isNaN(n)) return `${(n * 100).toFixed(1)}%`;
  return val;
}

function displayCell(key, grid, formats = {}) {
  const raw = grid[key];
  if (raw === undefined) return '';
  const val = typeof raw === 'string' && raw.startsWith('=') ? evaluateFormula(raw, grid) : raw;
  return formatValue(val, formats[key]);
}

// ============================================================================
// COMMAND PALETTE — Cmd/Ctrl+K quick switcher
// ============================================================================
function CommandPalette({ open, onClose, actions, dark }) {
  const [q, setQ] = useState('');
  const inputRef = useRef(null);
  useEffect(() => { if (open) { setQ(''); setTimeout(() => inputRef.current?.focus(), 20); } }, [open]);
  if (!open) return null;
  const filtered = actions.filter((a) => a.label.toLowerCase().includes(q.toLowerCase()));
  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-28" style={{ background: 'rgba(0,0,0,0.45)' }} onClick={onClose}>
      <div onClick={(e) => e.stopPropagation()}
        className={`w-full max-w-md rounded-xl shadow-2xl border overflow-hidden ${dark ? 'bg-zinc-900 border-zinc-700' : 'bg-white border-zinc-200'}`}>
        <div className="flex items-center px-3 py-2.5 border-b border-zinc-200 dark:border-zinc-800">
          <Command size={15} className="text-zinc-400 mr-2" />
          <input ref={inputRef} value={q} onChange={(e) => setQ(e.target.value)} placeholder="Jump to app, action..."
            className={`flex-1 outline-none bg-transparent text-sm ${dark ? 'text-zinc-100' : 'text-zinc-900'}`} />
          <kbd className="text-[10px] text-zinc-400 border rounded px-1">esc</kbd>
        </div>
        <div className="max-h-72 overflow-y-auto ov-scrollbar">
          {filtered.length === 0 && <p className="text-xs text-zinc-400 px-3 py-3">No matches.</p>}
          {filtered.map((a) => (
            <button key={a.label} onClick={() => { a.run(); onClose(); }}
              className={`w-full flex items-center space-x-2.5 px-3 py-2 text-sm text-left ${dark ? 'text-zinc-200 hover:bg-zinc-800' : 'text-zinc-700 hover:bg-zinc-100'}`}>
              <a.icon size={14} style={{ color: BRASS }} /> <span>{a.label}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// TRASH PANEL — shared recycle bin across Drive / Docs / Slides
// ============================================================================
function TrashPanel({ open, onClose, dark, files, restoreFile, docs, restoreDoc, slides, restoreSlide }) {
  if (!open) return null;
  const empty = files.length === 0 && docs.length === 0 && slides.length === 0;
  return (
    <div className="fixed inset-0 z-50 flex justify-end" style={{ background: 'rgba(0,0,0,0.35)' }} onClick={onClose}>
      <div onClick={(e) => e.stopPropagation()}
        className={`w-96 h-full p-5 overflow-y-auto ov-scrollbar ${dark ? 'bg-zinc-900 text-zinc-100' : 'bg-white text-zinc-900'}`}>
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-semibold text-lg flex items-center space-x-2"><Trash2 size={17} /><span>Trash</span></h2>
          <button onClick={onClose}><X size={16} /></button>
        </div>
        {empty && <p className="text-sm text-zinc-400">Trash is empty.</p>}
        {files.length > 0 && (
          <div className="mb-5">
            <p className="text-xs font-semibold text-zinc-400 mb-2">FILES</p>
            {files.map((f) => (
              <div key={f.id} className="flex items-center justify-between py-1.5 text-sm">
                <span className="truncate">{f.name}</span>
                <button onClick={() => restoreFile(f.id)} className="text-xs font-medium" style={{ color: BRASS }}>Restore</button>
              </div>
            ))}
          </div>
        )}
        {docs.length > 0 && (
          <div className="mb-5">
            <p className="text-xs font-semibold text-zinc-400 mb-2">DOCS</p>
            {docs.map((d) => (
              <div key={d.id} className="flex items-center justify-between py-1.5 text-sm">
                <span className="truncate">{d.name}</span>
                <button onClick={() => restoreDoc(d.id)} className="text-xs font-medium" style={{ color: BRASS }}>Restore</button>
              </div>
            ))}
          </div>
        )}
        {slides.length > 0 && (
          <div>
            <p className="text-xs font-semibold text-zinc-400 mb-2">SLIDES</p>
            {slides.map((s) => (
              <div key={s.id} className="flex items-center justify-between py-1.5 text-sm">
                <span className="truncate">{s.title}</span>
                <button onClick={() => restoreSlide(s.id)} className="text-xs font-medium" style={{ color: BRASS }}>Restore</button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ============================================================================
// MAIN APP
// ============================================================================
export default function OmniVault() {
  const [app, setApp] = useState('drive');
  const [dark, setDark] = useState(false);
  const [query, setQuery] = useState('');
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [trashOpen, setTrashOpen] = useState(false);

  const [files, setFiles] = useState([
    { id: 'f1', name: 'Q3_Board_Deck.pdf', size: 4.2, modified: 'Jul 28' },
    { id: 'f2', name: 'Resistance_Dataset.csv', size: 18.6, modified: 'Jul 25' },
  ]);
  const [trashFiles, setTrashFiles] = useState([]);

  const [docs, setDocs] = useState([
    { id: 'd1', name: 'Strategic Plan', html: '<h2>Strategic Plan</h2><p>Client-side encryption is <strong>active</strong>. Start writing your notes here...</p>', versions: [], comments: [] },
  ]);
  const [trashDocs, setTrashDocs] = useState([]);

  const [slides, setSlides] = useState([
    { id: 's1', title: 'Project Deck', body: 'Click to add presentation notes', notes: '', layout: 'title', theme: 'classic', image: null },
    { id: 's2', title: 'Key Features', body: 'Detailed roadmap points', notes: '', layout: 'title-body', theme: 'classic', image: null },
  ]);
  const [trashSlides, setTrashSlides] = useState([]);

  const quotaGB = 15;
  const usedGB = files.reduce((s, f) => s + f.size, 0) / 1024;

  useEffect(() => {
    const onKey = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') { e.preventDefault(); setPaletteOpen((v) => !v); }
      if (e.key === 'Escape') { setPaletteOpen(false); setTrashOpen(false); }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  const apps = [
    { key: 'drive', label: 'Drive', icon: Cloud },
    { key: 'docs', label: 'Docs', icon: FileText },
    { key: 'sheets', label: 'Sheets', icon: Table2 },
    { key: 'slides', label: 'Slides', icon: Presentation },
    { key: 'mail', label: 'Mail', icon: MailIcon },
  ];

  const paletteActions = [
    ...apps.map((a) => ({ label: `Go to ${a.label}`, icon: a.icon, run: () => setApp(a.key) })),
    { label: 'Toggle dark mode', icon: dark ? Sun : Moon, run: () => setDark((d) => !d) },
    { label: 'Open Trash', icon: Trash2, run: () => setTrashOpen(true) },
    { label: 'New document', icon: FileText, run: () => { setApp('docs'); } },
    { label: 'New sheet', icon: Table2, run: () => setApp('sheets') },
    { label: 'New slide', icon: Presentation, run: () => setApp('slides') },
    { label: 'Compose email', icon: MailIcon, run: () => setApp('mail') },
  ];

  const restoreFile = (id) => { const it = trashFiles.find((f) => f.id === id); if (!it) return; setFiles((p) => [...p, it]); setTrashFiles((p) => p.filter((f) => f.id !== id)); };
  const restoreDoc = (id) => { const it = trashDocs.find((d) => d.id === id); if (!it) return; setDocs((p) => [...p, it]); setTrashDocs((p) => p.filter((d) => d.id !== id)); };
  const restoreSlide = (id) => { const it = trashSlides.find((s) => s.id === id); if (!it) return; setSlides((p) => [...p, it]); setTrashSlides((p) => p.filter((s) => s.id !== id)); };

  const shell = dark ? 'bg-zinc-950 text-zinc-100' : 'bg-zinc-50 text-zinc-900';

  return (
    <div className={`h-full w-full flex flex-col ${shell} ov-display`} style={{ minHeight: 640 }}>
      <style>{FONT_STYLE}</style>
      <CommandPalette open={paletteOpen} onClose={() => setPaletteOpen(false)} actions={paletteActions} dark={dark} />
      <TrashPanel open={trashOpen} onClose={() => setTrashOpen(false)} dark={dark}
        files={trashFiles} restoreFile={restoreFile} docs={trashDocs} restoreDoc={restoreDoc} slides={trashSlides} restoreSlide={restoreSlide} />

      <header className="h-14 bg-zinc-900 border-b border-zinc-800 flex items-center justify-between px-4 shrink-0">
        <div className="flex items-center space-x-2.5">
          <VaultSeal size={24} />
          <span className="font-semibold text-white tracking-tight text-[15px]">OmniVault</span>
        </div>

        <nav className="flex items-center space-x-1 bg-zinc-800 p-1 rounded-lg">
          {apps.map(({ key, label, icon: Icon }) => (
            <button key={key} onClick={() => setApp(key)}
              className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-md text-sm font-medium transition ${app === key ? 'bg-zinc-950 text-amber-400' : 'text-zinc-400 hover:text-zinc-100'}`}
              style={app === key ? { boxShadow: `inset 0 0 0 1px ${BRASS_DARK}` } : {}}>
              <Icon size={15} /> <span>{label}</span>
            </button>
          ))}
        </nav>

        <div className="flex items-center space-x-2.5">
          <div className="relative hidden md:block">
            <Search size={14} className="absolute left-2.5 top-2 text-zinc-500" />
            <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search workspace..."
              className="pl-8 pr-3 py-1.5 bg-zinc-800 text-zinc-100 placeholder-zinc-500 rounded-full text-xs outline-none w-52" />
          </div>
          <button onClick={() => setPaletteOpen(true)} title="Command palette (Ctrl/Cmd+K)" className="p-1.5 rounded-md text-zinc-400 hover:text-amber-400 hover:bg-zinc-800">
            <Command size={16} />
          </button>
          <button onClick={() => setTrashOpen(true)} title="Trash" className="p-1.5 rounded-md text-zinc-400 hover:text-amber-400 hover:bg-zinc-800">
            <Trash2 size={16} />
          </button>
          <button onClick={() => setDark((d) => !d)} title="Toggle theme" className="p-1.5 rounded-md text-zinc-400 hover:text-amber-400 hover:bg-zinc-800">
            {dark ? <Sun size={16} /> : <Moon size={16} />}
          </button>
          <div className="w-7 h-7 rounded-full flex items-center justify-center font-bold text-[11px] text-zinc-950" style={{ background: BRASS }}>YOU</div>
        </div>
      </header>

      <div className={`px-4 py-1.5 border-b flex items-center gap-3 text-xs ${dark ? 'border-zinc-800 text-zinc-400' : 'border-zinc-200 text-zinc-500'}`}>
        <Lock size={12} />
        <span>Vault storage</span>
        <div className="flex-1 h-1.5 rounded-full bg-zinc-200 max-w-xs overflow-hidden">
          <div className="h-full rounded-full" style={{ width: `${Math.min((usedGB / quotaGB) * 100, 100)}%`, background: BRASS }} />
        </div>
        <span className="ov-mono">{usedGB.toFixed(2)} / {quotaGB} GB</span>
        <span className="ml-auto hidden sm:inline text-zinc-400">Press <kbd className="border rounded px-1 ov-mono">Ctrl K</kbd> to jump anywhere</span>
      </div>

      <main className="flex-1 overflow-hidden flex">
        {app === 'drive' && <DriveModule files={files} setFiles={setFiles} setTrashFiles={setTrashFiles} dark={dark} query={query} />}
        {app === 'docs' && <DocsModule docs={docs} setDocs={setDocs} setTrashDocs={setTrashDocs} dark={dark} query={query} />}
        {app === 'sheets' && <SheetsModule dark={dark} />}
        {app === 'slides' && <SlidesModule slides={slides} setSlides={setSlides} setTrashSlides={setTrashSlides} dark={dark} />}
        {app === 'mail' && <MailModule dark={dark} query={query} />}
      </main>
    </div>
  );
}

// ============================================================================
// DRIVE
// ============================================================================
function DriveModule({ files, setFiles, setTrashFiles, dark, query }) {
  const inputRef = useRef(null);
  const visible = files.filter((f) => f.name.toLowerCase().includes(query.toLowerCase()));

  const onUpload = (e) => {
    const chosen = Array.from(e.target.files || []);
    const next = chosen.map((f) => ({ id: uid('f'), name: f.name, size: Math.round((f.size / (1024 * 1024)) * 100) / 100, modified: 'Just now' }));
    setFiles((prev) => [...next, ...prev]);
    e.target.value = '';
  };

  const trash = (f) => { setTrashFiles((p) => [...p, f]); setFiles((prev) => prev.filter((x) => x.id !== f.id)); };

  return (
    <div className={`flex-1 overflow-y-auto ov-scrollbar p-6 ${dark ? 'bg-zinc-950' : 'bg-zinc-50'}`}>
      <div className="flex items-center justify-between mb-5">
        <h1 className="text-xl font-semibold">Drive</h1>
        <button onClick={() => inputRef.current?.click()} className="flex items-center space-x-2 text-zinc-950 px-4 py-2 rounded-lg text-sm font-semibold shadow-sm" style={{ background: BRASS }}>
          <Upload size={15} /> <span>Upload</span>
        </button>
        <input ref={inputRef} type="file" multiple className="hidden" onChange={onUpload} />
      </div>
      {visible.length === 0 ? (
        <div className={`text-center py-20 rounded-xl border-2 border-dashed ${dark ? 'border-zinc-800 text-zinc-600' : 'border-zinc-300 text-zinc-400'}`}>No files match — upload something to get started.</div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {visible.map((f) => (
            <div key={f.id} className={`rounded-xl border p-4 ${dark ? 'bg-zinc-900 border-zinc-800' : 'bg-white border-zinc-200'}`}>
              <div className="flex items-start justify-between">
                <FileText size={18} style={{ color: BRASS }} />
                <button onClick={() => trash(f)} className="text-zinc-400 hover:text-red-500"><Trash2 size={14} /></button>
              </div>
              <p className="text-sm font-medium mt-2 truncate">{f.name}</p>
              <p className="text-xs text-zinc-500 mt-0.5 ov-mono">{f.size} MB · {f.modified}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ============================================================================
// DOCS — rich text, comments, version history, find/replace, print
// ============================================================================
function DocsModule({ docs, setDocs, setTrashDocs, dark, query }) {
  const [activeId, setActiveId] = useState(docs[0]?.id || null);
  const [showFind, setShowFind] = useState(false);
  const [findText, setFindText] = useState('');
  const [replaceText, setReplaceText] = useState('');
  const [wordCount, setWordCount] = useState(0);
  const editorRef = useRef(null);
  const active = docs.find((d) => d.id === activeId);
  const visible = docs.filter((d) => d.name.toLowerCase().includes(query.toLowerCase()));

  useEffect(() => {
    if (editorRef.current && active) {
      editorRef.current.innerHTML = active.html;
      updateCount();
    }
  }, [activeId]);

  const updateCount = () => {
    const text = editorRef.current?.innerText || '';
    setWordCount(text.trim() ? text.trim().split(/\s+/).length : 0);
  };

  const exec = (cmd, val = null) => { editorRef.current?.focus(); document.execCommand(cmd, false, val); saveContent(); };

  const saveContent = () => {
    if (!editorRef.current) return;
    const html = editorRef.current.innerHTML;
    setDocs((prev) => prev.map((d) => (d.id === activeId ? { ...d, html } : d)));
    updateCount();
  };

  const newDoc = () => {
    const id = uid('d');
    setDocs((prev) => [...prev, { id, name: `Untitled ${prev.length + 1}`, html: '<p>Start typing...</p>', versions: [], comments: [] }]);
    setActiveId(id);
  };

  const trashDoc = (d) => { setTrashDocs((p) => [...p, d]); setDocs((prev) => prev.filter((x) => x.id !== d.id)); setActiveId((cur) => (cur === d.id ? docs.find((x) => x.id !== d.id)?.id : cur)); };

  const insertLink = () => { const url = prompt('Link URL:'); if (url) exec('createLink', url); };
  const insertImage = () => {
    const input = document.createElement('input'); input.type = 'file'; input.accept = 'image/*';
    input.onchange = (e) => {
      const file = e.target.files[0]; if (!file) return;
      const reader = new FileReader();
      reader.onload = () => exec('insertImage', reader.result);
      reader.readAsDataURL(file);
    };
    input.click();
  };
  const insertTable = () => {
    const rows = 3, cols = 3;
    let html = '<table style="border-collapse:collapse;width:100%;margin:8px 0;">';
    for (let r = 0; r < rows; r++) { html += '<tr>'; for (let c = 0; c < cols; c++) html += '<td style="border:1px solid #ccc;padding:6px;min-width:60px;">&nbsp;</td>'; html += '</tr>'; }
    html += '</table><p></p>';
    exec('insertHTML', html);
  };

  const addComment = () => {
    const sel = window.getSelection();
    if (!sel || sel.isCollapsed || sel.rangeCount === 0) { alert('Select some text first.'); return; }
    const range = sel.getRangeAt(0);
    const anchorText = sel.toString();
    const text = prompt('Comment:');
    if (!text) return;
    const id = uid('c');
    const mark = document.createElement('mark');
    mark.className = 'ov-comment-mark';
    mark.dataset.cid = id;
    try { range.surroundContents(mark); } catch { const contents = range.extractContents(); mark.appendChild(contents); range.insertNode(mark); }
    setDocs((prev) => prev.map((d) => (d.id === activeId ? { ...d, comments: [...(d.comments || []), { id, text, anchorText }] } : d)));
    saveContent();
  };
  const removeComment = (cid) => {
    const el = editorRef.current?.querySelector(`[data-cid="${cid}"]`);
    if (el) { const parent = el.parentNode; while (el.firstChild) parent.insertBefore(el.firstChild, el); parent.removeChild(el); }
    setDocs((prev) => prev.map((d) => (d.id === activeId ? { ...d, comments: (d.comments || []).filter((c) => c.id !== cid) } : d)));
    saveContent();
  };

  const saveVersion = () => {
    setDocs((prev) => prev.map((d) => (d.id === activeId ? { ...d, versions: [{ html: d.html, savedAt: new Date().toLocaleString() }, ...(d.versions || [])].slice(0, 10) } : d)));
  };
  const revertVersion = (html) => { editorRef.current.innerHTML = html; saveContent(); };

  const runReplace = () => {
    if (!editorRef.current || !findText) return;
    editorRef.current.innerHTML = editorRef.current.innerHTML.split(findText).join(replaceText);
    saveContent();
  };

  const printDoc = () => {
    const w = window.open('', 'print-window', 'width=800,height=900');
    if (!w) { alert('Enable pop-ups to print/export.'); return; }
    w.document.write(`<html><head><title>${active.name}</title></head><body style="font-family:Georgia,serif;max-width:720px;margin:40px auto;">${active.html}</body></html>`);
    w.document.close();
    setTimeout(() => w.print(), 200);
  };

  const toolBtn = (icon, cmd, val = null, title = '') => {
    const Icon = icon;
    return (
      <button title={title} onMouseDown={(e) => e.preventDefault()} onClick={() => exec(cmd, val)}
        className="p-1.5 rounded hover:bg-zinc-200/60 dark:hover:bg-zinc-800 text-zinc-600"><Icon size={15} /></button>
    );
  };

  if (!active) return <div className="flex-1 flex items-center justify-center text-zinc-400">No documents — create one to get started.</div>;

  return (
    <div className="flex-1 flex overflow-hidden">
      <aside className={`w-56 border-r p-3 space-y-2 overflow-y-auto ov-scrollbar ${dark ? 'bg-zinc-900 border-zinc-800' : 'bg-white border-zinc-200'}`}>
        <button onClick={newDoc} className="w-full flex items-center justify-center space-x-2 py-2 rounded-lg text-sm font-semibold text-zinc-950" style={{ background: BRASS }}>
          <Plus size={15} /> <span>New doc</span>
        </button>
        {visible.map((d) => (
          <div key={d.id} className="group relative">
            <button onClick={() => setActiveId(d.id)}
              className={`w-full text-left px-3 py-2 rounded-lg text-sm truncate pr-7 ${activeId === d.id ? 'bg-amber-500/10 text-amber-500 font-medium' : dark ? 'text-zinc-300 hover:bg-zinc-800' : 'text-zinc-600 hover:bg-zinc-100'}`}>
              {d.name}
            </button>
            <button onClick={() => trashDoc(d)} className="absolute right-2 top-2 opacity-0 group-hover:opacity-100 text-zinc-400 hover:text-red-500"><Trash2 size={13} /></button>
          </div>
        ))}
      </aside>

      <div className={`flex-1 flex flex-col ${dark ? 'bg-zinc-950' : 'bg-zinc-100'}`}>
        <div className={`flex flex-wrap items-center gap-0.5 px-3 py-2 border-b ${dark ? 'bg-zinc-900 border-zinc-800' : 'bg-white border-zinc-200'}`}>
          {toolBtn(Undo2, 'undo', null, 'Undo')}
          {toolBtn(Redo2, 'redo', null, 'Redo')}
          <div className="w-px h-4 bg-zinc-300 mx-1" />
          {toolBtn(Bold, 'bold', null, 'Bold')}
          {toolBtn(Italic, 'italic', null, 'Italic')}
          {toolBtn(Underline, 'underline', null, 'Underline')}
          {toolBtn(Strikethrough, 'strikeThrough', null, 'Strikethrough')}
          <div className="w-px h-4 bg-zinc-300 mx-1" />
          {toolBtn(Heading1, 'formatBlock', 'H2', 'Heading 1')}
          {toolBtn(Heading2, 'formatBlock', 'H3', 'Heading 2')}
          {toolBtn(Heading3, 'formatBlock', 'H4', 'Heading 3')}
          {toolBtn(Quote, 'formatBlock', 'BLOCKQUOTE', 'Quote')}
          {toolBtn(Code, 'formatBlock', 'PRE', 'Code block')}
          <div className="w-px h-4 bg-zinc-300 mx-1" />
          {toolBtn(AlignLeft, 'justifyLeft', null, 'Align left')}
          {toolBtn(AlignCenter, 'justifyCenter', null, 'Align center')}
          {toolBtn(AlignRight, 'justifyRight', null, 'Align right')}
          {toolBtn(AlignJustify, 'justifyFull', null, 'Justify')}
          <div className="w-px h-4 bg-zinc-300 mx-1" />
          {toolBtn(List, 'insertUnorderedList', null, 'Bullet list')}
          {toolBtn(ListOrdered, 'insertOrderedList', null, 'Numbered list')}
          <div className="w-px h-4 bg-zinc-300 mx-1" />
          <button title="Text color" onMouseDown={(e) => e.preventDefault()} className="p-1 rounded hover:bg-zinc-200/60">
            <input type="color" onChange={(e) => exec('foreColor', e.target.value)} className="w-5 h-5 cursor-pointer" />
          </button>
          <button title="Highlight" onMouseDown={(e) => e.preventDefault()} className="p-1 rounded hover:bg-zinc-200/60">
            <input type="color" defaultValue="#fff59d" onChange={(e) => exec('hiliteColor', e.target.value)} className="w-5 h-5 cursor-pointer" />
          </button>
          <div className="w-px h-4 bg-zinc-300 mx-1" />
          <button title="Insert link" onMouseDown={(e) => e.preventDefault()} onClick={insertLink} className="p-1.5 rounded hover:bg-zinc-200/60 text-zinc-600"><Link2 size={15} /></button>
          <button title="Insert image" onMouseDown={(e) => e.preventDefault()} onClick={insertImage} className="p-1.5 rounded hover:bg-zinc-200/60 text-zinc-600"><ImageIcon size={15} /></button>
          <button title="Insert table" onMouseDown={(e) => e.preventDefault()} onClick={insertTable} className="p-1.5 rounded hover:bg-zinc-200/60 text-zinc-600"><TableIcon size={15} /></button>
          <button title="Comment selection" onMouseDown={(e) => e.preventDefault()} onClick={addComment} className="p-1.5 rounded hover:bg-zinc-200/60 text-zinc-600"><MessageSquare size={15} /></button>
          <div className="w-px h-4 bg-zinc-300 mx-1" />
          <button title="Find & replace" onClick={() => setShowFind((v) => !v)} className="p-1.5 rounded hover:bg-zinc-200/60 text-zinc-600"><Search size={15} /></button>
          <button title="Save version" onClick={saveVersion} className="p-1.5 rounded hover:bg-zinc-200/60 text-zinc-600"><History size={15} /></button>
          <button title="Print / export PDF" onClick={printDoc} className="p-1.5 rounded hover:bg-zinc-200/60 text-zinc-600"><Printer size={15} /></button>
          <span className="ml-auto text-xs text-zinc-400 ov-mono">{wordCount} words</span>
        </div>

        {showFind && (
          <div className={`flex items-center gap-2 px-3 py-2 border-b text-sm ${dark ? 'bg-zinc-900 border-zinc-800' : 'bg-white border-zinc-200'}`}>
            <input value={findText} onChange={(e) => setFindText(e.target.value)} placeholder="Find" className={`px-2 py-1 rounded border text-sm outline-none ${dark ? 'bg-zinc-950 border-zinc-700' : 'border-zinc-300'}`} />
            <input value={replaceText} onChange={(e) => setReplaceText(e.target.value)} placeholder="Replace with" className={`px-2 py-1 rounded border text-sm outline-none ${dark ? 'bg-zinc-950 border-zinc-700' : 'border-zinc-300'}`} />
            <button onClick={runReplace} className="px-3 py-1 rounded text-xs font-semibold text-zinc-950" style={{ background: BRASS }}>Replace all</button>
          </div>
        )}

        <div className="flex-1 flex overflow-hidden">
          <div className="flex-1 overflow-y-auto ov-scrollbar p-8 flex justify-center">
            <div ref={editorRef} contentEditable suppressContentEditableWarning onInput={saveContent}
              onClick={(e) => { if (e.target.dataset.cid) { /* click on comment mark */ } }}
              className={`ov-serif w-full max-w-[720px] min-h-[600px] rounded-lg shadow-sm p-10 text-[15px] leading-relaxed ${dark ? 'bg-zinc-900 text-zinc-100' : 'bg-white text-zinc-900'}`} />
          </div>

          {(active.comments?.length > 0 || active.versions?.length > 0) && (
            <aside className={`w-64 border-l p-3 overflow-y-auto ov-scrollbar space-y-4 ${dark ? 'bg-zinc-900 border-zinc-800' : 'bg-white border-zinc-200'}`}>
              {active.comments?.length > 0 && (
                <div>
                  <p className="text-xs font-semibold text-zinc-400 mb-2 flex items-center gap-1"><MessageSquare size={12} /> COMMENTS</p>
                  {active.comments.map((c) => (
                    <div key={c.id} className={`text-xs rounded-lg p-2 mb-2 ${dark ? 'bg-zinc-800' : 'bg-zinc-50'}`}>
                      <p className="text-zinc-400 italic truncate">"{c.anchorText}"</p>
                      <p className="mt-1">{c.text}</p>
                      <button onClick={() => removeComment(c.id)} className="text-[10px] text-red-500 mt-1">Resolve</button>
                    </div>
                  ))}
                </div>
              )}
              {active.versions?.length > 0 && (
                <div>
                  <p className="text-xs font-semibold text-zinc-400 mb-2 flex items-center gap-1"><History size={12} /> VERSIONS</p>
                  {active.versions.map((v, i) => (
                    <div key={i} className={`text-xs rounded-lg p-2 mb-2 ${dark ? 'bg-zinc-800' : 'bg-zinc-50'}`}>
                      <p className="text-zinc-400">{v.savedAt}</p>
                      <button onClick={() => revertVersion(v.html)} className="text-[10px] font-medium mt-1" style={{ color: BRASS }}>Revert</button>
                    </div>
                  ))}
                </div>
              )}
            </aside>
          )}
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// SHEETS — multi-tab, cell formatting, ranges/IF, CSV/XLSX, charts
// ============================================================================
const emptySheet = () => ({ grid: {}, styles: {}, formats: {} });

function SheetsModule({ dark }) {
  const [sheets, setSheets] = useState({
    Sheet1: {
      grid: { A1: 'Item', B1: 'Cost', C1: 'Qty', D1: 'Total', A2: 'Widget A', B2: '10', C2: '5', D2: '=B2*C2', A3: 'Widget B', B3: '20', C3: '3', D3: '=B3*C3', A4: '', B4: '', C4: 'Sum', D4: '=SUM(D2:D3)' },
      styles: {}, formats: { B2: 'currency', B3: 'currency', D2: 'currency', D3: 'currency', D4: 'currency' },
    },
  });
  const [activeSheet, setActiveSheet] = useState('Sheet1');
  const [activeCell, setActiveCell] = useState('A1');
  const [showChart, setShowChart] = useState(false);
  const [chartCol, setChartCol] = useState('D');
  const fileRef = useRef(null);

  const cur = sheets[activeSheet];
  const cols = ['A', 'B', 'C', 'D', 'E', 'F', 'G'];
  const rows = Array.from({ length: 16 }, (_, i) => i + 1);

  const updateSheet = (patch) => setSheets((prev) => ({ ...prev, [activeSheet]: { ...prev[activeSheet], ...patch } }));
  const setCell = (key, val) => updateSheet({ grid: { ...cur.grid, [key]: val } });
  const toggleStyle = (key, prop) => updateSheet({ styles: { ...cur.styles, [key]: { ...cur.styles[key], [prop]: !cur.styles[key]?.[prop] } } });
  const setColor = (key, prop, val) => updateSheet({ styles: { ...cur.styles, [key]: { ...cur.styles[key], [prop]: val } } });
  const setFormat = (key, fmt) => updateSheet({ formats: { ...cur.formats, [key]: fmt } });

  const addSheet = () => {
    let n = Object.keys(sheets).length + 1;
    let name = `Sheet${n}`;
    while (sheets[name]) { n++; name = `Sheet${n}`; }
    setSheets((prev) => ({ ...prev, [name]: emptySheet() }));
    setActiveSheet(name);
  };
  const deleteSheet = (name) => {
    if (Object.keys(sheets).length <= 1) return;
    const rest = { ...sheets }; delete rest[name];
    setSheets(rest);
    if (activeSheet === name) setActiveSheet(Object.keys(rest)[0]);
  };
  const renameSheet = (name) => {
    const next = prompt('Rename sheet:', name);
    if (!next || sheets[next]) return;
    const rest = {}; Object.entries(sheets).forEach(([k, v]) => { rest[k === name ? next : k] = v; });
    setSheets(rest);
    if (activeSheet === name) setActiveSheet(next);
  };

  const importCSV = (e) => {
    const file = e.target.files[0]; if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      const parsed = Papa.parse(reader.result, { skipEmptyLines: true });
      const grid = {};
      parsed.data.forEach((row, rIdx) => row.forEach((val, cIdx) => { grid[numToCol(cIdx + 1) + (rIdx + 1)] = val; }));
      const name = file.name.replace(/\.csv$/i, '') || 'Imported';
      setSheets((prev) => ({ ...prev, [name]: { grid, styles: {}, formats: {} } }));
      setActiveSheet(name);
    };
    reader.readAsText(file);
    e.target.value = '';
  };

  const boundsOf = (grid) => {
    let maxRow = 1, maxCol = 1;
    Object.keys(grid).forEach((k) => { const p = parseRef(k); if (p) { maxRow = Math.max(maxRow, p.row); maxCol = Math.max(maxCol, colToNum(p.col)); } });
    return { maxRow, maxCol };
  };
  const toAOA = () => {
    const { maxRow, maxCol } = boundsOf(cur.grid);
    const aoa = [];
    for (let r = 1; r <= maxRow; r++) { const row = []; for (let c = 1; c <= maxCol; c++) row.push(displayCell(numToCol(c) + r, cur.grid, cur.formats)); aoa.push(row); }
    return aoa;
  };
  const exportCSV = () => {
    const csv = Papa.unparse(toAOA());
    const blob = new Blob([csv], { type: 'text/csv' });
    const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = `${activeSheet}.csv`; a.click();
  };
  const exportXLSX = () => {
    const ws = XLSX.utils.aoa_to_sheet(toAOA());
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, activeSheet.slice(0, 31));
    XLSX.writeFile(wb, `${activeSheet}.xlsx`);
  };

  const chartData = useMemo(() => {
    const { maxRow } = boundsOf(cur.grid);
    const out = [];
    for (let r = 2; r <= maxRow; r++) {
      const label = displayCell('A' + r, cur.grid, cur.formats);
      const val = parseFloat(evaluateFormula(String(cur.grid[chartCol + r] ?? ''), cur.grid)) || parseFloat(cur.grid[chartCol + r]) || 0;
      if (label) out.push({ name: String(label), value: val });
    }
    return out;
  }, [cur, chartCol]);

  const cellStyle = (key) => {
    const s = cur.styles[key] || {};
    return { fontWeight: s.bold ? 700 : 400, fontStyle: s.italic ? 'italic' : 'normal', color: s.color || undefined, background: s.bg || undefined };
  };

  return (
    <div className={`flex-1 flex flex-col overflow-hidden ${dark ? 'bg-zinc-950' : 'bg-white'}`}>
      <div className={`flex flex-wrap items-center gap-1 px-3 py-2 border-b ${dark ? 'border-zinc-800' : 'border-zinc-200'}`}>
        <span className="ov-mono text-xs font-bold min-w-[32px]" style={{ color: BRASS_DARK }}>{activeCell}</span>
        <div className="w-px h-4 bg-zinc-300" />
        <span className="text-zinc-400 italic text-xs">fx</span>
        <input value={cur.grid[activeCell] ?? ''} onChange={(e) => setCell(activeCell, e.target.value)} placeholder="Value, =SUM(A1:A5), =IF(A1>5,1,0)"
          className={`flex-1 border rounded px-2 py-1 text-sm outline-none ov-mono min-w-[160px] ${dark ? 'bg-zinc-900 border-zinc-700 text-zinc-100' : 'bg-white border-zinc-300'}`} />
        <div className="w-px h-4 bg-zinc-300 mx-1" />
        <button title="Bold" onClick={() => toggleStyle(activeCell, 'bold')} className="p-1.5 rounded hover:bg-zinc-200/60 text-zinc-600"><Bold size={14} /></button>
        <button title="Italic" onClick={() => toggleStyle(activeCell, 'italic')} className="p-1.5 rounded hover:bg-zinc-200/60 text-zinc-600"><Italic size={14} /></button>
        <input title="Text color" type="color" onChange={(e) => setColor(activeCell, 'color', e.target.value)} className="w-5 h-5 cursor-pointer" />
        <input title="Fill color" type="color" onChange={(e) => setColor(activeCell, 'bg', e.target.value)} className="w-5 h-5 cursor-pointer" />
        <select value={cur.formats[activeCell] || 'general'} onChange={(e) => setFormat(activeCell, e.target.value)}
          className={`text-xs rounded border px-1.5 py-1 ${dark ? 'bg-zinc-900 border-zinc-700' : 'border-zinc-300'}`}>
          <option value="general">General</option>
          <option value="currency">Currency</option>
          <option value="percent">Percent</option>
        </select>
        <div className="w-px h-4 bg-zinc-300 mx-1" />
        <button title="Import CSV" onClick={() => fileRef.current?.click()} className="p-1.5 rounded hover:bg-zinc-200/60 text-zinc-600"><Upload size={14} /></button>
        <input ref={fileRef} type="file" accept=".csv" className="hidden" onChange={importCSV} />
        <button title="Export CSV" onClick={exportCSV} className="p-1.5 rounded hover:bg-zinc-200/60 text-zinc-600"><Download size={14} /></button>
        <button title="Export XLSX" onClick={exportXLSX} className="p-1.5 rounded hover:bg-zinc-200/60 text-zinc-600"><FileSpreadsheet size={14} /></button>
        <button title="Insert chart" onClick={() => setShowChart((v) => !v)} className="p-1.5 rounded hover:bg-zinc-200/60 text-zinc-600"><BarChart3 size={14} /></button>
      </div>

      {showChart && (
        <div className={`px-4 py-3 border-b ${dark ? 'border-zinc-800' : 'border-zinc-200'}`}>
          <div className="flex items-center gap-2 mb-2 text-xs">
            <span>Chart column (values):</span>
            <select value={chartCol} onChange={(e) => setChartCol(e.target.value)} className={`rounded border px-1.5 py-0.5 ${dark ? 'bg-zinc-900 border-zinc-700' : 'border-zinc-300'}`}>
              {cols.map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
            <span className="text-zinc-400">(labels come from column A)</span>
          </div>
          <ResponsiveContainer width="100%" height={180}>
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.2} />
              <XAxis dataKey="name" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip />
              <Bar dataKey="value" fill={BRASS} radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      <div className="flex-1 overflow-auto ov-scrollbar">
        <table className="border-collapse w-full">
          <thead>
            <tr>
              <th className={`w-10 border sticky top-0 z-10 ${dark ? 'bg-zinc-900 border-zinc-800' : 'bg-zinc-100 border-zinc-300'}`} />
              {cols.map((c) => <th key={c} className={`border sticky top-0 z-10 text-xs font-semibold py-1.5 ov-mono ${dark ? 'bg-zinc-900 border-zinc-800 text-zinc-400' : 'bg-zinc-100 border-zinc-300 text-zinc-500'}`}>{c}</th>)}
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r}>
                <td className={`border text-center text-xs ov-mono ${dark ? 'bg-zinc-900 border-zinc-800 text-zinc-500' : 'bg-zinc-100 border-zinc-300 text-zinc-400'}`}>{r}</td>
                {cols.map((c) => {
                  const key = `${c}${r}`;
                  const isActive = activeCell === key;
                  return (
                    <td key={key} onClick={() => setActiveCell(key)} className={`border p-0 h-8 ${dark ? 'border-zinc-800' : 'border-zinc-200'}`}
                      style={isActive ? { boxShadow: `inset 0 0 0 2px ${BRASS}` } : {}}>
                      <div className="px-2 py-1 text-sm truncate" style={cellStyle(key)}>{String(displayCell(key, cur.grid, cur.formats))}</div>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className={`flex items-center gap-1 px-2 py-1.5 border-t overflow-x-auto ${dark ? 'border-zinc-800 bg-zinc-900' : 'border-zinc-200 bg-zinc-50'}`}>
        {Object.keys(sheets).map((name) => (
          <div key={name} className="flex items-center">
            <button onClick={() => setActiveSheet(name)} onDoubleClick={() => renameSheet(name)}
              className={`px-3 py-1 rounded-t-md text-xs font-medium ${activeSheet === name ? 'bg-white dark:bg-zinc-950 text-amber-600' : 'text-zinc-500'}`}>{name}</button>
            {Object.keys(sheets).length > 1 && <button onClick={() => deleteSheet(name)} className="text-zinc-400 hover:text-red-500 -ml-1"><X size={11} /></button>}
          </div>
        ))}
        <button onClick={addSheet} className="p-1 rounded hover:bg-zinc-200/60 text-zinc-500"><Plus size={14} /></button>
      </div>
      <p className="text-[11px] text-zinc-500 px-4 py-1.5">Formulas: SUM/AVERAGE/MIN/MAX/COUNT over ranges (e.g. <span className="ov-mono">=SUM(A1:A5)</span>), IF, and arithmetic — evaluated by mathjs's sandboxed parser, never raw code execution.</p>
    </div>
  );
}

// ============================================================================
// SLIDES — themes, layouts, notes, present mode, reorder, duplicate, print
// ============================================================================
const THEMES = {
  classic: { bg: '#ffffff', fg: '#18181b', accent: BRASS },
  midnight: { bg: '#0f172a', fg: '#f1f5f9', accent: '#38bdf8' },
  sunset: { bg: '#431407', fg: '#fef3c7', accent: '#fb923c' },
  mono: { bg: '#fafafa', fg: '#111111', accent: '#111111' },
};

function SlidesModule({ slides, setSlides, setTrashSlides, dark }) {
  const [activeIdx, setActiveIdx] = useState(0);
  const [presenting, setPresenting] = useState(false);
  const active = slides[activeIdx];

  useEffect(() => {
    if (!presenting) return;
    const onKey = (e) => {
      if (e.key === 'ArrowRight') setActiveIdx((i) => Math.min(slides.length - 1, i + 1));
      if (e.key === 'ArrowLeft') setActiveIdx((i) => Math.max(0, i - 1));
      if (e.key === 'Escape') setPresenting(false);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [presenting, slides.length]);

  const update = (field, val) => setSlides((prev) => prev.map((s, i) => (i === activeIdx ? { ...s, [field]: val } : s)));
  const addSlide = (layout = 'title-body') => { setSlides((prev) => [...prev, { id: uid('s'), title: 'New slide', body: 'Bullet point...', notes: '', layout, theme: active?.theme || 'classic', image: null }]); setActiveIdx(slides.length); };
  const duplicateSlide = (idx) => { const copy = { ...slides[idx], id: uid('s') }; setSlides((prev) => [...prev.slice(0, idx + 1), copy, ...prev.slice(idx + 1)]); setActiveIdx(idx + 1); };
  const moveSlide = (idx, dir) => {
    const j = idx + dir; if (j < 0 || j >= slides.length) return;
    const next = [...slides]; [next[idx], next[j]] = [next[j], next[idx]]; setSlides(next); setActiveIdx(j);
  };
  const trashSlide = (idx) => { setTrashSlides((p) => [...p, slides[idx]]); setSlides((prev) => prev.filter((_, i) => i !== idx)); setActiveIdx((i) => Math.max(0, i - (idx <= activeIdx ? 1 : 0))); };
  const insertImage = () => {
    const input = document.createElement('input'); input.type = 'file'; input.accept = 'image/*';
    input.onchange = (e) => { const f = e.target.files[0]; if (!f) return; const r = new FileReader(); r.onload = () => update('image', r.result); r.readAsDataURL(f); };
    input.click();
  };
  const printDeck = () => {
    const w = window.open('', 'print-deck', 'width=900,height=700');
    if (!w) { alert('Enable pop-ups to print/export.'); return; }
    const html = slides.map((s) => `<div style="page-break-after:always;padding:60px;text-align:center;"><h1>${s.title}</h1><p>${s.body}</p></div>`).join('');
    w.document.write(`<html><body>${html}</body></html>`); w.document.close();
    setTimeout(() => w.print(), 200);
  };

  if (!active) return (
    <div className="flex-1 flex flex-col items-center justify-center text-zinc-400 space-y-3">
      <p>No slides — add one to start.</p>
      <button onClick={() => addSlide()} className="px-4 py-2 rounded-lg text-sm font-semibold text-zinc-950" style={{ background: BRASS }}>Add slide</button>
    </div>
  );

  const theme = THEMES[active.theme] || THEMES.classic;

  if (presenting) {
    return (
      <div className="fixed inset-0 z-50 flex flex-col items-center justify-center" style={{ background: theme.bg, color: theme.fg }}>
        <button onClick={() => setPresenting(false)} className="absolute top-4 right-4 text-sm opacity-70">Exit (Esc)</button>
        <h1 className="text-5xl font-bold mb-6" style={{ color: theme.accent }}>{active.title}</h1>
        <p className="text-xl max-w-2xl text-center whitespace-pre-line">{active.body}</p>
        {active.image && <img src={active.image} alt="" className="max-h-64 mt-8 rounded-lg" />}
        <p className="absolute bottom-6 text-xs opacity-50">{activeIdx + 1} / {slides.length} — use ← →</p>
      </div>
    );
  }

  return (
    <div className={`flex-1 flex overflow-hidden ${dark ? 'bg-zinc-950' : 'bg-zinc-100'}`}>
      <aside className={`w-56 border-r p-3 space-y-3 overflow-y-auto ov-scrollbar ${dark ? 'bg-zinc-900 border-zinc-800' : 'bg-white border-zinc-200'}`}>
        <div className="grid grid-cols-2 gap-1.5">
          <button onClick={() => addSlide('title')} className="flex items-center justify-center space-x-1 py-1.5 rounded-lg text-xs font-semibold text-zinc-950" style={{ background: BRASS }}><Plus size={13} /><span>Title</span></button>
          <button onClick={() => addSlide('title-body')} className="flex items-center justify-center space-x-1 py-1.5 rounded-lg text-xs font-semibold text-zinc-950" style={{ background: BRASS }}><Plus size={13} /><span>Content</span></button>
        </div>
        <button onClick={() => setPresenting(true)} className="w-full flex items-center justify-center space-x-2 py-1.5 rounded-lg text-xs font-medium border border-zinc-300 dark:border-zinc-700"><Play size={13} /><span>Present</span></button>
        <button onClick={printDeck} className="w-full flex items-center justify-center space-x-2 py-1.5 rounded-lg text-xs font-medium border border-zinc-300 dark:border-zinc-700"><Printer size={13} /><span>Print / export</span></button>

        {slides.map((s, idx) => (
          <div key={s.id} onClick={() => setActiveIdx(idx)} className={`relative p-2 rounded-lg border cursor-pointer group ${activeIdx === idx ? 'border-amber-500' : dark ? 'border-zinc-800' : 'border-zinc-200'}`}>
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-bold text-zinc-400">{idx + 1}</span>
              <div className="flex opacity-0 group-hover:opacity-100 gap-0.5">
                <button onClick={(e) => { e.stopPropagation(); moveSlide(idx, -1); }}><ChevronUp size={11} /></button>
                <button onClick={(e) => { e.stopPropagation(); moveSlide(idx, 1); }}><ChevronDown size={11} /></button>
                <button onClick={(e) => { e.stopPropagation(); duplicateSlide(idx); }}><Copy size={11} /></button>
                <button onClick={(e) => { e.stopPropagation(); trashSlide(idx); }}><Trash2 size={11} /></button>
              </div>
            </div>
            <div className="h-16 rounded flex flex-col items-center justify-center text-center px-2 mt-1" style={{ background: (THEMES[s.theme] || THEMES.classic).bg, color: (THEMES[s.theme] || THEMES.classic).fg }}>
              <p className="text-[10px] font-bold truncate w-full">{s.title}</p>
              <p className="text-[8px] opacity-60 truncate w-full">{s.body}</p>
            </div>
          </div>
        ))}
      </aside>

      <div className="flex-1 flex flex-col items-center justify-center p-8 space-y-4">
        <div className="flex items-center gap-2 text-xs">
          <span className="text-zinc-400">Theme:</span>
          {Object.keys(THEMES).map((t) => (
            <button key={t} onClick={() => update('theme', t)} className={`w-5 h-5 rounded-full border-2 ${active.theme === t ? 'border-amber-500' : 'border-transparent'}`} style={{ background: THEMES[t].bg }} title={t} />
          ))}
          <button onClick={insertImage} className="ml-3 flex items-center space-x-1 text-zinc-500"><ImageIcon size={13} /><span>Add image</span></button>
        </div>

        <div className="w-full max-w-[760px] aspect-video rounded-xl shadow-md p-12 flex flex-col items-center justify-center text-center space-y-4" style={{ background: theme.bg, color: theme.fg }}>
          <input value={active.title} onChange={(e) => update('title', e.target.value)} className="ov-display text-3xl font-bold text-center outline-none bg-transparent w-full" style={{ color: theme.accent }} />
          {active.layout !== 'title' && <textarea value={active.body} onChange={(e) => update('body', e.target.value)} className="text-base text-center outline-none bg-transparent w-full resize-none h-20 opacity-90" />}
          {active.image && <img src={active.image} alt="" className="max-h-32 rounded" />}
        </div>

        <textarea value={active.notes} onChange={(e) => update('notes', e.target.value)} placeholder="Speaker notes..."
          className={`w-full max-w-[760px] text-xs rounded-lg border p-2 outline-none resize-none h-14 ${dark ? 'bg-zinc-900 border-zinc-800 text-zinc-300' : 'bg-white border-zinc-200'}`} />
      </div>
    </div>
  );
}

// ============================================================================
// MAIL — labels, archive, attachments, signature, shortcuts, undo send, bulk
// ============================================================================
function MailModule({ dark, query }) {
  const [mails, setMails] = useState([
    { id: 'm1', from: 'team@omnivault.io', subject: 'Weekly storage digest', preview: 'Your workspace used 165 MB this week...', time: '09:12', read: false, starred: true, label: 'Work' },
    { id: 'm2', from: 'security@omnivault.io', subject: 'New sign-in detected', preview: 'A sign-in was detected from a new device...', time: 'Yesterday', read: true, starred: false, label: 'Important' },
  ]);
  const [archived, setArchived] = useState([]);
  const [trashed, setTrashed] = useState([]);
  const [snoozed, setSnoozed] = useState([]);
  const [sent, setSent] = useState([]);
  const [selected, setSelected] = useState([]);
  const [activeId, setActiveId] = useState('m1');
  const [composing, setComposing] = useState(false);
  const [draft, setDraft] = useState({ to: '', subject: '', body: '', attachments: [] });
  const [folder, setFolder] = useState('inbox');
  const [labelFilter, setLabelFilter] = useState('All');
  const [signature, setSignature] = useState('— Sent from OmniVault');
  const [showSettings, setShowSettings] = useState(false);
  const [pendingSend, setPendingSend] = useState(null);
  const searchRef = useRef(null);

  const folders = { inbox: mails, archive: archived, trash: trashed, snoozed, sent };
  const labels = ['All', 'Work', 'Personal', 'Important'];

  const visible = (folders[folder] || []).filter((m) => {
    const text = (m.subject + (m.from || m.to || '')).toLowerCase();
    const matchQ = text.includes(query.toLowerCase());
    const matchLabel = folder !== 'inbox' || labelFilter === 'All' || m.label === labelFilter;
    return matchQ && matchLabel;
  });
  const active = mails.find((m) => m.id === activeId);

  useEffect(() => {
    const onKey = (e) => {
      const typing = ['INPUT', 'TEXTAREA'].includes(document.activeElement?.tagName);
      if (typing) return;
      if (e.key === 'c') startCompose();
      if (e.key === '/') { e.preventDefault(); searchRef.current?.focus(); }
      if (e.key === 'r' && active) startCompose({ to: active.from, subject: `Re: ${active.subject}`, body: `\n\n---- Original ----\n${active.preview}`, attachments: [] });
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [active]);

  const openMail = (id) => setMails((prev) => prev.map((m) => (m.id === id ? { ...m, read: true } : m)));
  const toggleStar = (id) => setMails((prev) => prev.map((m) => (m.id === id ? { ...m, starred: !m.starred } : m)));
  const setLabel = (id, label) => setMails((prev) => prev.map((m) => (m.id === id ? { ...m, label } : m)));
  const archiveMail = (m) => { setArchived((p) => [...p, m]); setMails((prev) => prev.filter((x) => x.id !== m.id)); };
  const deleteMail = (m) => { setTrashed((p) => [...p, m]); setMails((prev) => prev.filter((x) => x.id !== m.id)); setArchived((prev) => prev.filter((x) => x.id !== m.id)); };
  const snoozeMail = (m) => { setSnoozed((p) => [...p, m]); setMails((prev) => prev.filter((x) => x.id !== m.id)); };

  const toggleSelect = (id) => setSelected((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
  const bulkMarkRead = () => setMails((prev) => prev.map((m) => (selected.includes(m.id) ? { ...m, read: true } : m)));
  const bulkDelete = () => { const toMove = mails.filter((m) => selected.includes(m.id)); setTrashed((p) => [...p, ...toMove]); setMails((prev) => prev.filter((m) => !selected.includes(m.id))); setSelected([]); };

  const startCompose = (prefill = { to: '', subject: '', body: `\n\n${signature}`, attachments: [] }) => { setDraft(prefill); setComposing(true); };
  const attachFile = (e) => {
    const files = Array.from(e.target.files || []);
    files.forEach((f) => {
      const reader = new FileReader();
      reader.onload = () => setDraft((d) => ({ ...d, attachments: [...d.attachments, { name: f.name, size: f.size, url: reader.result }] }));
      reader.readAsDataURL(f);
    });
    e.target.value = '';
  };

  const send = () => {
    if (!draft.to || !draft.subject) return;
    const payload = { id: uid('sm'), to: draft.to, subject: draft.subject, body: draft.body, attachments: draft.attachments, time: 'Just now' };
    setComposing(false);
    const timer = setTimeout(() => { setSent((prev) => [payload, ...prev]); setPendingSend(null); }, 5000);
    setPendingSend({ timer, payload });
  };
  const undoSend = () => { if (pendingSend) { clearTimeout(pendingSend.timer); setPendingSend(null); } };

  return (
    <div className={`flex-1 flex overflow-hidden relative ${dark ? 'bg-zinc-950' : 'bg-white'}`}>
      <aside className={`w-56 border-r p-3 space-y-4 overflow-y-auto ov-scrollbar ${dark ? 'bg-zinc-900 border-zinc-800' : 'bg-white border-zinc-200'}`}>
        <button onClick={() => startCompose()} className="w-full flex items-center justify-center space-x-2 py-2.5 rounded-full text-sm font-semibold text-zinc-950 shadow-sm" style={{ background: BRASS }}>
          <Plus size={16} /> <span>Compose</span>
        </button>
        <div className="space-y-1">
          {[
            { key: 'inbox', label: 'Inbox', icon: MailIcon, count: mails.filter((m) => !m.read).length },
            { key: 'sent', label: 'Sent', icon: Send },
            { key: 'archive', label: 'Archive', icon: Archive },
            { key: 'snoozed', label: 'Snoozed', icon: Clock },
            { key: 'trash', label: 'Trash', icon: Trash2 },
          ].map(({ key, label, icon: Icon, count }) => (
            <button key={key} onClick={() => setFolder(key)}
              className={`flex items-center justify-between w-full px-3 py-2 rounded-lg text-sm font-medium ${folder === key ? 'bg-amber-500/10 text-amber-500' : 'text-zinc-500 hover:bg-zinc-100 dark:hover:bg-zinc-800'}`}>
              <span className="flex items-center space-x-2"><Icon size={14} /><span>{label}</span></span>
              {!!count && <span className="text-xs">{count}</span>}
            </button>
          ))}
        </div>
        {folder === 'inbox' && (
          <div className="space-y-1">
            <p className="text-[10px] font-semibold text-zinc-400 px-1">LABELS</p>
            {labels.map((l) => (
              <button key={l} onClick={() => setLabelFilter(l)} className={`flex items-center space-x-2 w-full px-3 py-1.5 rounded-lg text-xs ${labelFilter === l ? 'font-semibold' : 'text-zinc-500'}`}>
                <Tag size={11} style={{ color: l === 'All' ? '#a1a1aa' : BRASS }} /> <span>{l}</span>
              </button>
            ))}
          </div>
        )}
        <button onClick={() => setShowSettings(true)} className="flex items-center space-x-2 text-xs text-zinc-500 px-1"><Settings size={12} /><span>Signature settings</span></button>
      </aside>

      <div className={`w-72 border-r overflow-y-auto ov-scrollbar ${dark ? 'border-zinc-800' : 'border-zinc-200'}`}>
        {folder === 'inbox' && selected.length > 0 && (
          <div className="flex items-center gap-2 px-3 py-2 border-b text-xs">
            <button onClick={bulkMarkRead} className="underline">Mark read</button>
            <button onClick={bulkDelete} className="underline text-red-500">Delete</button>
            <span className="ml-auto text-zinc-400">{selected.length} selected</span>
          </div>
        )}
        {visible.length === 0 && <p className="text-sm text-zinc-400 p-4">Nothing here.</p>}
        {folder === 'inbox' && visible.map((m) => (
          <div key={m.id} className={`flex items-start gap-2 p-3.5 cursor-pointer border-b ${dark ? 'border-zinc-900' : 'border-zinc-100'} ${activeId === m.id ? (dark ? 'bg-zinc-900' : 'bg-amber-500/5') : ''}`}>
            <button onClick={(e) => { e.stopPropagation(); toggleSelect(m.id); }} className="mt-0.5">
              {selected.includes(m.id) ? <CheckSquare size={14} style={{ color: BRASS }} /> : <Square size={14} className="text-zinc-400" />}
            </button>
            <div className="flex-1 min-w-0 space-y-1" onClick={() => { setActiveId(m.id); openMail(m.id); }}>
              <div className="flex justify-between items-center">
                <span className={`text-sm truncate ${!m.read ? 'font-bold' : 'font-medium text-zinc-500'}`}>{m.from}</span>
                <span className="text-[11px] text-zinc-400 shrink-0">{m.time}</span>
              </div>
              <p className={`text-xs truncate ${!m.read ? 'font-semibold' : 'text-zinc-500'}`}>{m.subject}</p>
              <p className="text-xs text-zinc-400 truncate">{m.preview}</p>
              {m.label && <span className="text-[10px] px-1.5 py-0.5 rounded" style={{ background: `${BRASS}22`, color: BRASS_DARK }}>{m.label}</span>}
            </div>
          </div>
        ))}
        {folder !== 'inbox' && visible.map((m) => (
          <div key={m.id} className={`p-3.5 border-b space-y-1 ${dark ? 'border-zinc-900' : 'border-zinc-100'}`}>
            <div className="flex justify-between items-center">
              <span className="text-sm font-medium truncate">{m.to ? `To: ${m.to}` : m.from}</span>
              <span className="text-[11px] text-zinc-400">{m.time}</span>
            </div>
            <p className="text-xs font-semibold truncate">{m.subject}</p>
          </div>
        ))}
      </div>

      <div className="flex-1 p-8 overflow-y-auto ov-scrollbar relative">
        {folder === 'inbox' && active ? (
          <>
            <div className="flex justify-between items-start border-b pb-4 mb-4">
              <div>
                <h2 className="text-lg font-semibold">{active.subject}</h2>
                <p className="text-xs text-zinc-500 mt-1">From: {active.from}</p>
              </div>
              <button onClick={() => toggleStar(active.id)}><Star size={16} fill={active.starred ? BRASS : 'none'} color={active.starred ? BRASS : '#a1a1aa'} /></button>
            </div>
            <p className="ov-serif text-[15px] leading-relaxed text-zinc-600 dark:text-zinc-300">{active.preview}</p>
            <div className="flex flex-wrap gap-2 mt-6">
              <button onClick={() => startCompose({ to: active.from, subject: `Re: ${active.subject}`, body: `\n\n---- Original ----\n${active.preview}\n\n${signature}`, attachments: [] })} className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-sm border border-zinc-300 dark:border-zinc-700"><Reply size={14} /><span>Reply</span></button>
              <button onClick={() => startCompose({ to: '', subject: `Fwd: ${active.subject}`, body: `\n\n---- Forwarded ----\n${active.preview}\n\n${signature}`, attachments: [] })} className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-sm border border-zinc-300 dark:border-zinc-700"><Forward size={14} /><span>Forward</span></button>
              <button onClick={() => archiveMail(active)} className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-sm border border-zinc-300 dark:border-zinc-700"><Archive size={14} /><span>Archive</span></button>
              <button onClick={() => snoozeMail(active)} className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-sm border border-zinc-300 dark:border-zinc-700"><Clock size={14} /><span>Snooze</span></button>
              <button onClick={() => deleteMail(active)} className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-sm border border-zinc-300 dark:border-zinc-700 text-red-500"><Trash2 size={14} /><span>Delete</span></button>
              {labels.filter((l) => l !== 'All').map((l) => (
                <button key={l} onClick={() => setLabel(active.id, l)} className="text-xs px-2 py-1 rounded-full border border-zinc-300 dark:border-zinc-700">{l}</button>
              ))}
            </div>
          </>
        ) : folder === 'inbox' ? (
          <div className="text-zinc-400 text-sm">Select an email to read it. <span className="ov-mono text-xs">(c: compose, /: search, r: reply)</span></div>
        ) : (
          <div className="text-zinc-400 text-sm">{visible.length ? 'Select an item on the left.' : 'This folder is empty.'}</div>
        )}

        {composing && (
          <div className={`absolute bottom-4 right-4 w-[420px] rounded-t-xl shadow-2xl border flex flex-col ${dark ? 'bg-zinc-900 border-zinc-700' : 'bg-white border-zinc-300'}`}>
            <div className="px-4 py-2.5 rounded-t-xl flex justify-between items-center text-sm font-semibold text-white" style={{ background: '#18181b' }}>
              <span>New message</span>
              <button onClick={() => setComposing(false)}><X size={14} /></button>
            </div>
            <input value={draft.to} onChange={(e) => setDraft((d) => ({ ...d, to: e.target.value }))} placeholder="To" className={`px-3 py-2 text-sm outline-none border-b ${dark ? 'bg-zinc-900 border-zinc-800' : 'border-zinc-100'}`} />
            <input value={draft.subject} onChange={(e) => setDraft((d) => ({ ...d, subject: e.target.value }))} placeholder="Subject" className={`px-3 py-2 text-sm outline-none border-b font-medium ${dark ? 'bg-zinc-900 border-zinc-800' : 'border-zinc-100'}`} />
            <textarea value={draft.body} onChange={(e) => setDraft((d) => ({ ...d, body: e.target.value }))} placeholder="Write your message..." className={`h-32 px-3 py-2 text-sm outline-none resize-none ${dark ? 'bg-zinc-900' : 'bg-white'}`} />
            {draft.attachments.length > 0 && (
              <div className="px-3 py-1 flex flex-wrap gap-1">
                {draft.attachments.map((a, i) => <span key={i} className="text-[10px] px-1.5 py-0.5 rounded bg-zinc-200 dark:bg-zinc-800 flex items-center gap-1"><Paperclip size={9} />{a.name}</span>)}
              </div>
            )}
            <div className="p-3 flex justify-between items-center">
              <label className="cursor-pointer text-zinc-500"><Paperclip size={16} /><input type="file" multiple className="hidden" onChange={attachFile} /></label>
              <button onClick={send} className="px-4 py-1.5 rounded-lg text-sm font-semibold text-zinc-950" style={{ background: BRASS }}>Send</button>
            </div>
          </div>
        )}

        {pendingSend && (
          <div className="absolute bottom-4 left-4 flex items-center gap-3 px-4 py-2.5 rounded-lg shadow-lg text-sm bg-zinc-900 text-white">
            <span>Message sent</span>
            <button onClick={undoSend} className="font-semibold flex items-center gap-1" style={{ color: BRASS }}><RotateCcw size={12} />Undo</button>
          </div>
        )}

        {showSettings && (
          <div className="fixed inset-0 z-50 flex items-center justify-center" style={{ background: 'rgba(0,0,0,0.4)' }} onClick={() => setShowSettings(false)}>
            <div onClick={(e) => e.stopPropagation()} className={`w-96 rounded-xl p-5 shadow-2xl ${dark ? 'bg-zinc-900 text-zinc-100' : 'bg-white'}`}>
              <h3 className="font-semibold mb-3">Signature</h3>
              <textarea value={signature} onChange={(e) => setSignature(e.target.value)} className={`w-full h-20 rounded border p-2 text-sm outline-none resize-none ${dark ? 'bg-zinc-950 border-zinc-700' : 'border-zinc-300'}`} />
              <button onClick={() => setShowSettings(false)} className="mt-3 px-4 py-1.5 rounded-lg text-sm font-semibold text-zinc-950" style={{ background: BRASS }}>Done</button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
