"""
MarketMind AI — Stage 1: Chunking
Splits cleaned Documents into retrieval-optimized chunks.

Strategy: Source-specific chunk sizes because different data types
have very different information density.
"""

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter


# ─────────────────────────────────────────────
# CHUNK SIZE RATIONALE
# ─────────────────────────────────────────────
#
# Price data      → NO splitting. Already one atomic fact per doc.
#                   Splitting "RELIANCE | ₹2,940 | +1.2%" is destructive.
#
# SEBI filings    → 400 chars, 60 overlap. Filings are dense legal text.
#                   Smaller chunks = more precise retrieval per claim.
#
# Bulk deals      → NO splitting. Each deal is one structured fact.
#
# YouTube         → 300 chars, 50 overlap. Spoken language is less dense.
#                   Shorter windows catch individual financial claims.
#
# News articles   → 500 chars, 80 overlap. News paragraphs need context
#                   across sentences to make sense.
# ─────────────────────────────────────────────

SPLITTER_SEBI = RecursiveCharacterTextSplitter(
    chunk_size=400,
    chunk_overlap=60,
    separators=["\n\n", "\n", ". ", "! ", "? ", " "],
    length_function=len,
)

SPLITTER_YOUTUBE = RecursiveCharacterTextSplitter(
    chunk_size=300,
    chunk_overlap=50,
    separators=[". ", "! ", "? ", "\n", " "],
    length_function=len,
)

SPLITTER_NEWS = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=80,
    separators=["\n\n", "\n", ". ", " "],
    length_function=len,
)


def _split_with_metadata(
    doc: Document,
    splitter: RecursiveCharacterTextSplitter,
) -> list[Document]:
    """Split one Document and copy metadata to all child chunks."""
    chunks = splitter.split_text(doc.page_content)
    result = []
    for i, chunk in enumerate(chunks):
        chunk = chunk.strip()
        if len(chunk) < 40:  # skip tiny trailing fragments
            continue
        result.append(Document(
            page_content=chunk,
            metadata={**doc.metadata, "chunk_index": i, "chunk_total": len(chunks)},
        ))
    return result


def chunk_documents(clean_docs: list[Document]) -> list[Document]:
    """
    Apply source-appropriate chunking to each clean Document.
    Returns the final list of chunks ready for embedding.
    """
    all_chunks: list[Document] = []

    for doc in clean_docs:
        doc_type = doc.metadata.get("type", "news")

        if doc_type in ("price", "bulk_deal"):
            # These are already atomic — no splitting needed
            doc.metadata["chunk_index"] = 0
            doc.metadata["chunk_total"] = 1
            all_chunks.append(doc)

        elif doc_type == "filing":
            all_chunks.extend(_split_with_metadata(doc, SPLITTER_SEBI))

        elif doc_type == "transcript":
            all_chunks.extend(_split_with_metadata(doc, SPLITTER_YOUTUBE))

        else:  # news, default
            all_chunks.extend(_split_with_metadata(doc, SPLITTER_NEWS))

    # Print breakdown by type
    type_counts: dict[str, int] = {}
    for chunk in all_chunks:
        t = chunk.metadata.get("type", "unknown")
        type_counts[t] = type_counts.get(t, 0) + 1

    print("\n[Chunking Stats]")
    print(f"  Total chunks: {len(all_chunks)}")
    for t, count in sorted(type_counts.items()):
        print(f"  [{t}]: {count} chunks")

    return all_chunks


if __name__ == "__main__":
    # Quick test
    test_docs = [
        Document(
            page_content=(
                "Stock: RELIANCE | Date: 2025-03-22 | Price: ₹2,940.50 | "
                "Day change: +1.2% | 52W High: ₹3,200.00 | 52W Low: ₹2,180.00 | "
                "Market cap: ₹1,98,000 Cr"
            ),
            metadata={"type": "price", "ticker": "RELIANCE", "source": "yfinance"},
        ),
        Document(
            page_content=(
                "SEBI Filing: Paytm compliance notice issued. The Securities and Exchange "
                "Board of India has issued a compliance notice to One97 Communications Ltd "
                "(Paytm) regarding quarterly disclosure norms. The company is required to "
                "submit a detailed response within 15 working days. This follows an earlier "
                "inquiry into the fintech company's financial reporting practices."
            ),
            metadata={"type": "filing", "source": "sebi_rss", "date": "2025-03-22"},
        ),
    ]
    chunks = chunk_documents(test_docs)
    for c in chunks:
        print(f"\n[{c.metadata['type']}] chunk {c.metadata.get('chunk_index','—')}: {c.page_content[:100]}")