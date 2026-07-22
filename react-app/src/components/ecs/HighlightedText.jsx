import React from "react";
import PropTypes from "prop-types";

HighlightedText.propTypes = {
  children: PropTypes.string,
  query: PropTypes.string,
};

export function HighlightedText({ children = "", query = "" }) {
  if (!query) return children;

  const index = children.toLowerCase().indexOf(query.toLowerCase());
  if (index === -1) return children;

  return (
    <>
      {children.slice(0, index)}
      <mark className="rounded px-1 py-0.5">
        {children.slice(index, index + query.length)}
      </mark>
      {children.slice(index + query.length)}
    </>
  );
}
