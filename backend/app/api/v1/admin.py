1|import logging
2|from datetime import date
3|from datetime import datetime as _dt
4|from datetime import timezone as _tz
5|from typing import Any, Literal
6|
7|from celery.result import AsyncResult
8|from fastapi import APIRouter, Depends, HTTPException
9|from pydantic import BaseModel, Field
10|from sqlalchemy import func, select
11|
12|from app.api.deps import AppSettings, DbSession, current_user, get_db
13|from app.config import settings
14|from app.core.ai_models import User as _UserModel
15|from app.core.schemas import TaskStatusResponse
16|from app.tasks.celery_app import celery_app
17|from app.tasks.ingest_applications import ingest_weekly_applications
18|from app.tasks.ingest_grants import ingest_weekly_grants
19|
20|_log = logging.getLogger(__name__)
21|
22|router = APIRouter()
23|
24|DEFAULT_THEMES = [
25|    {"name": "Human Necessities", "cpc_prefixes": ["A"], "assignee_keywords": [], "title_keywords": [], "description": "Biotechnology, pharma, food, agriculture"},
26|    {"name": "Performing Operations", "cpc_prefixes": ["B"], "assignee_keywords": [], "title_keywords": [], "description": "Manufacturing, transport, tools"},
27|    {"name": "Chemistry & Metallurgy", "cpc_prefixes": ["C"], "assignee_keywords": [], "title_keywords": [], "description": "Chemical processes, materials, metallurgy"},
28|    {"name": "Textiles & Paper", "cpc_prefixes": ["D"], "assignee_keywords": [], "title_keywords": [], "description": "Textiles, paper, flexible materials"},
29|    {"name": "Fixed Constructions", "cpc_prefixes": ["E"], "assignee_keywords": [], "title_keywords": [], "description": "Building, construction, mining"},
30|    {"name": "Mechanical Engineering", "cpc_prefixes": ["F"], "assignee_keywords": [], "title_keywords": [], "description": "Engines, pumps, mechanical systems"},
31|    {"name": "Physics & Computing", "cpc_prefixes": ["G"], "assignee_keywords": [], "title_keywords": [], "description": "AI/ML, computing, optics, instruments"},
32|    {"name": "Electricity & Electronics", "cpc_prefixes": ["H"], "assignee_keywords": [], "title_keywords": [], "description": "Electronics, communications, energy"},
33|]
34|
35|DEFAULT_TOPICS = [
36|    {
37|        "name": "AI Agents & LLMs",
38|        "description": "Autonomous agents, large language models, RAG, prompt engineering, multi-agent systems",
39|        "cpc_prefixes": ["G06N", "G06F"],
40|        "keywords": ["agent", "LLM", "large language model", "prompt", "retrieval augmented", "multi-agent", "autonomous", "reasoning"],
41|        "opportunity_tags": ["startup", "enterprise", "cross_industry"],
42|        "min_opportunity_score": 30,
43|    },
44|    {
45|        "name": "Robotics & Automation",
46|        "description": "Industrial robots, autonomous vehicles, manipulation, perception, human-robot interaction",
47|        "cpc_prefixes": ["B25J", "G05D", "G05B"],
48|        "keywords": ["robot", "autonomous", "manipulation", "gripper", "end effector", "SLAM", "path planning", "human-robot"],
49|        "opportunity_tags": ["enterprise", "revival"],
50|        "min_opportunity_score": 25,
51|    },
52|    {
53|        "name": "Climate Tech",
54|        "description": "Carbon capture, renewable energy, energy storage, green materials, climate adaptation",
55|        "cpc_prefixes": ["Y02E", "Y02C", "Y02P", "B01D"],
56|        "keywords": ["carbon capture", "renewable", "solar", "wind", "battery", "energy storage", "hydrogen", "decarbonization"],
57|        "opportunity_tags": ["sustainability", "startup"],
58|        "min_opportunity_score": 25,
59|    },
60|    {
61|        "name": "Battery Technology",
62|        "description": "Lithium-ion, solid-state, sodium-ion, flow batteries, battery management systems",
63|        "cpc_prefixes": ["H01M", "H02J"],
64|        "keywords": ["lithium", "solid state", "sodium ion", "cathode", "anode", "electrolyte", "BMS", "thermal runaway"],
65|        "opportunity_tags": ["enterprise", "sustainability"],
66|        "min_opportunity_score": 30,
67|    },
68|    {
69|        "name": "Biotech & Gene Therapy",
70|        "description": "CRISPR, mRNA, cell therapy, gene editing, protein engineering, precision medicine",
71|        "cpc_prefixes": ["C12N", "C07K", "A61K"],
72|        "keywords": ["CRISPR", "mRNA", "gene therapy", "cell therapy", "CAR-T", "protein engineering", "monoclonal antibody"],
73|        "opportunity_tags": ["startup", "revival"],
74|        "min_opportunity_score": 30,
75|    },
76|    {
77|        "name": "Quantum Computing",
78|        "description": "Quantum processors, error correction, quantum algorithms, quantum networking, quantum sensing",
79|        "cpc_prefixes": ["G06N", "H01L"],
80|        "keywords": ["quantum", "qubit", "superconducting", "trapped ion", "quantum error", "quantum annealing", "entanglement"],
81|        "opportunity_tags": ["cross_industry", "startup"],
82|        "min_opportunity_score": 25,
83|    },
84|]
85|
86|
87|async def require_admin(
88|    user_id: str = Depends(current_user),
89|    db = Depends(get_db),
90|) -> _UserModel:
91|    user = (await db.execute(select(_UserModel).where(_UserModel.id == user_id))).scalar_one_or_none()
92|    if user is None or not user.is_admin:
93|        raise HTTPException(status_code=403, detail="Admin required")
94|    return user
95|
96|
97|class TriggerIngestRequest(BaseModel):
98|    type: Literal["grants", "applications", "epo", "pct"] = Field(...)
99|    target_date: date | None = None
100|    max_results: int | None = Field(default=None, ge=1, le=1000)
101|
102|
103|@router.post("/trigger-ingest", response_model=TaskStatusResponse)
104|async def trigger_ingest(
105|    request: TriggerIngestRequest,
106|    admin: _UserModel = Depends(require_admin),
107|) -> TaskStatusResponse:
108|    """
109|    Manually trigger patent ingestion (development only).
110|
111|    Supported types:
112|    - grants: USPTO granted patents (Tuesday)
113|    - applications: USPTO published applications (Thursday)
114|    - epo: EPO publications (Wednesday) - requires EPO credentials
115|    - pct: WIPO PCT applications (Thursday)
116|
117|    Enqueues the appropriate Celery task and returns the task ID.
118|    """
119|    if settings.environment == "production":
120|        raise HTTPException(status_code=403, detail="Not available in production")
121|
122|    target_date_str = request.target_date.isoformat() if request.target_date else None
123|
124|    if request.type == "grants":
125|        task = ingest_weekly_grants.delay(target_date_str)
126|    elif request.type == "applications":
127|        task = ingest_weekly_applications.delay(target_date_str)
128|    elif request.type == "epo":
129|        from app.tasks.ingest_epo import ingest_weekly_epo
130|
131|        if not settings.epo_ops_client_id:
132|            raise HTTPException(
133|                status_code=400, detail="EPO OPS credentials not configured"
134|            )
135|        task = ingest_weekly_epo.delay(target_date_str)
136|    elif request.type == "pct":
137|        from app.tasks.ingest_wipo import ingest_weekly_pct
138|
139|        max_results = request.max_results or 100
140|        task = ingest_weekly_pct.delay(target_date_str, max_results)
141|    else:
142|        raise HTTPException(status_code=400, detail=f"Unknown type: {request.type}")
143|
144|    return TaskStatusResponse(
145|        task_id=task.id,
146|        status="PENDING",
147|        result=None,
148|    )
149|
150|
151|@router.get("/task-status/{task_id}", response_model=TaskStatusResponse)
152|async def get_task_status(task_id: str) -> TaskStatusResponse:
153|    """Get status of a Celery task."""
154|    if settings.environment == "production":
155|        raise HTTPException(status_code=403, detail="Not available in production")
156|
157|    result = AsyncResult(task_id, app=celery_app)
158|
159|    return TaskStatusResponse(
160|        task_id=task_id,
161|        status=result.status,
162|        result=result.result if result.ready() else None,
163|    )
164|
165|
166|@router.post("/trigger-summarize", response_model=TaskStatusResponse)
167|async def trigger_batch_summarize(
168|    limit: int = 10,
169|    admin: _UserModel = Depends(require_admin),
170|) -> TaskStatusResponse:
171|    """
172|    Manually trigger batch summarization (development only).
173|    """
174|    if settings.environment == "production":
175|        raise HTTPException(status_code=403, detail="Not available in production")
176|
177|    from app.tasks.summarize import batch_summarize_pending
178|
179|    task = batch_summarize_pending.delay(limit)
180|
181|    return TaskStatusResponse(
182|        task_id=task.id,
183|        status="PENDING",
184|        result=None,
185|    )
186|
187|
188|@router.post("/trigger-family-resolution", response_model=TaskStatusResponse)
189|async def trigger_family_resolution(
190|    limit: int = 100,
191|    admin: _UserModel = Depends(require_admin),
192|) -> TaskStatusResponse:
193|    """
194|    Manually trigger INPADOC family resolution (development only).
195|
196|    Requires EPO OPS credentials.
197|    """
198|    if settings.environment == "production":
199|        raise HTTPException(status_code=403, detail="Not available in production")
200|
201|    if not settings.epo_ops_client_id:
202|        raise HTTPException(status_code=400, detail="EPO OPS credentials not configured")
203|
204|    from app.tasks.ingest_epo import resolve_epo_families
205|
206|    task = resolve_epo_families.delay(limit)
207|
208|    return TaskStatusResponse(
209|        task_id=task.id,
210|        status="PENDING",
211|        result=None,
212|    )
213|
214|
215|@router.post("/trigger-expiry-backfill", response_model=TaskStatusResponse)
216|async def trigger_expiry_backfill(
217|    app_settings: AppSettings,
218|    admin: _UserModel = Depends(require_admin),
219|) -> TaskStatusResponse:
220|    """
221|    Trigger backfill of USPTO grants from 2006-2011 for expiry window population (development only).
222|    """
223|    if app_settings.environment == "production":
224|        raise HTTPException(status_code=403, detail="Not available in production")
225|
226|    from app.tasks.ingest_grants import ingest_expiry_window_grants
227|
228|    task = ingest_expiry_window_grants.delay()
229|
230|    return TaskStatusResponse(task_id=task.id, status="PENDING", result=None)
231|
232|
233|@router.post("/seed-themes")
234|async def seed_themes(db: DbSession, settings: AppSettings) -> dict[str, Any]:
235|    """
236|    Seed default CPC-section themes and user topic packs if they don't already exist
237|    (development only).
238|    """
239|    if settings.environment == "production":
240|        raise HTTPException(status_code=403, detail="Not available in production")
241|
242|    from app.core.theme_models import Theme
243|
244|    created = 0
245|    skipped = 0
246|
247|    for theme_data in DEFAULT_THEMES:
248|        name = theme_data["name"]
249|        result = await db.execute(select(Theme).where(Theme.name == name))
250|        existing = result.scalar_one_or_none()
251|
252|        if existing:
253|            skipped += 1
254|        else:
255|            theme = Theme(
256|                name=name,
257|                description=theme_data["description"],
258|                cpc_prefixes=theme_data["cpc_prefixes"],
259|                assignee_keywords=theme_data["assignee_keywords"],
260|                title_keywords=theme_data["title_keywords"],
261|            )
262|            db.add(theme)
263|            created += 1
264|
265|    # Seed default user topic packs
266|    for topic_data in DEFAULT_TOPICS:
267|        name = topic_data["name"]
268|        result = await db.execute(select(Theme).where(Theme.name == name))
269|        existing = result.scalar_one_or_none()
270|
271|        if existing:
272|            skipped += 1
273|        else:
274|            theme = Theme(
275|                name=name,
276|                description=topic_data["description"],
277|                cpc_prefixes=topic_data["cpc_prefixes"],
278|                keywords=topic_data.get("keywords"),
279|                opportunity_tags=topic_data.get("opportunity_tags"),
280|                min_opportunity_score=topic_data.get("min_opportunity_score"),
281|                user_id="default_pack",
282|            )
283|            db.add(theme)
284|            created += 1
285|
286|    await db.commit()
287|
288|    return {"created": created, "skipped": skipped}
289|
290|
291|@router.post("/trigger-enrich-abstracts", response_model=TaskStatusResponse)
292|async def trigger_enrich_abstracts(
293|    batch_size: int = 200,
294|    admin: _UserModel = Depends(require_admin),
295|) -> TaskStatusResponse:
296|    """
297|    Fetch abstracts from EPO OPS for patents missing them (development only).
298|
299|    This is the critical step to get high-quality AI summaries.
300|    EPO OPS rate limit: ~120 requests/min, so 200 patents takes ~2 minutes.
301|    """
302|    if settings.environment == "production":
303|        raise HTTPException(status_code=403, detail="Not available in production")
304|
305|    if not settings.epo_ops_client_id:
306|        raise HTTPException(status_code=400, detail="EPO OPS credentials not configured")
307|
308|    from app.tasks.enrich_abstracts import enrich_batch
309|
310|    task = enrich_batch.delay(batch_size)
311|
312|    return TaskStatusResponse(task_id=task.id, status="PENDING", result=None)
313|
314|
315|@router.post("/trigger-resummarize", response_model=TaskStatusResponse)
316|async def trigger_resummarize(
317|    limit: int = 50,
318|    admin: _UserModel = Depends(require_admin),
319|) -> TaskStatusResponse:
320|    """
321|    Re-summarize patents that now have abstracts but were previously
322|    summarized with title-only (development only).
323|    """
324|    if settings.environment == "production":
325|        raise HTTPException(status_code=403, detail="Not available in production")
326|
327|    from app.tasks.summarize import batch_resummarize_enriched
328|
329|    task = batch_resummarize_enriched.delay(limit)
330|
331|    return TaskStatusResponse(task_id=task.id, status="PENDING", result=None)
332|
333|
334|@router.post("/trigger-match-themes", response_model=TaskStatusResponse)
335|async def trigger_match_themes(
336|    app_settings: AppSettings,
337|    admin: _UserModel = Depends(require_admin),
338|) -> TaskStatusResponse:
339|    """
340|    Trigger theme matching for all active themes (development only).
341|    """
342|    if app_settings.environment == "production":
343|        raise HTTPException(status_code=403, detail="Not available in production")
344|
345|    from app.tasks.theme_matcher import match_all_themes
346|
347|    task = match_all_themes.delay(limit_per_theme=10000)
348|
349|    return TaskStatusResponse(task_id=task.id, status="PENDING", result=None)
350|
351|
352|# ── Sprint 7: Admin user management ──────────────────────────────────
353|
354|
355|class TierOverrideBody(BaseModel):
356|    tier: str
357|    reason: str | None = None
358|
359|
360|@router.get("/users")
361|async def admin_list_users(
362|    admin: _UserModel = Depends(require_admin),
363|    db = Depends(get_db),
364|    page: int = 1,
365|    page_size: int = 20,
366|):
367|    from app.core.ai_models import User
368|    from app.core.billing_models import BillingSubscription
369|    total = (await db.execute(
370|        select(func.count()).select_from(User)
371|    )).scalar()
372|    users = (await db.execute(
373|        select(User).offset((page - 1) * page_size).limit(page_size).order_by(User.created_at.desc())
374|    )).scalars().all()
375|    user_ids = [u.id for u in users]
376|    billing_map = {}
377|    if user_ids:
378|        rows = (await db.execute(
379|            select(BillingSubscription).where(BillingSubscription.user_id.in_(user_ids))
380|        )).scalars().all()
381|        billing_map = {b.user_id: b for b in rows}
382|    return {
383|        "users": [{
384|            "id": u.id, "email": u.email, "display_name": u.display_name,
385|            "tier": u.tier,
386|            "billing_status": billing_map[u.id].status if u.id in billing_map else None,
387|            "current_period_end": billing_map[u.id].current_period_end.isoformat() if u.id in billing_map and billing_map[u.id].current_period_end else None,
388|            "created_at": u.created_at.isoformat() if u.created_at else None,
389|        } for u in users],
390|        "total": total, "page": page,
391|    }
392|
393|
394|@router.post("/users/{user_id}/tier")
395|async def admin_override_tier(
396|    user_id: str,
397|    body: TierOverrideBody,
398|    admin: _UserModel = Depends(require_admin),
399|    db=Depends(get_db),
400|):
401|    from app.core.ai_models import User
402|    from app.core.billing_models import BillingSubscription
403|    if body.tier not in ("free", "basic", "lifetime", "enterprise"):
404|        raise HTTPException(status_code=422, detail=f"Invalid tier: {body.tier}")
405|    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
406|    if not user:
407|        raise HTTPException(status_code=404, detail="User not found")
408|    old_tier = user.tier
409|    user.tier = body.tier
410|    await db.commit()
411|    existing = (await db.execute(
412|        select(BillingSubscription).where(BillingSubscription.user_id == user_id)
413|    )).scalar_one_or_none()
414|    row = existing or BillingSubscription(user_id=user_id)
415|    row.tier = body.tier
416|    row.status = "active"
417|    row.updated_at = _dt.now(_tz.utc)
418|    db.add(row)
419|    await db.commit()
420|    _log.info("Admin tier override: user=%s old=%s new=%s reason=%s", user_id, old_tier, body.tier, body.reason)
421|    return {"user_id": user_id, "tier": body.tier, "old_tier": old_tier}
422|
423|
424|@router.get("/exports")
425|async def admin_list_exports(admin: _UserModel = Depends(require_admin), db=Depends(get_db)):
426|    from app.core.ai_models import User
427|    from app.core.billing_models import Export
428|    exports = (await db.execute(
429|        select(Export).order_by(Export.created_at.desc()).limit(100)
430|    )).scalars().all()
431|    user_ids = list({e.user_id for e in exports})
432|    users_map = {}
433|    if user_ids:
434|        users_map = {u.id: u.email or u.id for u in (
435|            await db.execute(select(User).where(User.id.in_(user_ids)))
436|        ).scalars().all()}
437|    return [{
438|        "id": str(e.id), "user_id": e.user_id,
439|        "user_email": users_map.get(e.user_id, e.user_id),
440|        "export_type": e.export_type, "scope": e.scope,
441|        "payload_size_bytes": e.payload_size_bytes,
442|        "created_at": e.created_at.isoformat() if e.created_at else None,
443|    } for e in exports]
444|
445|
446|@router.post("/trigger-assignee-backfill", response_model=TaskStatusResponse)
447|async def trigger_assignee_backfill(
448|    admin: _UserModel = Depends(require_admin),
449|) -> TaskStatusResponse:
450|    """Manually trigger assignee normalization backfill.
451|
452|    Runs the same idempotent upsert as the daily 04:00 UTC beat schedule.
453|    Populates normalized assignee names and entity_type heuristics from
454|    patent_publications.assignees. Safe to run repeatedly — the ON CONFLICT
455|    clause handles existing rows.
456|    """
457|    from app.tasks.backfill_assignees import backfill_assignees_task
458|
459|    task = backfill_assignees_task.delay()
460|    return TaskStatusResponse(task_id=task.id, status="enqueued")
461|
462|
463|@router.post("/debug/sentry")
464|async def trigger_sentry_test(
465|    admin: _UserModel = Depends(require_admin),
466|):
467|    """Trigger a test exception to verify the Sentry pipeline.
468|
469|    Returns 500 with a unique marker so the admin can identify the
470|    corresponding event in Sentry.
471|    """
472|    raise RuntimeError("PR8 Sentry debug — intentional test exception")
473|
474|
475|# ── System health ────────────────────────────────────────────
476|
477|
478|@router.get("/system-health")
479|async def admin_system_health(
480|    admin: _UserModel = Depends(require_admin),
481|):
482|    """Returns Anthropic API health status for monitoring."""
483|    from app.tasks.tag import (
484|        _LAST_ANTHROPIC_ERROR_AT,
485|        ANTHROPIC_ERROR_MAX_CONSECUTIVE,
486|        _anthropic_error_count,
487|    )
488|
489|    status = "ok"
490|    if _anthropic_error_count >= ANTHROPIC_ERROR_MAX_CONSECUTIVE:
491|        status = "credits_exhausted"
492|    elif _anthropic_error_count > 0:
493|        status = "degraded"
494|
495|    return {
496|        "anthropic_status": status,
497|        "anthropic_consecutive_errors": _anthropic_error_count,
498|        "anthropic_last_error_at": _LAST_ANTHROPIC_ERROR_AT,
499|        "circuit_broken": _anthropic_error_count >= ANTHROPIC_ERROR_MAX_CONSECUTIVE,
500|    }
501|
502|
503|# ── Data health ──────────────────────────────────────────────
504|
505|
506|@router.get("/llm-provider")
507|async def admin_llm_provider(
508|    admin: _UserModel = Depends(require_admin),
509|):
510|    """Check current LLM provider."""
511|    return {
512|        "provider": settings.llm_provider or "deepseek",
513|        "model": settings.deepseek_chat_model if (settings.llm_provider or "deepseek") == "deepseek" else settings.claude_model,
514|        "deepseek_configured": bool(settings.deepseek_api_key),
515|        "anthropic_configured": bool(settings.anthropic_api_key),
516|    }
517|
518|
519|@router.post("/llm-provider")
520|async def admin_set_llm_provider(
521|    payload: dict[str, str],
522|    admin: _UserModel = Depends(require_admin),
523|):
524|    """Switch LLM provider. Writes to a runtime override. Requires restart."""
525|    provider = (payload.get("provider") or "").lower()
526|    if provider not in ("deepseek", "anthropic"):
527|        raise HTTPException(400, "provider must be 'deepseek' or 'anthropic'")
528|    # Write to app.env for persistence across restarts
529|    import os
530|    env_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "app.env")
531|    env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "app.env"))
532|    try:
533|        with open(env_path, "r") as f:
534|            lines = f.readlines()
535|        with open(env_path, "w") as f:
536|            found = False
537|            for line in lines:
538|                if line.startswith("LLM_PROVIDER="):
539|                    f.write(f"LLM_PROVIDER={provider}\n")
540|                    found = True
541|                else:
542|                    f.write(line)
543|            if not found:
544|                f.write(f"\nLLM_PROVIDER={provider}\n")
545|        # Update runtime setting
546|        settings.llm_provider = provider
547|        return {"provider": provider, "restart_required": True}
548|    except Exception as e:
549|        raise HTTPException(500, f"Failed to update: {e}")
550|
551|
552|@router.get("/data-health")
553|async def admin_data_health(
554|    admin: _UserModel = Depends(require_admin),
555|    db=Depends(get_db),
556|):
557|    """Aggregated patent data health across offices and coverage axes."""
558|    from app.core.models import PatentPublication, SourceFetch
559|
560|    # Per-office counts
561|    office_rows = (await db.execute(
562|        select(
563|            PatentPublication.office,
564|            func.count(PatentPublication.id).label("total"),
565|            func.count(PatentPublication.abstract).label("with_abstract"),
566|            func.count(PatentPublication.claims_text).label("with_claims"),
567|            func.count(PatentPublication.figure_page_url).label("with_figure_url"),
568|            func.count(PatentPublication.embedding).label("with_embedding"),
569|            func.count(PatentPublication.tags).label("with_tags"),
570|            func.count(PatentPublication.summarized_at).label("with_summary"),
571|        ).group_by(PatentPublication.office)
572|    )).all()
573|
574|    # Citation coverage
575|    citation_stats = (await db.execute(
576|        select(
577|            func.count(PatentPublication.id).label("total_patents"),
578|            func.count(PatentPublication.id).filter(
579|                func.jsonb_array_length(PatentPublication.citations_forward) > 0
580|            ).label("with_forward_citations"),
581|            func.count(PatentPublication.id).filter(
582|                func.jsonb_array_length(PatentPublication.citations_backward) > 0
583|            ).label("with_backward_citations"),
584|        )
585|    )).one()
586|
587|    # Family coverage
588|    family_stats = (await db.execute(
589|        select(
590|            func.count(PatentPublication.id).filter(
591|                PatentPublication.family_id.isnot(None)
592|            ).label("with_family_id"),
593|            func.count(PatentPublication.id).filter(
594|                func.jsonb_array_length(PatentPublication.family_members) > 0
595|            ).label("with_family_members"),
596|        )
597|    )).one()
598|
599|    # Recent source_fetches failures
600|    recent_failures = (await db.execute(
601|        select(SourceFetch)
602|        .where(SourceFetch.status.in_(["failed", "blocked"]))
603|        .order_by(SourceFetch.created_at.desc())
604|        .limit(10)
605|    )).scalars().all()
606|
607|    # Latest success per provider
608|    latest_success = (await db.execute(
609|        select(
610|            SourceFetch.provider,
611|            func.max(SourceFetch.created_at).label("last_success"),
612|        )
613|        .where(SourceFetch.status == "success")
614|        .group_by(SourceFetch.provider)
615|    )).all()
616|
617|    total = sum(r.total for r in office_rows)
618|
619|    return {
620|        "total_patents": total,
621|        "by_office": [
622|            {
623|                "office": r.office,
624|                "total": r.total,
625|                "abstract_pct": round(r.with_abstract / r.total * 100, 1) if r.total else 0,
626|                "claims_pct": round(r.with_claims / r.total * 100, 1) if r.total else 0,
627|                "figure_url_pct": round(r.with_figure_url / r.total * 100, 1) if r.total else 0,
628|                "embedding_pct": round(r.with_embedding / r.total * 100, 1) if r.total else 0,
629|                "tags_pct": round(r.with_tags / r.total * 100, 1) if r.total else 0,
630|                "summary_pct": round(r.with_summary / r.total * 100, 1) if r.total else 0,
631|            }
632|            for r in office_rows
633|        ],
634|        "citations": {
635|            "total": citation_stats.total_patents,
636|            "forward_pct": round(
637|                citation_stats.with_forward_citations / citation_stats.total_patents * 100, 1
638|            ) if citation_stats.total_patents else 0,
639|            "backward_pct": round(
640|                citation_stats.with_backward_citations / citation_stats.total_patents * 100, 1
641|            ) if citation_stats.total_patents else 0,
642|        },
643|        "family": {
644|            "with_family_id": family_stats.with_family_id,
645|            "with_family_members": family_stats.with_family_members,
646|        },
647|        "recent_failures": [
648|            {
649|                "id": str(f.id),
650|                "provider": f.provider,
651|                "target_type": f.target_type,
652|                "target_id": f.target_id,
653|                "error_message": f.error_message[:200] if f.error_message else None,
654|                "created_at": f.created_at.isoformat() if f.created_at else None,
655|            }
656|            for f in recent_failures
657|        ],
658|        "latest_success_by_provider": {
659|            r.provider: r.last_success.isoformat() if r.last_success else None
660|            for r in latest_success
661|        },
662|    }
663|
664|
665|@router.get("/source-fetches")
666|async def admin_source_fetches(
667|    admin: _UserModel = Depends(require_admin),
668|    db=Depends(get_db),
669|    limit: int = 20,
670|    provider: str | None = None,
671|    status: str | None = None,
672|):
673|    """Recent source fetch log entries."""
674|    from app.core.models import SourceFetch
675|
676|    q = select(SourceFetch).order_by(SourceFetch.created_at.desc())
677|    if provider:
678|        q = q.where(SourceFetch.provider == provider)
679|    if status:
680|        q = q.where(SourceFetch.status == status)
681|    q = q.limit(min(limit, 100))
682|
683|    rows = (await db.execute(q)).scalars().all()
684|    return [
685|        {
686|            "id": str(r.id),
687|            "provider": r.provider,
688|            "office": r.office,
689|            "target_type": r.target_type,
690|            "target_id": r.target_id,
691|            "source_url": r.source_url,
692|            "status": r.status,
693|            "http_status": r.http_status,
694|            "error_message": r.error_message[:300] if r.error_message else None,
695|            "records_found": r.records_found,
696|            "duration_ms": r.duration_ms,
697|            "retry_count": r.retry_count,
698|            "started_at": r.started_at.isoformat() if r.started_at else None,
699|            "completed_at": r.completed_at.isoformat() if r.completed_at else None,
700|            "created_at": r.created_at.isoformat() if r.created_at else None,
701|        }
702|        for r in rows
703|    ]
704|
705|
706|# ── Phase 1: Admin embedding management ──────────────────────────
707|
708|
709|@router.post("/embed/{patent_id}")
710|async def admin_re_embed_patent(
711|    patent_id: str,
712|    admin: _UserModel = Depends(require_admin),
713|    db=Depends(get_db),
714|):
715|    """Force (re-)generate the embedding for a single patent.
716|
717|    Overwrites any existing embedding. Requires admin access.
718|    """
719|    from uuid import UUID
720|
721|    from app.ai.embedder import EmbeddingError, PatentEmbedder
722|    from app.core.models import PatentPublication
723|
724|    try:
725|        pid = UUID(patent_id)
726|    except ValueError:
727|        raise HTTPException(status_code=400, detail="Invalid patent ID format")
728|
729|    result = await db.execute(
730|        select(PatentPublication).where(PatentPublication.id == pid)
731|    )
732|    patent = result.scalar_one_or_none()
733|
734|    if not patent:
735|        raise HTTPException(status_code=404, detail="Patent not found")
736|
737|    if not patent.title and not patent.abstract:
738|        raise HTTPException(
739|            status_code=400,
740|            detail="Patent has no title or abstract — nothing to embed",
741|        )
742|
743|    try:
744|        with PatentEmbedder() as embedder:
745|            embedding = embedder.generate_patent_embedding(patent)
746|    except EmbeddingError as e:
747|        raise HTTPException(
748|            status_code=503,
749|            detail=f"Embedding generation failed: {e}",
750|        )
751|
752|    patent.embedding = embedding
753|    await db.commit()
754|
755|    return {
756|        "patent_id": str(patent.id),
757|        "doc_id": patent.doc_id,
758|        "status": "re-embedded",
759|        "dimensions": len(embedding),
760|    }
761|
762|
763|@router.get("/embedding-stats")
764|async def admin_embedding_stats(
765|    admin: _UserModel = Depends(require_admin),
766|    db=Depends(get_db),
767|):
768|    """Return embedding coverage statistics.
769|
770|    Requires admin access.
771|    """
772|    from app.core.models import PatentPublication
773|
774|    row = (await db.execute(
775|        select(
776|            func.count(PatentPublication.id).label("total"),
777|            func.count(PatentPublication.id).filter(
778|                PatentPublication.embedding.isnot(None)
779|            ).label("embedded"),
780|        )
781|    )).one()
782|
783|    total = row.total or 0
784|    embedded = row.embedded or 0
785|    coverage_pct = round(embedded / total * 100, 1) if total > 0 else 0.0
786|
787|    return {
788|        "total_patents": total,
789|        "embedded": embedded,
790|        "missing": total - embedded,
791|        "coverage_pct": coverage_pct,
792|    }
793|
794|
795|# ── Phase 5 PR 1: Email analytics ─────────────────────────────
796|
797|
798|@router.get("/email/analytics")
799|async def admin_email_analytics(
800|    admin: _UserModel = Depends(require_admin),
801|    db=Depends(get_db),
802|):
803|    """Admin-only email analytics — open/click rates + A/B variant breakdown.
804|
805|    Returns aggregate stats for last 7 days and per-subject-variant.
806|    """
807|    from datetime import datetime, timedelta, timezone
808|
809|    from app.core.subscription_models import EmailDelivery
810|
811|    since = datetime.now(timezone.utc) - timedelta(days=7)
812|
813|    # ── Global stats ──────────────────────────────────────────────
814|    sent = (await db.execute(
815|        select(func.count(EmailDelivery.id)).where(
816|            EmailDelivery.email_type == "weekly_briefing",
817|            EmailDelivery.sent_at >= since,
818|        )
819|    )).scalar() or 0
820|
821|    opens = (await db.execute(
822|        select(func.count(EmailDelivery.id)).where(
823|            EmailDelivery.email_type == "weekly_briefing",
824|            EmailDelivery.sent_at >= since,
825|            EmailDelivery.email_opened_at.isnot(None),
826|        )
827|    )).scalar() or 0
828|
829|    clicks = (await db.execute(
830|        select(func.count(EmailDelivery.id)).where(
831|            EmailDelivery.email_type == "weekly_briefing",
832|            EmailDelivery.sent_at >= since,
833|            EmailDelivery.email_clicked_at.isnot(None),
834|        )
835|    )).scalar() or 0
836|
837|    open_rate = round(opens / sent, 3) if sent > 0 else 0.0
838|    click_rate = round(clicks / sent, 3) if sent > 0 else 0.0
839|
840|    # ── Per-variant breakdown ─────────────────────────────────────
841|    variant_rows = (await db.execute(
842|        select(
843|            EmailDelivery.subject_variant,
844|            func.count(EmailDelivery.id).label("total"),
845|            func.count(EmailDelivery.id).filter(
846|                EmailDelivery.email_opened_at.isnot(None)
847|            ).label("opens"),
848|        ).where(
849|            EmailDelivery.email_type == "weekly_briefing",
850|            EmailDelivery.sent_at >= since,
851|            EmailDelivery.subject_variant.isnot(None),
852|        ).group_by(EmailDelivery.subject_variant)
853|    )).all()
854|
855|    by_variant = {}
856|    for row in variant_rows:
857|        v_sent = row.total or 0
858|        v_opens = row.opens or 0
859|        by_variant[str(row.subject_variant)] = {
860|            "sent": v_sent,
861|            "opens": v_opens,
862|            "open_rate": round(v_opens / v_sent, 3) if v_sent > 0 else 0.0,
863|        }
864|
865|    return {
866|        "last_7_days": {
867|            "sent": sent,
868|            "opens": opens,
869|            "open_rate": open_rate,
870|            "clicks": clicks,
871|            "click_rate": click_rate,
872|        },
873|        "by_variant": by_variant,
874|    }
875|

# ── V3.5: Source Health & Ingestion Admin ────────────────────────


class RetryGrantWeekBody(BaseModel):
    issue_date: str  # YYYY-MM-DD


class RetryAppWeekBody(BaseModel):
    publication_date: str  # YYYY-MM-DD


class CatchUpBody(BaseModel):
    start_date: str  # YYYY-MM-DD
    end_date: str | None = None  # YYYY-MM-DD, defaults to today


@router.get("/source-health")
async def admin_source_health(
    admin: _UserModel = Depends(require_admin),
    db=Depends(get_db),
):
    """Aggregated source health — ingestion providers, latest status, source lag."""
    from app.core.models import PatentPublication, SourceFetch

    freshness_row = (await db.execute(
        select(
            func.count(PatentPublication.id).label("total"),
            func.max(PatentPublication.publication_date).label("latest_pub_date"),
            func.max(PatentPublication.created_at).label("latest_ingested_at"),
        )
    )).one()

    providers = ["uspto_bulkdata", "uspto_odp", "bigquery", "wipo_bigquery"]
    provider_rows = []
    for provider in providers:
        latest = (await db.execute(
            select(SourceFetch)
            .where(SourceFetch.provider == provider)
            .order_by(SourceFetch.created_at.desc())
            .limit(1)
        )).scalar_one_or_none()

        latest_success = (await db.execute(
            select(SourceFetch)
            .where(SourceFetch.provider == provider, SourceFetch.status == "success")
            .order_by(SourceFetch.created_at.desc())
            .limit(1)
        )).scalar_one_or_none()

        latest_failure = (await db.execute(
            select(SourceFetch)
            .where(SourceFetch.provider == provider, SourceFetch.status.in_(["failed", "blocked", "unavailable"]))
            .order_by(SourceFetch.created_at.desc())
            .limit(1)
        )).scalar_one_or_none()

        if latest or latest_success or latest_failure:
            provider_rows.append({
                "provider": provider,
                "latest_status": latest.status if latest else "unknown",
                "latest_target_type": latest.target_type if latest else None,
                "latest_target_id": latest.target_id if latest else None,
                "latest_http_status": latest.http_status if latest else None,
                "latest_records_found": latest.records_found if latest else None,
                "latest_error": (latest.error_message[:200] if latest and latest.error_message else None),
                "latest_started_at": latest.started_at.isoformat() if latest and latest.started_at else None,
                "latest_success_at": latest_success.created_at.isoformat() if latest_success and latest_success.created_at else None,
                "latest_failure_at": latest_failure.created_at.isoformat() if latest_failure and latest_failure.created_at else None,
                "latest_source_url": latest.source_url if latest else None,
            })

    source_lag_days = None
    if freshness_row.latest_pub_date:
        source_lag_days = (date.today() - freshness_row.latest_pub_date).days

    return {
        "total_patents": freshness_row.total,
        "latest_publication_date": freshness_row.latest_pub_date.isoformat() if freshness_row.latest_pub_date else None,
        "latest_ingested_at": freshness_row.latest_ingested_at.isoformat() if freshness_row.latest_ingested_at else None,
        "source_lag_days": source_lag_days,
        "providers": provider_rows,
    }


@router.post("/ingestion/retry-grant-week", response_model=TaskStatusResponse)
async def retry_grant_week(
    body: RetryGrantWeekBody,
    admin: _UserModel = Depends(require_admin),
) -> TaskStatusResponse:
    """Retry USPTO grant week ingestion for a specific Tuesday issue date."""
    from app.tasks.ingest_uspto_bulk import ingest_grant_week

    task = ingest_grant_week.delay(body.issue_date)
    return TaskStatusResponse(task_id=task.id, status="PENDING", result=None)


@router.post("/ingestion/retry-application-week", response_model=TaskStatusResponse)
async def retry_application_week(
    body: RetryAppWeekBody,
    admin: _UserModel = Depends(require_admin),
) -> TaskStatusResponse:
    """Retry USPTO application week ingestion for a specific Thursday publication date."""
    from app.tasks.ingest_uspto_bulk import ingest_application_week

    task = ingest_application_week.delay(body.publication_date)
    return TaskStatusResponse(task_id=task.id, status="PENDING", result=None)


@router.post("/ingestion/catch-up", response_model=TaskStatusResponse)
async def catch_up(
    body: CatchUpBody,
    admin: _UserModel = Depends(require_admin),
) -> TaskStatusResponse:
    """Run catch-up ingestion across a date range (grant + application weeks)."""
    from app.tasks.ingest_uspto_bulk import catch_up_weeks

    task = catch_up_weeks.delay(body.start_date, body.end_date)
    return TaskStatusResponse(task_id=task.id, status="PENDING", result=None)
