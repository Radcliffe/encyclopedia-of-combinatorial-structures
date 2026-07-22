import React from "react";
import PropTypes from "prop-types";
import {
  AlertCircle,
  BookOpen,
  Database,
  Filter,
  Hash,
  Layers,
  ListFilter,
  Loader2,
  Search,
  SigmaSquare,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { prettyNumber } from "@/lib/ecs";
import { ResultsList } from "./ResultsList";

const filtersPropType = PropTypes.shape({
  id: PropTypes.string.isRequired,
  name: PropTypes.string.isRequired,
  terms: PropTypes.string.isRequired,
  generatingFunction: PropTypes.string.isRequired,
  closedForm: PropTypes.string.isRequired,
  sortBy: PropTypes.oneOf(["id", "name"]).isRequired,
});

SearchView.propTypes = {
  datasetSize: PropTypes.number.isRequired,
  filters: filtersPropType.isRequired,
  items: PropTypes.array.isRequired,
  loadState: PropTypes.string.isRequired,
  onFilterChange: PropTypes.func.isRequired,
  onSelect: PropTypes.func.isRequired,
};

export function SearchView({
  datasetSize,
  filters,
  items,
  loadState,
  onFilterChange,
  onSelect,
}) {
  return (
    <>
      <Card className="shadow-sm">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-lg">
            <ListFilter className="h-5 w-5" /> Search
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {loadState !== "ready" && (
            <div className="flex flex-col items-start gap-3 rounded-xl border p-3 sm:flex-row sm:items-center">
              <div className="flex items-center gap-2">
                <Database className="h-5 w-5" />
                <div className="font-medium">Data source</div>
              </div>
              <div className="text-sm opacity-80">
                {loadState === "loading" && (
                  <span className="inline-flex items-center gap-2">
                    <Loader2 className="h-4 w-4 animate-spin" /> Loading <code>ecs.json</code>…
                  </span>
                )}
                {loadState === "error" && (
                  <span className="inline-flex items-center gap-2 text-amber-700">
                    <AlertCircle className="h-4 w-4" /> Couldn&apos;t fetch <code>/ecs.json</code>.
                  </span>
                )}
                {loadState === "idle" && (
                  <span>Ready to load <code>ecs.json</code>.</span>
                )}
              </div>
            </div>
          )}

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
            <SearchField icon={Hash} label="Structure #">
              <Input
                placeholder="e.g. 42"
                value={filters.id}
                onChange={(event) => onFilterChange("id", event.target.value)}
              />
            </SearchField>
            <SearchField icon={Search} label="Name keywords">
              <Input
                placeholder="e.g. ternary trees"
                value={filters.name}
                onChange={(event) => onFilterChange("name", event.target.value)}
              />
            </SearchField>
            <SearchField icon={SigmaSquare} label="First terms (prefix)">
              <Input
                placeholder="e.g. 0,1,0,0,1"
                value={filters.terms}
                onChange={(event) => onFilterChange("terms", event.target.value)}
              />
            </SearchField>
            <SearchField icon={Layers} label="Generating function contains">
              <Input
                placeholder="e.g. x^3 / (1-x)"
                value={filters.generatingFunction}
                onChange={(event) => onFilterChange("generatingFunction", event.target.value)}
              />
            </SearchField>
            <SearchField icon={BookOpen} label="Closed form contains">
              <Input
                placeholder="e.g. binom(n, k)"
                value={filters.closedForm}
                onChange={(event) => onFilterChange("closedForm", event.target.value)}
              />
            </SearchField>
            <SearchField icon={Filter} label="Sort">
              <select
                className="h-10 w-full rounded-md border px-3"
                value={filters.sortBy}
                onChange={(event) => onFilterChange("sortBy", event.target.value)}
              >
                <option value="id">Structure # (ascending)</option>
                <option value="name">Name (A→Z)</option>
              </select>
            </SearchField>
          </div>

          <div className="flex items-center gap-2 text-sm text-slate-600">
            <span>Matches:</span>
            <Badge variant="secondary">{prettyNumber(items.length)}</Badge>
            <span className="ml-3">Dataset size:</span>
            <Badge variant="outline">{datasetSize ? prettyNumber(datasetSize) : "—"}</Badge>
          </div>
        </CardContent>
      </Card>

      <Card className="shadow-sm">
        <CardHeader className="pb-2">
          <CardTitle className="text-lg">Results</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <ResultsList items={items} onSelect={onSelect} nameQuery={filters.name} />
        </CardContent>
      </Card>
    </>
  );
}

SearchField.propTypes = {
  children: PropTypes.node.isRequired,
  icon: PropTypes.elementType.isRequired,
  label: PropTypes.string.isRequired,
};

function SearchField({ children, icon: Icon, label }) {
  return (
    <div className="space-y-1">
      <label className="flex items-center gap-2 text-sm font-medium">
        <Icon className="h-4 w-4" /> {label}
      </label>
      {children}
    </div>
  );
}
