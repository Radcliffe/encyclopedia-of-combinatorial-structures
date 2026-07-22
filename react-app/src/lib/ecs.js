export function prettyNumber(number) {
  return number.toLocaleString();
}

export function parseSequenceTerm(term) {
  if (typeof term === "number" && !Number.isSafeInteger(term)) {
    throw new TypeError(
      "Sequence terms must be encoded as decimal strings when they exceed JavaScript's safe-integer range",
    );
  }
  return BigInt(term);
}

export function normalizeText(value) {
  return (value ?? "")
    .toString()
    .toLowerCase()
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "");
}

export function parseTermsQuery(query) {
  if (!query) return [];
  return query
    .split(/[\s,]+/)
    .map((term) => term.trim())
    .filter(Boolean)
    .map((term) => BigInt(term));
}

export function makeReferenceLink(reference) {
  const match = reference.match(/^EIS\s+A(\d{1,6})$/i);
  if (match) {
    return `https://oeis.org/A${match[1].padStart(6, "0")}`;
  }
  return /^https?:\/\//i.test(reference) ? reference : "#";
}

export function makeBfileLink(structureId) {
  return `/b-files/b${String(structureId).padStart(6, "0")}.txt`;
}

export function prefixMatchesSequence(sequence, prefix) {
  if (!prefix.length) return true;
  if (!Array.isArray(sequence) || prefix.length > sequence.length) return false;
  return prefix.every((term, index) => sequence[index] === term);
}

export function normalizeRecord(record) {
  const id = Number(record.id);
  return {
    id,
    key: String(id),
    name: record.name ?? "Unnamed structure",
    description: record.description ?? "",
    specification: record.specification ?? "",
    labeled: Boolean(record.labeled),
    symbol: record.symbol ?? "",
    terms: Array.isArray(record.terms) ? record.terms.map(parseSequenceTerm) : [],
    generating_function: record.gf ?? "",
    closed_form: record.closedform ?? "",
    references: Array.isArray(record.references) ? record.references : [],
  };
}
