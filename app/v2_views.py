"""Riya. Network view and evidence dossier for Cluster Detail. Observation-only wording. Copy to app/v2_views.py."""
import re
from difflib import SequenceMatcher
from itertools import combinations

import pandas as pd

STOP = {"shree", "shri", "sri", "sree", "new", "the", "om", "sai", "m", "s", "mr", "ms"}
STRUCK = ("strike off", "under process of striking off")
LEAD_LINE = "This is a lead for human review, not a finding of wrongdoing."


def _key(s):
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", str(s).lower())).strip()


def _is_struck(status):
    return str(status).lower().startswith(STRUCK)


def member_edges(members):
    """Links between members: same address, same name stem, registered within 30 days."""
    m = members.reset_index(drop=True)
    keys = m.address_normalized.map(_key)
    stems = m.company_name_normalized.map(lambda s: (str(s).split() or [""])[0])
    dates = pd.to_datetime(m.date_of_registration, errors="coerce")
    edges = []
    for i, j in combinations(range(len(m)), 2):
        kinds = []
        if keys[i] and keys[i] == keys[j]:
            kinds.append("same address")
        if stems[i] and stems[i] == stems[j] and stems[i] not in STOP:
            kinds.append("same name stem")
        if pd.notna(dates[i]) and pd.notna(dates[j]) and abs((dates[i] - dates[j]).days) <= 30:
            kinds.append("registered within 30 days")
        if kinds:
            edges.append((i, j, kinds))
    return edges


def network_html(members, height="420px"):
    """Interactive graph (needs pyvis). Returns None if pyvis is not installed."""
    try:
        from pyvis.network import Network
    except Exception:
        return None
    m = members.reset_index(drop=True)
    net = Network(height=height, width="100%", bgcolor="#07090E", font_color="#E2E8F0", notebook=False)
    for i, r in m.iterrows():
        s = str(r.company_status).lower()
        color = "#F87171" if _is_struck(s) else ("#FBBF24" if "inactive" in s else "#34D399")
        net.add_node(int(i), label=str(r.company_name_raw)[:26], title=f"{r.company_name_raw} | {r.company_status}", color=color)
    for i, j, kinds in member_edges(m):
        net.add_edge(int(i), int(j), title=", ".join(kinds), value=len(kinds))
    return net.generate_html()


def network_fig(members):
    """Static fallback (matplotlib + networkx)."""
    import matplotlib.pyplot as plt
    import networkx as nx
    m = members.reset_index(drop=True)
    g = nx.Graph()
    g.add_nodes_from(range(len(m)))
    for i, j, kinds in member_edges(m):
        g.add_edge(i, j, w=len(kinds))
    colors = ["#F87171" if _is_struck(s) else "#34D399" for s in m.company_status]
    fig, ax = plt.subplots(figsize=(6, 4))
    pos = nx.spring_layout(g, seed=1)
    nx.draw_networkx(g, pos, ax=ax, node_color=colors, labels={i: str(m.company_name_raw[i])[:14] for i in g.nodes},
                     font_size=6, width=[1 + d["w"] for _, _, d in g.edges(data=True)])
    ax.axis("off")
    return fig


def build_dossier(cid, scores, members, explanations, reuse, feature_labels):
    """Plain facts from the data. Numbers and wording come only from the inputs."""
    facts = []
    n = len(members)
    facts.append(f"{n} companies are grouped in this cluster.")
    dates = pd.to_datetime(members.date_of_registration, errors="coerce").dropna()
    if len(dates) >= 2:
        facts.append(f"Registration dates span {(dates.max() - dates.min()).days} days "
                     f"({dates.min().date()} to {dates.max().date()}).")
    n_addr = members.address_normalized.map(_key).nunique()
    facts.append("All companies list the same address." if n_addr == 1 and n > 1
                 else f"The companies list {n_addr} distinct address texts.")
    struck = int(sum(_is_struck(s) for s in members.company_status))
    if struck:
        facts.append(f"{struck} of {n} companies are struck off or under process of striking off.")
    if reuse is not None and len(reuse) and int(reuse.n_clusters.max()) >= 3:
        facts.append(f"The most reused address here appears in {int(reuse.n_clusters.max())} different clusters.")
    m = members.reset_index(drop=True)
    pairs = 0
    for i, j in combinations(range(len(m)), 2):
        di, dj = pd.to_datetime(m.date_of_registration[i], errors="coerce"), pd.to_datetime(m.date_of_registration[j], errors="coerce")
        if pd.isna(di) or pd.isna(dj) or abs((di - dj).days) > 3:
            continue
        a, b = str(m.company_name_normalized[i]), str(m.company_name_normalized[j])
        if a == b or SequenceMatcher(None, a, b).ratio() >= 0.92:
            pairs += 1
    if pairs:
        facts.append(f"{pairs} pair(s) look like the same company recorded twice (similar name, registered within 3 days).")
    if scores:
        flag_disp = {"high_priority": "review suggested"}.get(scores["flag_category"], scores["flag_category"])
        facts.append(f"Model score {float(scores['composite_score']):.1f} out of 100, class: {flag_disp}.")
    if explanations is not None and len(explanations):
        top = [feature_labels.get(r.feature_name, r.feature_name) for r in explanations.head(3).itertuples()]
        facts.append("Top model factors: " + "; ".join(top) + ".")
    text = f"Evidence dossier: cluster {cid}\n" + "\n".join(f"- {f}" for f in facts) + f"\n\n{LEAD_LINE}\n"
    return facts, text
