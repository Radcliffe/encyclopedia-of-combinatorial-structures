import React, { useMemo, useState } from "react";
import PropTypes from "prop-types";
import { AlertCircle, BookOpen, Loader2, Search } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { normalizeText, prettyNumber } from "@/lib/ecs";
import { HighlightedText } from "./HighlightedText";

const INDEX_LETTERS = ["#", ..."ABCDEFGHIJKLMNOPQRSTUVWXYZ"];

function indexLetter(name) {
  const first = normalizeText(name).trim().charAt(0).toUpperCase();
  return /^[A-Z]$/.test(first) ? first : "#";
}

AlphabeticalIndex.propTypes = {
  items: PropTypes.array.isRequired,
  loadState: PropTypes.string.isRequired,
  selected: PropTypes.object,
  onSelect: PropTypes.func.isRequired,
};

export function AlphabeticalIndex({ items, loadState, selected, onSelect }) {
  const [query, setQuery] = useState("");

  const groups = useMemo(() => {
    const words = normalizeText(query).split(/\s+/).filter(Boolean);
    const matching = items
      .filter((item) => {
        const name = normalizeText(item.name);
        return words.every((word) => name.includes(word));
      })
      .sort(
        (a, b) =>
          a.name.localeCompare(b.name, undefined, { sensitivity: "base", numeric: true }) ||
          a.id - b.id,
      );

    const grouped = new Map();
    for (const item of matching) {
      const letter = indexLetter(item.name);
      if (!grouped.has(letter)) grouped.set(letter, []);
      grouped.get(letter).push(item);
    }
    return grouped;
  }, [items, query]);

  const visibleLetters = INDEX_LETTERS.filter((letter) => groups.has(letter));
  const matchCount = Array.from(groups.values()).reduce((total, group) => total + group.length, 0);

  function handleEntryClick(event, item) {
    if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    onSelect(item);
  }

  return (
    <Card className="shadow-sm">
      <CardHeader className="pb-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <CardTitle className="flex items-center gap-2 text-lg">
            <BookOpen className="h-5 w-5" /> Alphabetical Index
          </CardTitle>
          <Badge variant="secondary">{prettyNumber(matchCount)} structures</Badge>
        </div>
        <p className="text-sm text-slate-600">
          Browse every structure by name, or filter the index with a few keywords.
        </p>
      </CardHeader>
      <CardContent className="space-y-5">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <Input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Filter structure names"
            className="pl-9"
            aria-label="Filter the alphabetical index"
          />
        </div>

        {loadState === "loading" && (
          <div className="flex items-center justify-center py-10 text-sm text-slate-600">
            <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Loading index…
          </div>
        )}
        {loadState === "error" && (
          <div className="flex items-center gap-2 rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
            <AlertCircle className="h-4 w-4 shrink-0" /> The index could not load because{" "}
            <code>/ecs.json</code> is unavailable.
          </div>
        )}
        {loadState === "ready" && matchCount === 0 && (
          <div className="rounded-lg border border-dashed p-6 text-center text-sm text-slate-600">
            No structure names match “{query}”.
          </div>
        )}
        {loadState === "ready" && matchCount > 0 && (
          <>
            <nav aria-label="Index letters" className="flex flex-wrap gap-1.5 border-y py-3">
              {INDEX_LETTERS.map((letter) =>
                groups.has(letter) ? (
                  <a
                    key={letter}
                    href={`#index-${letter === "#" ? "other" : letter}`}
                    className="inline-flex h-8 min-w-8 items-center justify-center rounded-md border bg-white px-2 text-sm font-medium hover:bg-slate-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-400"
                  >
                    {letter}
                  </a>
                ) : (
                  <span
                    key={letter}
                    aria-hidden="true"
                    className="inline-flex h-8 min-w-8 items-center justify-center px-2 text-sm text-slate-300"
                  >
                    {letter}
                  </span>
                ),
              )}
            </nav>

            <div className="space-y-7">
              {visibleLetters.map((letter) => (
                <section
                  key={letter}
                  id={`index-${letter === "#" ? "other" : letter}`}
                  className="scroll-mt-24"
                >
                  <div className="mb-2 flex items-baseline gap-2 border-b pb-1">
                    <h2 className="text-xl font-semibold">{letter}</h2>
                    <span className="text-xs text-slate-500">{groups.get(letter).length}</span>
                  </div>
                  <ol className="grid grid-cols-1 gap-x-5 sm:grid-cols-2">
                    {groups.get(letter).map((item) => (
                      <li key={item.key}>
                        <a
                          href={`?nbr=${item.id}`}
                          onClick={(event) => handleEntryClick(event, item)}
                          aria-current={selected?.id === item.id ? "page" : undefined}
                          className={`group flex min-h-10 items-start gap-2 rounded-md px-2 py-2 text-sm transition hover:bg-slate-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-400 ${
                            selected?.id === item.id ? "bg-slate-100" : ""
                          }`}
                        >
                          <span className="w-12 shrink-0 pt-0.5 font-mono text-xs text-slate-500">
                            #{item.id}
                          </span>
                          <span className="leading-5 text-slate-800 group-hover:underline">
                            <HighlightedText query={query}>{item.name}</HighlightedText>
                          </span>
                        </a>
                      </li>
                    ))}
                  </ol>
                </section>
              ))}
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}
