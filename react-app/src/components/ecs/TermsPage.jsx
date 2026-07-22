import React from "react";
import PropTypes from "prop-types";
import { ArrowLeft, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { TermsExplorer } from "./TermsExplorer";

TermsPage.propTypes = {
  loadState: PropTypes.string.isRequired,
  onBack: PropTypes.func.isRequired,
  structure: PropTypes.object,
};

export function TermsPage({ loadState, onBack, structure }) {
  return (
    <main className="mx-auto max-w-6xl px-4 py-6">
      <Button type="button" variant="ghost" className="mb-4" onClick={onBack}>
        <ArrowLeft className="h-4 w-4" /> Back to the ECS
      </Button>

      {structure ? (
        <TermsExplorer structure={structure} />
      ) : (
        <Card className="shadow-sm">
          <CardContent className="py-16 text-center text-sm text-slate-600">
            {loadState === "loading" || loadState === "idle" ? (
              <span className="inline-flex items-center gap-2">
                <Loader2 className="h-4 w-4 animate-spin" /> Loading sequence…
              </span>
            ) : (
              "The requested structure could not be found."
            )}
          </CardContent>
        </Card>
      )}
    </main>
  );
}
