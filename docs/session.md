# Session Management Plan

## Current Problems
- In-memory `active_sessions` dict loses all data on restart
- No session expiry or cleanup
- No conversation continuity between requests
- Session data not linked to analysis results

## Implementation Plan

### Phase 1: Database Schema
- Add `sessions` table with id, conversation_id, status, timestamps
- Add indexes for performance
- Link sessions to conversations table

### Phase 2: Replace In-Memory Storage
- Create SessionService class
- Remove `active_sessions` dict from main.py
- Use PostgreSQL for persistence
- Add Redis for caching active sessions

### Phase 3: Session Lifecycle
- Auto-expire after 30 minutes idle
- Touch session on each request
- Background cleanup task every 5 minutes
- Graceful recovery for expired sessions

### Phase 4: API Updates
- Modify `/api/chat` to create persistent sessions
- Update stream endpoint to validate sessions
- Add session recovery middleware
- Return proper error codes for expired sessions

### Phase 5: Testing & Monitoring
- Test persistence across restarts
- Load test concurrent sessions
- Monitor Redis memory usage
- Add session metrics

## Configuration Required
- Redis instance for caching
- Session timeout settings
- Max concurrent sessions limit
- Cleanup interval

## Migration Steps
1. Deploy Redis
2. Run database migrations
3. Update main.py endpoints
4. Remove in-memory dict
5. Test session persistence

## Dependencies
- redis (asyncio client)
- Background task scheduler
- Session recovery middleware