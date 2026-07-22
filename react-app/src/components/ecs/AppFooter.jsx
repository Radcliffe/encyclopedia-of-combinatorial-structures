import React from "react";

export function AppFooter() {
  return (
    <footer className="mt-8 border-t">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-3 px-4 py-6 text-sm text-slate-600">
        <span>
          Created by David Radcliffe with data from INRIA Algorithms Project and the OEIS community.
          Last updated August 30, 2025.
        </span>
      </div>
    </footer>
  );
}
