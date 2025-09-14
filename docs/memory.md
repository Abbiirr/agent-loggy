# Memory Implementation Guide for Log Analysis Chatbot

## Architecture Overview

Three-tier memory system optimized for log analysis patterns:
- **Conversation Memory**: Recent messages (in-session)
- **Analysis Memory**: Historical patterns and resolutions
- **Reference Memory**: Known error patterns and solutions

## Database Schema

```sql
-- Enable JSONB indexing
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Conversation memory
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'
);

CREATE TABLE messages (
    id SERIAL PRIMARY KEY,
    conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL, -- 'user', 'assistant', 'system'
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    metadata JSONB DEFAULT '{}' -- stores parameters, trace_ids, etc.
);

-- Analysis memory
CREATE TABLE analysis_memory (
    id SERIAL PRIMARY KEY,
    conversation_id UUID REFERENCES conversations(id),
    query_text TEXT NOT NULL,
    parameters JSONB NOT NULL,
    trace_ids TEXT[],
    findings JSONB,
    error_pattern VARCHAR(100),
    resolution TEXT,
    confidence_score FLOAT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Pattern memory for quick lookups
CREATE TABLE error_patterns (
    id SERIAL PRIMARY KEY,
    pattern_key VARCHAR(200) UNIQUE NOT NULL,
    domain VARCHAR(50),
    error_type VARCHAR(100),
    typical_causes TEXT[],
    resolution_steps JSONB,
    success_rate FLOAT DEFAULT 0,
    usage_count INT DEFAULT 0,
    last_seen TIMESTAMP DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_messages_conversation ON messages(conversation_id);
CREATE INDEX idx_analysis_params ON analysis_memory USING GIN(parameters);
CREATE INDEX idx_analysis_error ON analysis_memory(error_pattern);
CREATE INDEX idx_analysis_created ON analysis_memory(created_at DESC);
CREATE INDEX idx_patterns_domain ON error_patterns(domain, error_type);
```

## Core Memory Service

```python
# app/services/memory_service.py
from typing import List, Dict, Optional
import asyncpg
import json
from datetime import datetime, timedelta

class MemoryService:
    def __init__(self, db_pool: asyncpg.Pool):
        self.db = db_pool
        
    async def store_conversation_message(
        self, 
        conversation_id: str, 
        role: str, 
        content: str, 
        metadata: Dict = None
    ):
        """Store message with analysis metadata"""
        await self.db.execute("""
            INSERT INTO messages (conversation_id, role, content, metadata)
            VALUES ($1, $2, $3, $4)
        """, conversation_id, role, content, json.dumps(metadata or {}))
    
    async def get_conversation_context(
        self, 
        conversation_id: str, 
        limit: int = 10
    ) -> List[Dict]:
        """Get recent messages for context"""
        rows = await self.db.fetch("""
            SELECT role, content, metadata, created_at
            FROM messages
            WHERE conversation_id = $1
            ORDER BY created_at DESC
            LIMIT $2
        """, conversation_id, limit)
        
        return [dict(r) for r in reversed(rows)]
    
    async def store_analysis_result(
        self,
        conversation_id: str,
        query: str,
        params: Dict,
        trace_ids: List[str],
        findings: Dict,
        error_pattern: str = None
    ):
        """Store analysis for pattern learning"""
        await self.db.execute("""
            INSERT INTO analysis_memory 
            (conversation_id, query_text, parameters, trace_ids, findings, error_pattern)
            VALUES ($1, $2, $3, $4, $5, $6)
        """, conversation_id, query, json.dumps(params), 
            trace_ids, json.dumps(findings), error_pattern)
        
        # Update pattern statistics
        if error_pattern:
            await self._update_pattern_stats(params.get('domain'), error_pattern)
    
    async def find_similar_analyses(
        self,
        params: Dict,
        limit: int = 5
    ) -> List[Dict]:
        """Find similar past analyses by parameters"""
        rows = await self.db.fetch("""
            SELECT 
                query_text,
                parameters,
                trace_ids,
                findings,
                error_pattern,
                resolution,
                confidence_score,
                created_at
            FROM analysis_memory
            WHERE parameters @> $1
            ORDER BY created_at DESC
            LIMIT $2
        """, json.dumps({'domain': params.get('domain')}), limit)
        
        return [dict(r) for r in rows]
    
    async def get_error_pattern_info(
        self,
        domain: str,
        error_type: str
    ) -> Optional[Dict]:
        """Get known resolution for error pattern"""
        row = await self.db.fetchrow("""
            SELECT * FROM error_patterns
            WHERE domain = $1 AND error_type = $2
        """, domain, error_type)
        
        if row:
            await self.db.execute("""
                UPDATE error_patterns 
                SET usage_count = usage_count + 1, last_seen = NOW()
                WHERE id = $1
            """, row['id'])
            
        return dict(row) if row else None
    
    async def _update_pattern_stats(self, domain: str, error_pattern: str):
        """Update or create error pattern statistics"""
        await self.db.execute("""
            INSERT INTO error_patterns (pattern_key, domain, error_type, usage_count)
            VALUES ($1, $2, $3, 1)
            ON CONFLICT (pattern_key) 
            DO UPDATE SET 
                usage_count = error_patterns.usage_count + 1,
                last_seen = NOW()
        """, f"{domain}:{error_pattern}", domain, error_pattern)
```

## Enhanced Orchestrator

```python
# app/orchestrator_v2.py
from app.orchestrator import Orchestrator
from app.services.memory_service import MemoryService

class MemoryAwareOrchestrator(Orchestrator):
    def __init__(self, client, model, memory_service: MemoryService):
        super().__init__(client, model)
        self.memory = memory_service
        
    async def analyze_stream(
        self, 
        text: str, 
        project: str, 
        env: str, 
        domain: str,
        conversation_id: str = None
    ):
        # Store user query
        if conversation_id:
            await self.memory.store_conversation_message(
                conversation_id, "user", text, 
                {"project": project, "env": env, "domain": domain}
            )
        
        # Extract parameters (remove hardcoded values!)
        params = self.param_agent.run(text)
        
        # Check for similar past issues
        similar = await self.memory.find_similar_analyses(params)
        if similar:
            yield "Found Similar Issues", {
                "count": len(similar),
                "most_recent": similar[0]['created_at'].isoformat() if similar else None,
                "common_traces": similar[0].get('trace_ids', [])[:3] if similar else []
            }
            
            # Check for known error patterns
            if similar[0].get('error_pattern'):
                pattern_info = await self.memory.get_error_pattern_info(
                    domain, similar[0]['error_pattern']
                )
                if pattern_info:
                    yield "Known Error Pattern", {
                        "pattern": pattern_info['error_type'],
                        "typical_causes": pattern_info.get('typical_causes', []),
                        "success_rate": pattern_info.get('success_rate', 0)
                    }
        
        # Continue with normal analysis flow
        async for step, payload in super().analyze_stream(text, project, env, domain):
            yield step, payload
            
            # Store analysis results at the end
            if step == "Verification Results" and conversation_id:
                await self.memory.store_analysis_result(
                    conversation_id,
                    text,
                    params,
                    payload.get('trace_ids', []),
                    payload.get('findings', {}),
                    payload.get('error_pattern')
                )
                
                # Store assistant response
                await self.memory.store_conversation_message(
                    conversation_id, "assistant", 
                    json.dumps(payload), 
                    {"step": "final_analysis"}
                )
```

## Context Builder

```python
# app/services/context_builder.py
class ContextBuilder:
    def __init__(self, memory_service: MemoryService):
        self.memory = memory_service
        
    async def build_prompt_with_context(
        self,
        conversation_id: str,
        new_message: str,
        include_patterns: bool = True
    ) -> str:
        """Build prompt including conversation history and patterns"""
        
        # Get conversation context
        context = await self.memory.get_conversation_context(conversation_id)
        
        prompt_parts = []
        
        # Add conversation history
        if context:
            prompt_parts.append("Previous conversation:")
            for msg in context[-5:]:  # Last 5 messages
                role = msg['role'].upper()
                content = msg['content'][:200]  # Truncate long messages
                prompt_parts.append(f"{role}: {content}")
            prompt_parts.append("")
        
        # Add relevant analysis patterns if found
        metadata = context[-1]['metadata'] if context else {}
        if include_patterns and metadata.get('parameters'):
            similar = await self.memory.find_similar_analyses(
                metadata['parameters'], 
                limit=2
            )
            if similar:
                prompt_parts.append("Similar past analyses found:")
                for analysis in similar:
                    prompt_parts.append(
                        f"- Query: {analysis['query_text'][:100]}"
                        f"\n  Traces: {', '.join(analysis['trace_ids'][:3])}"
                        f"\n  Pattern: {analysis.get('error_pattern', 'Unknown')}"
                    )
                prompt_parts.append("")
        
        # Add current message
        prompt_parts.append(f"Current query: {new_message}")
        
        return "\n".join(prompt_parts)
```

## API Integration

```python
# main.py additions
from app.services.memory_service import MemoryService
from app.orchestrator_v2 import MemoryAwareOrchestrator

# Initialize memory service
db_pool = await asyncpg.create_pool(settings.DATABASE_URL)
memory_service = MemoryService(db_pool)
orchestrator = MemoryAwareOrchestrator(client, model, memory_service)

@app.post("/api/conversations")
async def create_conversation():
    """Create new conversation with memory"""
    async with db_pool.acquire() as conn:
        conversation_id = await conn.fetchval(
            "INSERT INTO conversations DEFAULT VALUES RETURNING id"
        )
    return {"conversation_id": str(conversation_id)}

@app.get("/api/conversations/{conversation_id}/similar")
async def get_similar_issues(conversation_id: str):
    """Get similar past issues"""
    # Get last message metadata
    context = await memory_service.get_conversation_context(conversation_id, 1)
    if not context:
        return {"similar": []}
    
    params = context[0].get('metadata', {}).get('parameters', {})
    similar = await memory_service.find_similar_analyses(params)
    
    return {"similar": similar}
```

## Migration Steps

1. **Run migrations**: `alembic upgrade head`
2. **Remove hardcoded params** in orchestrator.py lines 89-95
3. **Replace in-memory sessions** with database in main.py
4. **Add memory service** initialization
5. **Test pattern matching** with similar queries

## Performance Optimization

```python
# app/services/memory_cache.py
import redis.asyncio as redis
from typing import Optional

class MemoryCache:
    def __init__(self, redis_url: str):
        self.redis = redis.from_url(redis_url)
        
    async def get_cached_analysis(self, params_hash: str) -> Optional[Dict]:
        """Check cache for recent identical analysis"""
        data = await self.redis.get(f"analysis:{params_hash}")
        return json.loads(data) if data else None
        
    async def cache_analysis(self, params_hash: str, result: Dict, ttl: int = 3600):
        """Cache analysis result for 1 hour"""
        await self.redis.setex(
            f"analysis:{params_hash}", 
            ttl, 
            json.dumps(result)
        )
```

## Testing

```python
# tests/test_memory.py
async def test_pattern_recognition():
    # Store analysis
    await memory.store_analysis_result(
        "conv1", "NPSB failed", 
        {"domain": "transactions"}, 
        ["trace123"], 
        {"error": "timeout"}, 
        "TIMEOUT_ERROR"
    )
    
    # Find similar
    similar = await memory.find_similar_analyses({"domain": "transactions"})
    assert len(similar) > 0
    assert similar[0]['error_pattern'] == "TIMEOUT_ERROR"
```