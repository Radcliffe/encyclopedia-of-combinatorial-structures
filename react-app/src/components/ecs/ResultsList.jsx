import React from "react";
import PropTypes from "prop-types";
import { ChevronRight } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { HighlightedText } from "./HighlightedText";

ResultsList.propTypes = {
  items: PropTypes.array.isRequired,
  onSelect: PropTypes.func.isRequired,
  nameQuery: PropTypes.string.isRequired,
};

export function ResultsList({ items, onSelect, nameQuery }) {
  return (
    <div className="divide-y">
      {items.length === 0 && (
        <div className="p-6 text-sm text-slate-600">No results. Try relaxing a filter.</div>
      )}
      {items.slice(0, 20).map((item) => (
        <button
          key={item.key}
          onClick={() => onSelect(item)}
          className="flex w-full flex-col gap-2 p-4 text-left transition hover:bg-slate-50"
        >
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-2 font-medium">
              <Badge variant="outline">#{item.id}</Badge>
              <span>
                <HighlightedText query={nameQuery}>{item.name}</HighlightedText>
              </span>
            </div>
            <ChevronRight className="h-4 w-4 opacity-50" />
          </div>
          <div className="line-clamp-2 text-sm text-slate-600">
            {item.description || <em className="opacity-70">No description</em>}
          </div>
          <div className="flex flex-wrap items-center gap-2 text-xs">
            {item.symbol && <Badge variant="secondary">symbol: {item.symbol}</Badge>}
            <Badge variant="secondary">labeled: {item.labeled ? "yes" : "no"}</Badge>
            {item.generating_function_type && (
              <Badge variant="outline">
                {item.generating_function_type === "exponential" ? "EGF" : "OGF"}
              </Badge>
            )}
            {item.terms.length > 0 && (
              <span className="opacity-70">
                terms: {item.terms.slice(0, 8).join(", ")}{item.terms.length > 8 ? "…" : ""}
              </span>
            )}
          </div>
        </button>
      ))}
    </div>
  );
}
