import React from "react";
import PropTypes from "prop-types";
import { AnimatePresence, motion } from "framer-motion";
import { ChartNoAxesColumn, ExternalLink, FileText, Info } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { makeBfileLink, makeReferenceLink } from "@/lib/ecs";

const CODE_URL = "https://github.com/Radcliffe/encyclopedia-of-combinatorial-structures";

SidePanel.propTypes = {
  view: PropTypes.string.isRequired,
  onViewChange: PropTypes.func.isRequired,
  selected: PropTypes.object,
  onClearSelection: PropTypes.func.isRequired,
  onOpenTerms: PropTypes.func.isRequired,
};

export function SidePanel({ view, onViewChange, selected, onClearSelection, onOpenTerms }) {
  return (
    <Tabs value={view} onValueChange={onViewChange} className="w-full">
      <TabsList className="grid grid-cols-2 gap-2">
        <TabsTrigger value="results">Details</TabsTrigger>
        <TabsTrigger value="about">About</TabsTrigger>
      </TabsList>

      <TabsContent value="results">
        {!selected ? (
          <EmptyDetails />
        ) : (
          <AnimatePresence mode="wait">
            <motion.div
              key={selected.key}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -6 }}
            >
              <StructureDetails
                structure={selected}
                onClose={onClearSelection}
                onOpenTerms={onOpenTerms}
              />
            </motion.div>
          </AnimatePresence>
        )}
      </TabsContent>

      <TabsContent value="about">
        <AboutPanel />
      </TabsContent>
    </Tabs>
  );
}

function EmptyDetails() {
  return (
    <Card className="shadow-sm">
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2 text-lg">
          <Info className="h-5 w-5" /> Details
        </CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-sm text-slate-600">
          Select a structure from the results to see its full record.
        </p>
      </CardContent>
    </Card>
  );
}

StructureDetails.propTypes = {
  structure: PropTypes.object.isRequired,
  onClose: PropTypes.func.isRequired,
  onOpenTerms: PropTypes.func.isRequired,
};

function StructureDetails({ structure, onClose, onOpenTerms }) {
  return (
    <Card className="shadow-sm">
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2 text-lg">
          <Badge variant="outline">#{structure.id}</Badge>
          <span>{structure.name}</span>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <FieldRow label="Description">
          {structure.description || <EmptyValue />}
        </FieldRow>
        <FieldRow label="Specification">
          {structure.specification || <EmptyValue />}
        </FieldRow>
        <div className="grid grid-cols-2 gap-3">
          <FieldRow label="Symbol">{structure.symbol || <EmptyValue />}</FieldRow>
          <FieldRow label="Labeled">{structure.labeled ? "yes" : "no"}</FieldRow>
        </div>
        <FieldRow label="First terms">
          {structure.terms.length > 0 ? (
            <code className="break-words text-sm">{structure.terms.join(", ")}</code>
          ) : (
            <EmptyValue />
          )}
        </FieldRow>
        <FieldRow label="B-file">
          <a
            href={makeBfileLink(structure.id)}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1 underline"
          >
            <FileText className="h-3.5 w-3.5" />
            b{String(structure.id).padStart(6, "0")}.txt
          </a>
        </FieldRow>
        <FieldRow
          label={
            structure.generating_function_type === "exponential"
              ? "Exponential generating function (EGF)"
              : structure.generating_function_type === "ordinary"
                ? "Ordinary generating function (OGF)"
                : "Generating function"
          }
        >
          {structure.generating_function ? (
            <code className="break-words text-sm">{structure.generating_function}</code>
          ) : (
            <EmptyValue />
          )}
        </FieldRow>
        <FieldRow label="Closed form">
          {structure.closed_form ? (
            <code className="break-words text-sm">{structure.closed_form}</code>
          ) : (
            <EmptyValue />
          )}
        </FieldRow>
        <FieldRow label="References">
          {structure.references.length ? (
            <ul className="list-inside list-disc space-y-1 text-sm">
              {structure.references.map((reference, index) => (
                <li key={`${reference}-${index}`} className="flex items-center gap-1">
                  <ExternalLink className="h-3.5 w-3.5 opacity-60" />
                  <a
                    href={makeReferenceLink(reference)}
                    target="_blank"
                    rel="noreferrer"
                    className="underline"
                  >
                    {reference}
                  </a>
                </li>
              ))}
            </ul>
          ) : (
            <EmptyValue />
          )}
        </FieldRow>
        <div className="flex flex-wrap gap-2 pt-1">
          <Button onClick={onOpenTerms}>
            <ChartNoAxesColumn className="h-4 w-4" /> Table and plots
          </Button>
          <Button variant="secondary" onClick={onClose}>
            Close
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

FieldRow.propTypes = {
  label: PropTypes.node.isRequired,
  children: PropTypes.node,
};

function FieldRow({ label, children }) {
  return (
    <div className="space-y-1">
      <div className="text-xs uppercase tracking-wide text-slate-500">{label}</div>
      <div className="text-sm">{children}</div>
    </div>
  );
}

function EmptyValue() {
  return <em className="opacity-70">—</em>;
}

function AboutPanel() {
  return (
    <Card className="shadow-sm">
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2 text-lg">
          <Info className="h-5 w-5" /> About this App
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3 text-sm text-slate-700">
        <p>
          This is a modern re-implementation of the Encyclopedia of Combinatorial Structures, a
          database of combinatorial structures and their associated integer sequences, with an
          emphasis on sequences that arise in the context of decomposable combinatorial structures.
        </p>
        <p>
          The database can be searched by the first terms in the sequence, keywords, generating
          functions, or closed forms.
        </p>
        <p>
          The code is available on{" "}
          <a href={CODE_URL} target="_blank" rel="noreferrer" className="underline">
            GitHub
          </a>
          .
        </p>
      </CardContent>
    </Card>
  );
}
