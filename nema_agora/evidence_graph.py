"""Phase 30 — evidence provenance graph and report engine.

Builds a bounded lineage graph from recorded provenance plus synthesized claims.
The report is an auditable research artifact, not an authorization or impact
determination.
"""
from __future__ import annotations
from dataclasses import asdict, dataclass
import hashlib, json
from typing import Any, Iterable, Mapping

POLICY_VERSION="phase30-v1"

@dataclass(frozen=True)
class EvidenceNode:
    node_id:str
    node_type:str
    label:str
    source_id:str
    metadata:dict[str,Any]
    def to_dict(self): return asdict(self)

@dataclass(frozen=True)
class EvidenceEdge:
    parent_id:str
    child_id:str
    relation:str="SUPPORTS"
    def to_dict(self): return asdict(self)

@dataclass(frozen=True)
class EvidenceGraph:
    graph_id:str
    nodes:tuple[EvidenceNode,...]
    edges:tuple[EvidenceEdge,...]
    orphan_claims:tuple[str,...]
    missing_parents:tuple[str,...]
    fingerprint:str
    policy_version:str=POLICY_VERSION
    decision_notice:str=("Evidence lineage is an engineering/research artifact; it does not "
        "establish environmental truth, environmental impact, regulatory status, "
        "NEMA authorization, production approval, enforcement, emergency response, "
        "or autonomous decision authority.")
    def to_dict(self): return asdict(self)

def _fp(v:Any)->str:
    return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),default=str).encode()).hexdigest()

def build_evidence_graph(*, provenance_records:Iterable[Mapping[str,Any]], synthesis:Mapping[str,Any])->EvidenceGraph:
    records=list(provenance_records)
    nodes=[]; edges=[]; ids=set()
    for r in records:
        pid=str(r.get("provenance_id","")).strip()
        if not pid: continue
        ids.add(pid)
        nodes.append(EvidenceNode(pid,str(r.get("event_type","UNKNOWN")),str(r.get("event_id",pid)),pid,{
            "dataset_version":r.get("dataset_version"),"dataset_hash":r.get("dataset_hash"),
            "model_identity":r.get("model_identity",{}),"evidence_hash":r.get("evidence_hash"),
        }))
    missing=set()
    for r in records:
        child=str(r.get("provenance_id","")).strip()
        if not child: continue
        for parent in r.get("parent_ids",()):
            parent=str(parent)
            if parent in ids: edges.append(EvidenceEdge(parent,child,"DERIVES_FROM"))
            else: missing.add(parent)
    claim_nodes=[]
    orphan=[]
    domains=synthesis.get("domains",{}) if isinstance(synthesis,Mapping) else {}
    for claim in synthesis.get("claims",()) if isinstance(synthesis,Mapping) else ():
        cid=str(claim.get("claim_id","")).strip()
        if not cid: continue
        claim_nodes.append(EvidenceNode("CLAIM-"+cid,"CLAIM",str(claim.get("claim",cid)),cid,{
            "domain":claim.get("evidence_domain"),"sample_size":claim.get("sample_size",0),
            "support_status":claim.get("support_status"),
            "limitations":claim.get("limitations",[]),
        }))
        sources=set(str(x) for x in claim.get("source_ids",()) if str(x).strip())
        linked=False
        for source in sources:
            if source in ids:
                edges.append(EvidenceEdge(source,"CLAIM-"+cid,"SUPPORTS"))
                linked=True
        if not linked: orphan.append(cid)
    nodes.extend(claim_nodes)
    payload={"nodes":[n.to_dict() for n in nodes],"edges":[e.to_dict() for e in edges],
             "orphan_claims":sorted(orphan),"missing_parents":sorted(missing)}
    digest=_fp(payload)
    return EvidenceGraph("GRAPH-"+digest[:16].upper(),tuple(nodes),tuple(edges),
        tuple(sorted(orphan)),tuple(sorted(missing)),digest)

def validate_graph(graph:EvidenceGraph)->dict[str,Any]:
    node_ids={n.node_id for n in graph.nodes}; errors=[]
    for edge in graph.edges:
        if edge.parent_id not in node_ids: errors.append("MISSING_EDGE_PARENT:"+edge.parent_id)
        if edge.child_id not in node_ids: errors.append("MISSING_EDGE_CHILD:"+edge.child_id)
    errors.extend("MISSING_PARENT:"+x for x in graph.missing_parents)
    errors.extend("ORPHAN_CLAIM:"+x for x in graph.orphan_claims)
    return {"valid":not errors,"errors":errors,"nodes":len(graph.nodes),"edges":len(graph.edges),
            "policy_version":POLICY_VERSION,"decision_notice":graph.decision_notice}

def build_research_report(*, synthesis:Mapping[str,Any], graph:EvidenceGraph)->dict[str,Any]:
    validation=validate_graph(graph)
    domains=synthesis.get("domains",{})
    claims=synthesis.get("claims",[])
    return {
        "report_id":"REPORT-"+_fp({"synthesis":synthesis.get("evidence_fingerprint"),"graph":graph.fingerprint})[:16].upper(),
        "title":"NEMA-AGORA Evidence and Governance Report",
        "policy_version":POLICY_VERSION,
        "executive_summary":(
            "This report summarizes bounded engineering, workflow, governance and research evidence "
            "and preserves claim-level limitations."
        ),
        "evidence_domains":domains,
        "claim_evidence_limitation_matrix":claims,
        "provenance_graph":graph.to_dict(),
        "validation":validation,
        "limitations":list(synthesis.get("limitations",[])),
        "decision_notice":graph.decision_notice,
    }

def serialise_report(report:Mapping[str,Any])->str:
    return json.dumps(dict(report),sort_keys=True,indent=2,ensure_ascii=False)
