import React, { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { AlphabeticalIndex } from "@/components/ecs/AlphabeticalIndex";
import { AppFooter } from "@/components/ecs/AppFooter";
import { AppHeader } from "@/components/ecs/AppHeader";
import { SearchView } from "@/components/ecs/SearchView";
import { SidePanel } from "@/components/ecs/SidePanel";
import { TooltipProvider } from "@/components/ui/tooltip";
import {
  normalizeRecord,
  normalizeText,
  parseTermsQuery,
  prefixMatchesSequence,
} from "@/lib/ecs";

const INITIAL_FILTERS = {
  id: "",
  name: "",
  terms: "",
  generatingFunction: "",
  closedForm: "",
  sortBy: "id",
};

export default function App() {
  const [items, setItems] = useState([]);
  const [loadState, setLoadState] = useState("idle");
  const [filters, setFilters] = useState(INITIAL_FILTERS);
  const [mainView, setMainView] = useState("search");
  const [sideView, setSideView] = useState("results");
  const [selected, setSelected] = useState(null);
  const [searchParams, setSearchParams] = useSearchParams();

  useEffect(() => {
    const structureNumber = searchParams.get("nbr");
    if (!structureNumber) {
      setSelected(null);
      return;
    }
    if (items.length > 0) {
      const structure = items.find((item) => item.id === Number(structureNumber)) ?? null;
      setSelected(structure);
      if (structure) setSideView("results");
    }
  }, [searchParams, items]);

  useEffect(() => {
    const controller = new AbortController();

    async function loadStructures() {
      setLoadState("loading");
      try {
        const response = await fetch("/ecs.json", {
          headers: { "Content-Type": "application/json" },
          signal: controller.signal,
          cache: "no-store",
        });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);

        const data = await response.json();
        setItems(Object.values(data).map(normalizeRecord));
        setLoadState("ready");
      } catch (error) {
        if (error.name === "AbortError") return;
        console.warn("Could not load ecs.json", error);
        setLoadState("error");
      }
    }

    loadStructures();
    return () => controller.abort();
  }, []);

  const termsPrefix = useMemo(() => parseTermsQuery(filters.terms), [filters.terms]);

  const filteredItems = useMemo(() => {
    if (!items.length) return [];

    const idQuery = filters.id.trim();
    const nameWords = normalizeText(filters.name).split(/\s+/).filter(Boolean);
    const generatingFunctionQuery = normalizeText(filters.generatingFunction);
    const closedFormQuery = normalizeText(filters.closedForm);

    return items
      .filter((item) => {
        if (idQuery && !String(item.id).startsWith(idQuery)) return false;
        if (nameWords.length) {
          const name = normalizeText(item.name);
          if (!nameWords.every((word) => name.includes(word))) return false;
        }
        if (termsPrefix.length && !prefixMatchesSequence(item.terms, termsPrefix)) return false;
        if (
          generatingFunctionQuery &&
          !normalizeText(item.generating_function).includes(generatingFunctionQuery)
        ) {
          return false;
        }
        if (closedFormQuery && !normalizeText(item.closed_form).includes(closedFormQuery)) {
          return false;
        }
        return true;
      })
      .sort((a, b) =>
        filters.sortBy === "name" ? a.name.localeCompare(b.name) : a.id - b.id,
      );
  }, [items, filters, termsPrefix]);

  function updateFilter(name, value) {
    setFilters((current) => ({ ...current, [name]: value }));
  }

  function selectStructure(item) {
    setSelected(item);
    setSideView("results");
    const next = new URLSearchParams(searchParams);
    next.set("nbr", String(item.id));
    setSearchParams(next);
  }

  function clearSelection() {
    setSelected(null);
    const next = new URLSearchParams(searchParams);
    next.delete("nbr");
    setSearchParams(next);
  }

  return (
    <TooltipProvider>
      <div className="min-h-screen bg-gradient-to-b from-slate-50 to-white text-slate-900">
        <AppHeader
          mainView={mainView}
          onMainViewChange={setMainView}
          onAbout={() => setSideView("about")}
          onReload={() => window.location.reload()}
        />

        <main className="mx-auto max-w-6xl px-4 py-6">
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
            <div className="space-y-4 lg:col-span-2">
              {mainView === "index" ? (
                <AlphabeticalIndex
                  items={items}
                  loadState={loadState}
                  selected={selected}
                  onSelect={selectStructure}
                />
              ) : (
                <SearchView
                  datasetSize={items.length}
                  filters={filters}
                  items={filteredItems}
                  loadState={loadState}
                  onFilterChange={updateFilter}
                  onSelect={selectStructure}
                />
              )}
            </div>

            <div className="space-y-4 lg:col-span-1">
              <SidePanel
                view={sideView}
                onViewChange={setSideView}
                selected={selected}
                onClearSelection={clearSelection}
              />
            </div>
          </div>
        </main>

        <AppFooter />
      </div>
    </TooltipProvider>
  );
}
