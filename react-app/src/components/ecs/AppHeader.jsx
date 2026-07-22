import React from "react";
import PropTypes from "prop-types";
import { BookOpen, Info, RefreshCw, Search } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

AppHeader.propTypes = {
  mainView: PropTypes.oneOf(["search", "index"]).isRequired,
  onMainViewChange: PropTypes.func.isRequired,
  onAbout: PropTypes.func.isRequired,
  onReload: PropTypes.func.isRequired,
};

export function AppHeader({ mainView, onMainViewChange, onAbout, onReload }) {
  return (
    <header className="sticky top-0 z-40 border-b bg-white/70 backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-2 px-3 py-3 sm:gap-3 sm:px-4">
        <div className="flex min-w-0 items-center gap-2 sm:gap-3">
          <img
            src="/ecslogo.svg"
            height="48"
            width="48"
            alt="ECS logo"
            className="h-8 w-8 shrink-0 sm:h-12 sm:w-12"
          />
          <h1 className="min-w-0 text-sm font-semibold leading-tight sm:text-2xl">
            Encyclopedia of Combinatorial Structures
          </h1>
          <Badge variant="secondary" className="ml-1 hidden md:inline-flex">
            Prototype
          </Badge>
        </div>
        <div className="flex items-center gap-1 sm:gap-2">
          <Button
            variant={mainView === "search" ? "secondary" : "ghost"}
            onClick={() => onMainViewChange("search")}
            className="gap-2"
            title="Search the ECS"
          >
            <Search className="h-4 w-4" />
            <span className="hidden sm:inline">Search</span>
          </Button>
          <Button
            variant={mainView === "index" ? "secondary" : "ghost"}
            onClick={() => onMainViewChange("index")}
            className="gap-2"
            title="Browse the alphabetical index"
          >
            <BookOpen className="h-4 w-4" />
            <span className="hidden sm:inline">Index</span>
          </Button>
          <Button variant="ghost" size="icon" onClick={onAbout} title="About this project">
            <Info className="h-5 w-5" />
          </Button>
          <Button variant="ghost" size="icon" onClick={onReload} title="Reload">
            <RefreshCw className="h-5 w-5" />
          </Button>
        </div>
      </div>
    </header>
  );
}
