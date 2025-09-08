# backend/network_analysis.py
from __future__ import annotations
from typing import Iterable, List, Tuple
import networkx as nx

# Tunables to keep the UI snappy and avoid path explosions
MAX_NODES = 1_000
MAX_EDGES = 5_000
MAX_PATHS = 200          # limit number of returned paths
MAX_DEPTH = 25           # max hops when exploring paths

def _normalize_endpoint(ep: str) -> str:
    # Simple normalization to reduce accidental mismatches (e.g., trailing slashes, fragments)
    if not isinstance(ep, str):
        return str(ep)
    ep = ep.strip()
    # remove fragment
    if "#" in ep:
        ep = ep.split("#", 1)[0]
    # collapse multiple slashes except protocol
    if "://" in ep:
        scheme, rest = ep.split("://", 1)
        rest = rest.replace("//", "/")
        ep = f"{scheme}://{rest}"
    # drop trailing slash except bare scheme/host
    if ep.endswith("/") and "://" in ep and ep.count("/") > 2:
        ep = ep[:-1]
    return ep

def build_graph(endpoints: Iterable[str], connections: Iterable[Tuple[str, str]]) -> nx.DiGraph:
    """
    Build a directed graph from endpoints and (src,dst) connections.
    Applies normalization, de-duplication, and size caps.
    """
    G = nx.DiGraph()

    # Add nodes (normalized, de-duped, capped)
    count = 0
    for ep in endpoints or []:
        if count >= MAX_NODES:
            break
        nep = _normalize_endpoint(ep)
        if not nep:
            continue
        if nep not in G:
            G.add_node(nep)
            count += 1

    # Add edges only if both endpoints exist (and cap total)
    ecount = 0
    for pair in connections or []:
        if ecount >= MAX_EDGES:
            break
        if not pair or len(pair) != 2:
            continue
        src, dst = _normalize_endpoint(pair[0]), _normalize_endpoint(pair[1])
        if src in G and dst in G:
            if not G.has_edge(src, dst):
                G.add_edge(src, dst)
                ecount += 1

    return G

def _bounded_all_simple_paths(G: nx.DiGraph, source: str, target: str,
                              cutoff: int, limit: int) -> List[List[str]]:
    """
    A bounded generator for simple paths:
      - cutoff caps maximum path length (number of nodes)
      - limit caps the number of paths returned
    """
    paths: List[List[str]] = []
    try:
        for path in nx.all_simple_paths(G, source=source, target=target, cutoff=cutoff):
            paths.append(path)
            if len(paths) >= limit:
                break
    except Exception:
        # If Nodes not present or other internal errors, return what we have
        pass
    return paths

def find_attack_paths(G: nx.DiGraph, start: str, end: str) -> List[List[str]]:
    """
    Return up to MAX_PATHS simple paths from start to end, bounded by MAX_DEPTH.
    Always returns a list (possibly empty). Never raises.
    """
    if not isinstance(G, nx.DiGraph):
        return []

    # Normalize inputs
    start_n = _normalize_endpoint(start) if start else None
    end_n = _normalize_endpoint(end) if end else None

    # If caller passed invalid / absent nodes, try a reasonable default:
    if not start_n or start_n not in G:
        # pick any node with out-degree > 0, else any node
        candidates = [n for n in G.nodes if G.out_degree(n) > 0]
        start_n = candidates[0] if candidates else (next(iter(G.nodes), None))
    if not end_n or end_n not in G:
        # pick any node with in-degree > 0, else any node
        candidates = [n for n in G.nodes if G.in_degree(n) > 0]
        end_n = candidates[-1] if candidates else (next(iter(G.nodes), None))

    # If still invalid or graph too small, no paths to find
    if not start_n or not end_n or start_n == end_n or G.number_of_nodes() == 0:
        return []

    # Fast-path: if no edge between components, this will just return []
    paths = _bounded_all_simple_paths(G, start_n, end_n, cutoff=MAX_DEPTH, limit=MAX_PATHS)
    return paths
