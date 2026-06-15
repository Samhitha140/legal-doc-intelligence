"""
services/ingestion.py
PDF ingestion → clause-boundary chunking → vector store
"""

import re
import uuid
from pathlib import Path
from typing import List, Dict, Any

import fitz  # PyMuPDF
from vector_store.chroma_client import TextNode

# ─── Clause boundary patterns ────────────────────────────────────────────────
# Matches common legal section headers like:
#   "1. Definitions"   "ARTICLE IV"   "Section 12.3 – Indemnification"
CLAUSE_HEADER_RE = re.compile(
    r"""
    (?:^|\n)                              # start of line
    (?:
        (?:ARTICLE|SECTION|CLAUSE|EXHIBIT|SCHEDULE|ANNEX)\s+[\dIVXivx]+  # "ARTICLE IV"
        |(?:\d+\.)+\d*\s+[A-Z]           # "12.3 Indemnification"
        |\d+\.\s+[A-Z]                   # "1. Definitions"
    )
    [^\n]{3,80}                           # header text (3-80 chars)
    """,
    re.VERBOSE | re.MULTILINE,
)

# Clause type classifier – keyword → category
CLAUSE_TYPE_MAP: Dict[str, str] = {
    "indemnif": "indemnity",
    "hold harmless": "indemnity",
    "terminat": "termination",
    "intellectual property": "ip_assignment",
    "ip assignment": "ip_assignment",
    "confidential": "confidentiality",
    "non-compete": "non_compete",
    "non compete": "non_compete",
    "liability": "liability",
    "limitation of liability": "liability",
    "force majeure": "force_majeure",
    "governing law": "governing_law",
    "dispute": "dispute_resolution",
    "arbitration": "dispute_resolution",
    "payment": "payment_terms",
    "warranty": "warranty",
    "representation": "representations",
}


def classify_clause_type(text: str) -> str:
    """Return the legal category of a clause based on keyword scan."""
    lower = text.lower()
    for keyword, category in CLAUSE_TYPE_MAP.items():
        if keyword in lower:
            return category
    return "general"


def extract_text_from_pdf(pdf_path: str) -> List[Dict[str, Any]]:
    """
    Extract text page-by-page using PyMuPDF.
    Returns: [{"page": int, "text": str}, ...]
    """
    pages = []
    doc = fitz.open(pdf_path)
    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text("text")  # preserves layout order
        pages.append({"page": page_num + 1, "text": text})
    doc.close()
    return pages


def clause_boundary_chunk(pages: List[Dict[str, Any]], doc_name: str) -> List[TextNode]:
    """
    Split document at legal clause headers → one TextNode per clause.
    Each node carries rich metadata for filtered retrieval.
    """
    # Merge all pages into one string, tracking page boundaries
    full_text = ""
    page_offsets: List[tuple] = []  # (char_start, page_num)
    for p in pages:
        page_offsets.append((len(full_text), p["page"]))
        full_text += p["text"] + "\n"

    def char_to_page(char_idx: int) -> int:
        """Map a character offset back to its page number."""
        page_num = 1
        for offset, pg in page_offsets:
            if char_idx >= offset:
                page_num = pg
        return page_num

    # Find all clause header positions
    splits = [m.start() for m in CLAUSE_HEADER_RE.finditer(full_text)]

    # If no headers found, fall back to paragraph chunking
    if not splits:
        return _paragraph_fallback(full_text, doc_name, pages)

    # Build chunks between headers
    nodes = []
    for i, start in enumerate(splits):
        end = splits[i + 1] if i + 1 < len(splits) else len(full_text)
        chunk_text = full_text[start:end].strip()
        if len(chunk_text) < 50:  # skip near-empty chunks
            continue

        # Extract header line as clause name
        first_line = chunk_text.split("\n")[0].strip()
        clause_type = classify_clause_type(chunk_text)
        page_num = char_to_page(start)

        node = TextNode(
            text=chunk_text,
            id_=str(uuid.uuid4()),
            metadata={
                "doc_name": doc_name,
                "clause_name": first_line,
                "clause_type": clause_type,
                "page": page_num,
                "char_start": start,
            },
        )
        nodes.append(node)

    return nodes


def _paragraph_fallback(
    full_text: str, doc_name: str, pages: List[Dict[str, Any]]
) -> List[TextNode]:
    """Fallback: split on double newlines (paragraphs) when no headers found."""
    paragraphs = re.split(r"\n{2,}", full_text)
    nodes = []
    for i, para in enumerate(paragraphs):
        para = para.strip()
        if len(para) < 100:
            continue
        node = TextNode(
            text=para,
            id_=str(uuid.uuid4()),
            metadata={
                "doc_name": doc_name,
                "clause_name": f"Paragraph {i+1}",
                "clause_type": classify_clause_type(para),
                "page": min(i // 3 + 1, len(pages)),  # rough estimate
            },
        )
        nodes.append(node)
    return nodes


# ─── Main ingestion entry point ───────────────────────────────────────────────
async def ingest_document(pdf_path: str, doc_id: str, doc_name: str) -> Dict[str, Any]:
    """
    Full pipeline:
      PDF → page text → clause chunks → embed → store in vector DB
    Returns metadata dict with chunk count and clause type summary.
    """
    from services.embeddings import get_embedding_model

    # 1. Extract text
    pages = extract_text_from_pdf(pdf_path)

    # 2. Clause-boundary chunk
    nodes = clause_boundary_chunk(pages, doc_name)

    # 3. Attach doc_id to all nodes
    for node in nodes:
        node.metadata["doc_id"] = doc_id

    # 4. Embed + store
    from vector_store.chroma_client import add_nodes

    embed_model = get_embedding_model()

    texts = [n.text for n in nodes]
    embeddings = embed_model.get_text_embedding_batch(texts)

    for node, embedding in zip(nodes, embeddings):
        node.embedding = embedding

    add_nodes(nodes)

    # 5. Summarise clause types found
    from collections import Counter
    clause_type_counts = Counter(n.metadata["clause_type"] for n in nodes)

    return {
        "doc_id": doc_id,
        "doc_name": doc_name,
        "total_pages": len(pages),
        "total_chunks": len(nodes),
        "clause_types": dict(clause_type_counts),
        "status": "success",
    }
