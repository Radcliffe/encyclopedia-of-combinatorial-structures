import React, { useEffect, useMemo, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Search, Info, Database, AlertCircle, Filter, ListFilter, Upload, Loader2, Hash, SigmaSquare, BookOpen, Layers, Sparkles, ChevronRight, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { TooltipProvider } from "@/components/ui/tooltip";
import ExternalLink from "./components/ExternalLink";

// --- Minimal helpers ---
const prettyNumber = (n) => n.toLocaleString();
// const clamp = (v, a, b) => Math.max(a, Math.min(b, v));

// --- Small, simple in-memory search engine ---
function normalize(s) {
  return (s ?? "")
    .toString()
    .toLowerCase()
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "");
}

function parseTermsQuery(q) {
	// Accepts: "0,1,0,0,1" or "0 1 0 0 1" -> [0n, 1n, 0n, 0n, 1n]
	if (!q) return [];
	return q
		.split(/[\s,]+/)
		.map((x) => x.trim())
		.filter(Boolean)
		.map((x) => BigInt(x)); // Convert to BigInt
}

function makeLink(r) {
	const m = r.match(/^EIS\s+A(\d{1,6})$/i);
	if (m) {
		const num = m[1].padStart(6, "0");
		return `https://oeis.org/A${num}`;
	}
	if (/^https?:\/\//i.test(r)) {
		return r;
	}
	return '#';
}

function prefixMatchesSequence(seq, prefix) {
  if (!prefix.length) return true;
  if (!Array.isArray(seq)) return false;
  if (prefix.length > seq.length) return false;
  for (let i = 0; i < prefix.length; i++) {
    if (seq[i] !== prefix[i]) return false;
  }
  return true;
}

function highlight(text, query) {
  const t = text ?? "";
  if (!query) return t;
  const i = t.toLowerCase().indexOf(query.toLowerCase());
  if (i === -1) return t;
  return (
    <>
      {t.slice(0, i)}
      <mark className="rounded px-1 py-0.5">{t.slice(i, i + query.length)}</mark>
      {t.slice(i + query.length)}
    </>
  );
}

// --- Main App ---
export default function App() {
  const [data, setData] = useState(null); // raw JSON as object keyed by id
  const [items, setItems] = useState([]); // normalized array
  const [loadState, setLoadState] = useState("idle"); // idle | loading | error | ready
  const [error, setError] = useState("");

  // Search state
  const [qId, setQId] = useState(""); // structure number/id
  const [qName, setQName] = useState(""); // keywords in name
  const [qTerms, setQTerms] = useState(""); // first terms prefix
  const [qGF, setQGF] = useState(""); // generating function contains
  const [qCF, setQCF] = useState(""); // closed form contains
  const [sortBy, setSortBy] = useState("id"); // id | name
  const [view, setView] = useState("results"); // results | about
  const [selected, setSelected] = useState(null);

  const fileInputRef = useRef(null);

  // Load ecs.json from the same origin (public root). If it fails, we allow manual upload.
  useEffect(() => {
    const controller = new AbortController();
    async function boot() {
      setLoadState("loading");
      setError("");
      try {
        const res = await fetch("/ecs.json", { signal: controller.signal, cache: "no-store" });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const json = await res.json();
        setData(json);
        const arr = Object.values(json).map((rec) => normalizeRecord(rec));
        setItems(arr);
        setLoadState("ready");
      } catch (e) {
        console.warn("Auto-load failed, falling back to manual upload", e);
        setLoadState("error");
        setError(e?.message || "Failed to load ecs.json");
      }
    }
    boot();
    return () => controller.abort();
  }, []);

  function normalizeRecord(rec) {
    // Be generous about field names to accommodate historical/legacy dumps.
    const id = Number(rec.id ?? rec.ID ?? rec.number ?? rec.idx);
    return {
      id,
      key: String(id),
      name: rec.name ?? rec.title ?? "Unnamed structure",
      description: rec.description ?? rec.desc ?? "",
      specification: rec.specification ?? rec.spec ?? "",
      labeled: Boolean(rec.labeled ?? rec.is_labeled ?? rec.labelled),
      symbol: rec.symbol ?? rec.sym ?? "",
		terms: Array.isArray(rec.terms) ? rec.terms.map((term) => BigInt(term)) : [],
		generating_function: rec.generating_function ?? rec.gf ?? rec.genfun ?? "",
      closed_form: rec.closed_form ?? rec.cf ?? "",
      references: Array.isArray(rec.references) ? rec.references : [],
    };
  }

  function handleUpload(ev) {
    const file = ev.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    setLoadState("loading");
    reader.onload = () => {
      try {
        const json = JSON.parse(reader.result);
        setData(json);
        const arr = Object.values(json).map((rec) => normalizeRecord(rec));
        setItems(arr);
        setLoadState("ready");
        setError("");
      } catch (e) {
        setLoadState("error");
        setError("Invalid JSON file.");
      }
    };
    reader.readAsText(file);
  }

  // Derived search params
  const termsPrefix = useMemo(() => parseTermsQuery(qTerms), [qTerms]);

  const filtered = useMemo(() => {
    if (!items?.length) return [];
    const idQuery = qId.trim();
    const nameQuery = normalize(qName);
    const gfQuery = normalize(qGF);
    const cfQuery = normalize(qCF);

    let res = items.filter((it) => {
      // 1) ID exact or prefix (e.g., "10" matches 10, 100, 101)
      if (idQuery) {
        const idStr = String(it.id);
        if (!idStr.startsWith(idQuery)) return false;
      }
      // 2) Name keyword(s) (AND across words)
      if (nameQuery) {
        const words = nameQuery.split(/\s+/).filter(Boolean);
        const hay = normalize(it.name);
        if (!words.every((w) => hay.includes(w))) return false;
      }
      // 3) First terms prefix
      if (termsPrefix.length) {
        if (!prefixMatchesSequence(it.terms, termsPrefix)) return false;
      }
      // 4) Generating function contains
      if (gfQuery) {
        const hay = normalize(it.generating_function);
        if (!hay.includes(gfQuery)) return false;
      }
      // 5) Closed form contains
      if (cfQuery) {
        const hay = normalize(it.closed_form);
        if (!hay.includes(cfQuery)) return false;
      }
      return true;
    });

    res.sort((a, b) => {
      if (sortBy === "name") return a.name.localeCompare(b.name);
      return a.id - b.id;
    });
    return res;
  }, [items, qId, qName, qGF, qCF, termsPrefix, sortBy]);

  const count = filtered.length;

  return (
    <TooltipProvider>
      <div className="min-h-screen bg-gradient-to-b from-slate-50 to-white text-slate-900">
        <header className="sticky top-0 z-40 backdrop-blur bg-white/70 border-b">
          <div className="max-w-6xl mx-auto px-4 py-3 flex items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <Sparkles className="w-6 h-6" />
              <h1 className="text-xl sm:text-2xl font-semibold">Encyclopedia of Combinatorial Structures</h1>
              <Badge variant="secondary" className="ml-1">Prototype</Badge>
            </div>
            <div className="flex items-center gap-2">
              <Button variant="ghost" size="icon" onClick={() => setView("about")} title="About this project">
                <Info className="w-5 h-5" />
              </Button>
              <Button variant="ghost" size="icon" onClick={() => window.location.reload()} title="Reload">
                <RefreshCw className="w-5 h-5" />
              </Button>
            </div>
          </div>
        </header>

        <main className="max-w-6xl mx-auto px-4 py-6">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            <div className="lg:col-span-2 space-y-4">
              <Card className="shadow-sm">
                <CardHeader className="pb-3">
                  <CardTitle className="flex items-center gap-2 text-lg">
                    <ListFilter className="w-5 h-5" /> Search
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  {loadState !== "ready" && (
                    <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3 p-3 border rounded-xl">
                      <div className="flex items-center gap-2">
                        <Database className="w-5 h-5" />
                        <div className="font-medium">Data source</div>
                      </div>
                      <div className="text-sm opacity-80">
                        {loadState === "loading" && (
                          <span className="inline-flex items-center gap-2"><Loader2 className="w-4 h-4 animate-spin"/> Loading <code>ecs.json</code>…</span>
                        )}
                        {loadState === "error" && (
                          <span className="inline-flex items-center gap-2 text-amber-700"><AlertCircle className="w-4 h-4"/> Couldn't fetch <code>/ecs.json</code>. Upload it below.</span>
                        )}
                        {loadState === "idle" && (
                          <span>Ready to load <code>ecs.json</code>.</span>
                        )}
                      </div>
                      <div className="ml-auto flex items-center gap-2">
                        <input ref={fileInputRef} type="file" accept="application/json" className="hidden" onChange={handleUpload} />
                        <Button size="sm" onClick={() => fileInputRef.current?.click()}>
                          <Upload className="w-4 h-4 mr-1"/> Upload ecs.json (≈3 MB)
                        </Button>
                      </div>
                    </div>
                  )}

                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                    <div className="space-y-1">
                      <label className="text-sm font-medium flex items-center gap-2"><Hash className="w-4 h-4"/> Structure #</label>
                      <Input placeholder="e.g. 42" value={qId} onChange={(e) => setQId(e.target.value)} />
                    </div>
                    <div className="space-y-1">
                      <label className="text-sm font-medium flex items-center gap-2"><Search className="w-4 h-4"/> Name keywords</label>
                      <Input placeholder="e.g. ternary trees" value={qName} onChange={(e) => setQName(e.target.value)} />
                    </div>
                    <div className="space-y-1">
                      <label className="text-sm font-medium flex items-center gap-2"><SigmaSquare className="w-4 h-4"/> First terms (prefix)</label>
                      <Input placeholder="e.g. 0,1,0,0,1" value={qTerms} onChange={(e) => setQTerms(e.target.value)} />
                    </div>
                    <div className="space-y-1">
                      <label className="text-sm font-medium flex items-center gap-2"><Layers className="w-4 h-4"/> Generating function contains</label>
                      <Input placeholder="e.g. x^3 / (1-x)" value={qGF} onChange={(e) => setQGF(e.target.value)} />
                    </div>
                    <div className="space-y-1">
                      <label className="text-sm font-medium flex items-center gap-2"><BookOpen className="w-4 h-4"/> Closed form contains</label>
                      <Input placeholder="e.g. binom(n, k)" value={qCF} onChange={(e) => setQCF(e.target.value)} />
                    </div>
                    <div className="space-y-1">
                      <label className="text-sm font-medium flex items-center gap-2"><Filter className="w-4 h-4"/> Sort</label>
                      <select className="w-full border rounded-md h-10 px-3" value={sortBy} onChange={(e) => setSortBy(e.target.value)}>
                        <option value="id">Structure # (ascending)</option>
                        <option value="name">Name (A→Z)</option>
                      </select>
                    </div>
                  </div>

                  <div className="text-sm text-slate-600 flex items-center gap-2">
                    <span>Matches:</span>
                    <Badge variant="secondary">{prettyNumber(count)}</Badge>
                    <span className="ml-3">Dataset size:</span>
                    <Badge variant="outline">{items?.length ? prettyNumber(items.length) : "—"}</Badge>
                  </div>
                </CardContent>
              </Card>

              <Card className="shadow-sm">
                <CardHeader className="pb-2">
                  <CardTitle className="text-lg">Results</CardTitle>
                </CardHeader>
                <CardContent className="p-0">
                  <ResultsList
                    items={filtered}
                    onSelect={(it) => {
                      setSelected(it);
                      setView("results");
                    }}
                    queries={{ qId, qName, qGF, qCF }}
                  />
                </CardContent>
              </Card>
            </div>

            <div className="lg:col-span-1 space-y-4">
              <SidePanel view={view} setView={setView} selected={selected} clearSelection={() => setSelected(null)} />
            </div>
          </div>
        </main>

        <footer className="border-t mt-8">
          <div className="max-w-6xl mx-auto px-4 py-6 text-sm text-slate-600 flex flex-wrap items-center gap-3">
            <span>© {new Date().getFullYear()} Encyclopedia of Combinatorial Structures.</span>
          </div>
        </footer>
      </div>
    </TooltipProvider>
  );
}

function ResultsList({ items, onSelect, queries }) {
  const listRef = useRef(null);
  return (
    <div ref={listRef} className="divide-y">
      {items.length === 0 && (
        <div className="p-6 text-sm text-slate-600">No results. Try relaxing a filter.</div>
      )}
      {items.slice(0, 20).map((it) => (
        <button
          key={it.key}
          onClick={() => onSelect(it)}
          className="w-full text-left p-4 hover:bg-slate-50 transition flex flex-col gap-2"
        >
          <div className="flex items-center justify-between gap-3">
            <div className="font-medium flex items-center gap-2">
              <Badge variant="outline">#{it.id}</Badge>
              <span>{highlight(it.name, queries.qName)}</span>
            </div>
            <ChevronRight className="w-4 h-4 opacity-50"/>
          </div>
          <div className="text-sm text-slate-600 line-clamp-2">
            {it.description || <em className="opacity-70">No description</em>}
          </div>
          <div className="flex flex-wrap items-center gap-2 text-xs">
            {it.symbol && <Badge variant="secondary">symbol: {it.symbol}</Badge>}
            <Badge variant="secondary">labeled: {it.labeled ? "yes" : "no"}</Badge>
            {Array.isArray(it.terms) && it.terms.length > 0 && (
              <span className="opacity-70">terms: {it.terms.slice(0, 8).join(", ")}{it.terms.length > 8 ? "…" : ""}</span>
            )}
          </div>
        </button>
      ))}
    </div>
  );
}

function FieldRow({ label, children }) {
  return (
    <div className="space-y-1">
      <div className="text-xs uppercase tracking-wide text-slate-500">{label}</div>
      <div className="text-sm">{children}</div>
    </div>
  );
}

function SidePanel({ view, setView, selected, clearSelection }) {
  return (
    <Tabs value={view} onValueChange={setView} className="w-full">
      <TabsList className="grid grid-cols-2 gap-2">
        <TabsTrigger value="results">Details</TabsTrigger>
        <TabsTrigger value="about">About</TabsTrigger>
      </TabsList>

      <TabsContent value="results">
        {!selected ? (
          <Card className="shadow-sm">
            <CardHeader className="pb-2">
              <CardTitle className="text-lg flex items-center gap-2"><Info className="w-5 h-5"/> Details</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-slate-600">Select a structure from the results to see its full record.</p>
            </CardContent>
          </Card>
        ) : (
          <AnimatePresence mode="wait">
            <motion.div
              key={selected.key}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -6 }}
            >
              <Card className="shadow-sm">
                <CardHeader className="pb-2">
                  <CardTitle className="text-lg flex items-center gap-2">
                    <Badge variant="outline">#{selected.id}</Badge>
                    <span>{selected.name}</span>
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <FieldRow label="Description">{selected.description || <em className="opacity-70">—</em>}</FieldRow>
                  <FieldRow label="Specification">{selected.specification || <em className="opacity-70">—</em>}</FieldRow>
                  <div className="grid grid-cols-2 gap-3">
                    <FieldRow label="Symbol">{selected.symbol || <em className="opacity-70">—</em>}</FieldRow>
                    <FieldRow label="Labeled">{selected.labeled ? "yes" : "no"}</FieldRow>
                  </div>
                  <FieldRow label="First terms">
                    {Array.isArray(selected.terms) && selected.terms.length > 0 ? (
                      <code className="text-sm break-words">{selected.terms.join(", ")}</code>
                    ) : (
                      <em className="opacity-70">—</em>
                    )}
                  </FieldRow>
                  <FieldRow label="Generating function">
                    {selected.generating_function ? <code className="text-sm break-words">{selected.generating_function}</code> : <em className="opacity-70">—</em>}
                  </FieldRow>
                  <FieldRow label="Closed form">
                    {selected.closed_form ? <code className="text-sm break-words">{selected.closed_form}</code> : <em className="opacity-70">—</em>}
                  </FieldRow>
                  <FieldRow label="References">
                    {selected.references?.length ? (
                      <ul className="list-disc list-inside space-y-1 text-sm">
                        {selected.references.map((r, idx) => (
                          <li key={idx} className="flex items-center gap-1">
                            <ExternalLink className="w-3.5 h-3.5 opacity-60"/>
                            <span><a href={makeLink(r)} target="_blank">{r}</a></span>
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <em className="opacity-70">—</em>
                    )}
                  </FieldRow>
                  <div className="pt-1">
                    <Button variant="secondary" onClick={clearSelection}>Close</Button>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          </AnimatePresence>
        )}
      </TabsContent>

      <TabsContent value="about">
        <Card className="shadow-sm">
          <CardHeader className="pb-2">
            <CardTitle className="text-lg flex items-center gap-2">
              <Info className="w-5 h-5"/> About this POC
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm text-slate-700">
            <p>
              This is a modern replacement for the historic “Encyclopedia of Combinatorial Structures.”
              It ships as a static, client‑only web app: no server or database is required. The full dataset of 1,075 structures
              is provided as a ~3 MB JSON file (<code>ecs.json</code>) that loads in the browser.
            </p>
            <ul className="list-disc list-inside space-y-1">
              <li>Search by structure number, keywords in the name, a prefix of the first terms, or substrings in the generating function or closed form.</li>
              <li>Sort results by ID or name.</li>
              <li>If fetching <code>/ecs.json</code> fails (e.g., local preview), you can upload the file manually.</li>
              <li>The UI is responsive, accessible, and powered by React + Tailwind + shadcn/ui + Framer Motion.</li>
            </ul>
            <p className="opacity-80">
              Notes: generating function and closed form fields are optional in the JSON — the app handles their absence gracefully. Field aliases are supported for older dumps (e.g., <code>gf</code>, <code>genfun</code>, <code>cf</code>).
            </p>
          </CardContent>
        </Card>
      </TabsContent>
    </Tabs>
  );
}
