"""
Literature Review MCP Server
提供 3 个 tool：search_papers, download_paper, convert_pdf
"""

import asyncio
import json
import os
import re
import time
from pathlib import Path

import httpx
from fastmcp import FastMCP, Context

mcp = FastMCP(
    name="literature-tools",
    instructions="Academic paper search, download, and PDF-to-Markdown conversion tools.",
)

# ---------------------------------------------------------------------------
# Tool 1: search_papers
# ---------------------------------------------------------------------------


async def _search_semantic_scholar(
    client: httpx.AsyncClient, keywords: str, limit: int, year_from: int | None
) -> list[dict]:
    """Query Semantic Scholar API with retry on 429."""
    params = {
        "query": keywords,
        "limit": min(limit, 100),
        "fields": "title,authors,year,venue,citationCount,abstract,externalIds,openAccessPdf",
    }
    if year_from:
        params["year"] = f"{year_from}-"

    headers = {}
    api_key = os.environ.get("S2_API_KEY", "")
    if api_key:
        headers["x-api-key"] = api_key

    max_retries = 3
    for attempt in range(max_retries):
        try:
            resp = await client.get(
                "https://api.semanticscholar.org/graph/v1/paper/search",
                params=params,
                headers=headers,
                timeout=30.0,
            )
            if resp.status_code == 429:
                wait = 2 ** (attempt + 1)
                await asyncio.sleep(wait)
                continue
            resp.raise_for_status()
            data = resp.json()
            break
        except Exception as e:
            if attempt == max_retries - 1:
                return [
                    {
                        "_error": f"Semantic Scholar failed after {max_retries} retries: {e}"
                    }
                ]
            await asyncio.sleep(2)
    else:
        return [{"_error": "Semantic Scholar: rate limited after all retries"}]

    results = []
    for paper in data.get("data", []):
        authors = [a.get("name", "") for a in (paper.get("authors") or [])]
        ext_ids = paper.get("externalIds") or {}
        oa_pdf = paper.get("openAccessPdf") or {}

        results.append(
            {
                "id": ext_ids.get("ArXiv")
                or ext_ids.get("DOI")
                or paper.get("paperId", ""),
                "title": paper.get("title", ""),
                "authors": authors,
                "year": paper.get("year"),
                "venue": paper.get("venue", ""),
                "citations": paper.get("citationCount", 0),
                "abstract": paper.get("abstract", ""),
                "url": f"https://www.semanticscholar.org/paper/{paper.get('paperId', '')}",
                "source": "semantic_scholar",
                "open_access_url": oa_pdf.get("url", ""),
                "doi": ext_ids.get("DOI", ""),
                "arxiv_id": ext_ids.get("ArXiv", ""),
            }
        )
    return results


async def _search_arxiv(
    client: httpx.AsyncClient, keywords: str, limit: int, year_from: int | None
) -> list[dict]:
    """Query arXiv API (Atom XML)."""
    params = {
        "search_query": f"all:{keywords}",
        "max_results": min(limit, 100),
        "sortBy": "relevance",
    }

    try:
        resp = await client.get(
            "https://export.arxiv.org/api/query",
            params=params,
            timeout=30.0,
        )
        resp.raise_for_status()
        xml_text = resp.text
    except Exception as e:
        return [{"_error": f"arXiv failed: {e}"}]

    results = []
    # Simple XML parsing without lxml dependency
    entries = re.findall(r"<entry>(.*?)</entry>", xml_text, re.DOTALL)
    for entry in entries:
        title = _xml_tag(entry, "title").replace("\n", " ").strip()
        summary = _xml_tag(entry, "summary").replace("\n", " ").strip()
        published = _xml_tag(entry, "published")
        year = int(published[:4]) if published else None

        if year_from and year and year < year_from:
            continue

        # Extract authors
        authors = re.findall(r"<name>(.*?)</name>", entry)

        # Extract arxiv ID from <id> tag
        entry_id = _xml_tag(entry, "id")
        arxiv_id = ""
        if "arxiv.org/abs/" in entry_id:
            arxiv_id = entry_id.split("arxiv.org/abs/")[-1]
            # Remove version suffix for cleaner ID
            arxiv_id_base = re.sub(r"v\d+$", "", arxiv_id)
        else:
            arxiv_id_base = entry_id

        # Extract DOI if present
        doi = ""
        doi_match = re.search(r"<arxiv:doi[^>]*>(.*?)</arxiv:doi>", entry)
        if doi_match:
            doi = doi_match.group(1)

        results.append(
            {
                "id": arxiv_id_base,
                "title": title,
                "authors": authors,
                "year": year,
                "venue": "arXiv",
                "citations": 0,  # arXiv API doesn't provide citation count
                "abstract": summary,
                "url": entry_id,
                "source": "arxiv",
                "open_access_url": f"https://arxiv.org/pdf/{arxiv_id}"
                if arxiv_id
                else "",
                "doi": doi,
                "arxiv_id": arxiv_id_base,
            }
        )
    return results


def _xml_tag(xml: str, tag: str) -> str:
    """Extract text from a simple XML tag."""
    match = re.search(rf"<{tag}[^>]*>(.*?)</{tag}>", xml, re.DOTALL)
    return match.group(1).strip() if match else ""


def _deduplicate(papers: list[dict]) -> list[dict]:
    """Deduplicate by DOI exact match, then by normalized title."""
    seen_doi: set[str] = set()
    seen_title: set[str] = set()
    unique = []

    for p in papers:
        doi = p.get("doi", "").strip().lower()
        if doi and doi in seen_doi:
            continue

        # Normalize title: lowercase, remove punctuation, collapse whitespace
        norm_title = re.sub(r"[^a-z0-9\s]", "", p.get("title", "").lower())
        norm_title = re.sub(r"\s+", " ", norm_title).strip()
        if norm_title in seen_title:
            continue

        if doi:
            seen_doi.add(doi)
        seen_title.add(norm_title)
        unique.append(p)

    return unique


@mcp.tool
async def search_papers(
    keywords: str,
    limit: int = 30,
    year_from: int | None = None,
    ctx: Context = None,
) -> str:
    """Search academic papers from Semantic Scholar and arXiv.

    Args:
        keywords: Search query keywords.
        limit: Max results per source (default 30).
        year_from: Only include papers from this year onwards (optional).

    Returns:
        JSON array of deduplicated paper objects.
    """
    if ctx:
        await ctx.info(
            f"Searching for: {keywords} (limit={limit}, year_from={year_from})"
        )

    async with httpx.AsyncClient() as client:
        ss_task = _search_semantic_scholar(client, keywords, limit, year_from)
        ax_task = _search_arxiv(client, keywords, limit, year_from)
        ss_results, ax_results = await asyncio.gather(ss_task, ax_task)

    # Filter out error entries and log them
    errors = []
    all_papers = []
    for r in ss_results + ax_results:
        if "_error" in r:
            errors.append(r["_error"])
        else:
            all_papers.append(r)

    deduplicated = _deduplicate(all_papers)

    summary = {
        "query": keywords,
        "sources": ["semantic_scholar", "arxiv"],
        "total_before_dedup": len(all_papers),
        "total_after_dedup": len(deduplicated),
        "errors": errors,
        "papers": deduplicated,
    }
    return json.dumps(summary, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# Tool 2: download_paper
# ---------------------------------------------------------------------------


@mcp.tool
async def download_paper(
    paper_id: str,
    url: str,
    output_dir: str = "data/papers",
    ctx: Context = None,
) -> str:
    """Download a paper PDF to local storage.

    Args:
        paper_id: Unique paper identifier (used as filename).
        url: Direct URL to the PDF file.
        output_dir: Directory to save the PDF (default: data/papers).

    Returns:
        JSON with download status and file path.
    """
    if ctx:
        await ctx.info(f"Downloading: {paper_id} from {url}")

    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    # Sanitize filename
    safe_id = re.sub(r"[^\w\-.]", "_", paper_id)
    pdf_path = out_path / f"{safe_id}.pdf"

    # Skip if already downloaded
    if pdf_path.exists() and pdf_path.stat().st_size > 1000:
        return json.dumps(
            {
                "status": "skipped",
                "reason": "already exists",
                "path": str(pdf_path),
            }
        )

    try:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            resp = await client.get(url, timeout=60.0)
            resp.raise_for_status()

            content_type = resp.headers.get("content-type", "")
            if "pdf" not in content_type and not resp.content[:5] == b"%PDF-":
                return json.dumps(
                    {
                        "status": "failed",
                        "reason": f"Not a PDF (content-type: {content_type})",
                        "paper_id": paper_id,
                    }
                )

            pdf_path.write_bytes(resp.content)

        # Rate limiting: 2 second pause
        await asyncio.sleep(2)

        return json.dumps(
            {
                "status": "success",
                "path": str(pdf_path),
                "size_bytes": pdf_path.stat().st_size,
            }
        )

    except Exception as e:
        return json.dumps(
            {
                "status": "failed",
                "reason": str(e),
                "paper_id": paper_id,
            }
        )


# ---------------------------------------------------------------------------
# Tool 3: convert_pdf
# ---------------------------------------------------------------------------


@mcp.tool
def convert_pdf(
    pdf_path: str,
    output_dir: str = "data/papers-md",
) -> str:
    """Convert a PDF to Markdown using marker-pdf.

    Args:
        pdf_path: Path to the input PDF file.
        output_dir: Directory to save the Markdown output (default: data/papers-md).

    Returns:
        JSON with conversion status and output file path.
    """
    from marker.converters.pdf import PdfConverter
    from marker.models import create_model_dict
    from marker.output import text_from_rendered

    pdf = Path(pdf_path)
    if not pdf.exists():
        return json.dumps({"status": "failed", "reason": f"File not found: {pdf_path}"})

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    md_path = out / f"{pdf.stem}.md"

    # Skip if already converted
    if md_path.exists() and md_path.stat().st_size > 100:
        return json.dumps(
            {
                "status": "skipped",
                "reason": "already converted",
                "path": str(md_path),
            }
        )

    try:
        converter = PdfConverter(artifact_dict=create_model_dict())
        rendered = converter(str(pdf))
        text, _, images = text_from_rendered(rendered)

        md_path.write_text(text, encoding="utf-8")

        return json.dumps(
            {
                "status": "success",
                "path": str(md_path),
                "chars": len(text),
                "images": len(images),
            }
        )

    except Exception as e:
        return json.dumps({"status": "failed", "reason": str(e), "pdf_path": pdf_path})


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run(transport="stdio")
