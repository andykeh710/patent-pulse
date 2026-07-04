# V4.0 — Community Data Model

## Shared Publishable Object Base

Every community-facing object extends a common shape:

```sql
CREATE TABLE intelligence_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    object_type VARCHAR(32) NOT NULL,  -- patent, brief, collection, topic_signal, company_move
    title VARCHAR(512) NOT NULL,
    slug VARCHAR(256) UNIQUE,
    summary TEXT,
    body TEXT,
    owner_user_id VARCHAR(64) NOT NULL REFERENCES users(id),
    visibility VARCHAR(16) NOT NULL DEFAULT 'private',
        -- private, unlisted, organization, public, moderated, removed
    published_at TIMESTAMPTZ,
    canonical_url VARCHAR(1024),
    seo_title VARCHAR(256),
    seo_description VARCHAR(512),
    og_image_url VARCHAR(1024),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX ix_intelligence_items_slug ON intelligence_items(slug) WHERE slug IS NOT NULL;
CREATE INDEX ix_intelligence_items_visibility ON intelligence_items(visibility, published_at)
    WHERE visibility = 'public';
CREATE INDEX ix_intelligence_items_owner ON intelligence_items(owner_user_id, created_at);
```

## Evidence Items (required for public objects)

```sql
CREATE TABLE evidence_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    parent_type VARCHAR(32) NOT NULL,  -- intelligence_item, patent, brief
    parent_id UUID NOT NULL,
    source_type VARCHAR(32) NOT NULL,  -- patent_office, trend_computation, citation_analysis, user_submitted
    source_name VARCHAR(128) NOT NULL,
    source_url VARCHAR(1024),
    patent_id UUID REFERENCES patent_publications(id),
    field_used VARCHAR(64),
    fact TEXT NOT NULL,
    confidence VARCHAR(16) DEFAULT 'medium',
    retrieved_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX ix_evidence_items_parent ON evidence_items(parent_type, parent_id);
```

## Collections

```sql
CREATE TABLE collections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    intelligence_item_id UUID REFERENCES intelligence_items(id) ON DELETE CASCADE,
    name VARCHAR(256) NOT NULL,
    description TEXT,
    owner_user_id VARCHAR(64) NOT NULL REFERENCES users(id),
    visibility VARCHAR(16) NOT NULL DEFAULT 'private',
    tags JSONB DEFAULT '[]',
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE collection_items (
    collection_id UUID NOT NULL REFERENCES collections(id) ON DELETE CASCADE,
    object_type VARCHAR(32) NOT NULL,
    object_id UUID NOT NULL,
    added_by_user_id VARCHAR(64) REFERENCES users(id),
    note TEXT,
    sort_order INTEGER DEFAULT 0,
    added_at TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY (collection_id, object_type, object_id)
);
```

## Features

- Single `intelligence_items` table — no per-type table explosion
- `parent_type + parent_id` evidence reference — works for briefs, patents, collections
- Collections reference any object via `object_type + object_id`
- Visibility enforced at query level: `WHERE visibility = 'public'`
- Slug uniqueness enforced for public objects
- SEO metadata optional — only populated for public objects

## What Does NOT Get Its Own Table

- Topic pages → render from `themes` table + `intelligence_items` where object_type='topic_overview'
- Company pages → render from `patent_publications` aggregations + `intelligence_items`
- Public feed → query `intelligence_items` where visibility='public'
