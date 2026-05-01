"""Assignee Intelligence — rules-based artifact."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.llm_client import RulesArtifactRequest, hash_rules, record_rules_artifact
from app.core.models import PatentPublication

logger = logging.getLogger(__name__)
RULES_ID = "assignee_intelligence_rules"
RULES_VERSION = 1
DEFAULT_WEIGHTS = {"assignee_type": 0.35, "portfolio_signals": 0.25, "commercial_orientation": 0.25, "licensing_potential": 0.15}
_UNI = ("university","institute of technology","national lab","national laborator","research institute","academy","college of")
_GOV = ("department of","ministry of","naval research","air force","army research","darpa")
_MEGA = ("ibm","microsoft","google","alphabet","apple","amazon","meta platforms","facebook","samsung","intel","qualcomm","siemens","ge ","general electric","general motors","toyota","ford motor","boeing","lockheed","raytheon","pfizer","merck","johnson & johnson","novartis")

def _classify(a):
    if not a: return "unknown"
    j=" ".join(x.lower() for x in a)
    if any(h in j for h in _UNI): return "university"
    if any(h in j for h in _GOV): return "gov"
    if any(h in j for h in _MEGA): return "megacorp"
    return "sme"

def _ts(c): return {"university":1.0,"sme":0.75,"gov":0.6,"megacorp":0.35,"unknown":0.5}.get(c,0.5)
def _ps(fs): return min(fs/5.0,1.0)
def _co(c,hc): return min({"university":0.4,"sme":0.75,"gov":0.3,"megacorp":0.9,"unknown":0.5}.get(c,0.5)+(0.1 if hc else 0.0),1.0)
def _lp(c,fs): return min({"university":0.85,"sme":0.65,"gov":0.4,"megacorp":0.25,"unknown":0.5}.get(c,0.5)+fs*0.05,1.0)

@dataclass
class AF:
    assignees: list[str]; assignee_class: str; family_size: int; has_claims: bool; has_abstract: bool
    industries: list[str]; technology_method: list[str]
    def as_dict(self): return {"assignees":self.assignees,"assignee_class":self.assignee_class,"family_size":self.family_size,"has_claims":self.has_claims,"has_abstract":self.has_abstract,"industries":self.industries,"technology_method":self.technology_method}

def extract_features(p):
    t=p.tags or {}
    c=_classify(p.assignees or [])
    return AF(assignees=list(p.assignees or []),assignee_class=c,family_size=len(p.family_members or []),has_claims=bool(p.claims_text),has_abstract=bool(p.abstract),industries=list(t.get("industries") or []),technology_method=list(t.get("technology_method") or []))

def compute_intelligence(f,w=None):
    w=w or DEFAULT_WEIGHTS; comps={}; total=0.0; wt=0.0
    funcs={"assignee_type":lambda:_ts(f.assignee_class),"portfolio_signals":lambda:_ps(f.family_size),"commercial_orientation":lambda:_co(f.assignee_class,f.has_claims),"licensing_potential":lambda:_lp(f.assignee_class,f.family_size)}
    for name,fn in funcs.items():
        sub=float(fn()); ww=float(w.get(name,0.0)); c=sub*ww
        comps[name]={"sub_score":round(sub,4),"weight":ww,"contribution":round(c,4)}
        total+=c; wt+=ww
    if wt>0: total=total/wt
    return {"assignee_intelligence_score":round(100.0*max(0.0,min(total,1.0)),2),"version":RULES_VERSION,"weights":w,"components":comps,"computed_at":datetime.utcnow().isoformat()}

async def generate_assignee_intelligence(session,patent,*,run_id=None,weights=None):
    f=extract_features(patent); w=weights or DEFAULT_WEIGHTS
    rules_hash=hash_rules(RULES_ID,RULES_VERSION,w)
    intel=compute_intelligence(f,w)
    req=RulesArtifactRequest(artifact_type="assignee_intelligence",rules_id=RULES_ID,rules_version=RULES_VERSION,rules_hash=rules_hash,input_payload=f.as_dict(),content_json=intel,patent_publication_id=patent.id,run_id=run_id)
    resp=await record_rules_artifact(session,req)
    return resp.content_json,resp.artifact_id
