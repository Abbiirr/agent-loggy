# Frontend Integration Guide: DB Configuration

**Date:** 2025-01-12
**Version:** 1.0

---

## Overview

The backend now supports database-backed configuration for settings, projects, and context rules. This guide explains the changes and how to build admin interfaces to manage these configurations.

---

## What Changed

### Before
- Loki URL, thresholds, output paths were hardcoded
- Project namespaces derived from project code (`project.lower()`)
- Context rules and negate keys loaded from CSV files

### After
- All configuration can be managed via database
- Controlled by feature flags (`USE_DB_SETTINGS`, `USE_DB_PROJECTS`)
- Graceful fallback to defaults when DB unavailable

---

## Database Tables

### 1. `app_settings` - Application Settings

Stores key-value configuration organized by category.

```sql
CREATE TABLE app_settings (
    id SERIAL PRIMARY KEY,
    category VARCHAR(100) NOT NULL,      -- e.g., 'loki', 'thresholds', 'paths'
    setting_key VARCHAR(255) NOT NULL,   -- e.g., 'base_url', 'highly_relevant'
    setting_value TEXT NOT NULL,         -- The value (serialized)
    value_type VARCHAR(50) NOT NULL,     -- 'string', 'int', 'float', 'bool', 'json'
    description TEXT,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    UNIQUE(category, setting_key)
);
```

**Current Settings:**

| Category | Key | Type | Default | Description |
|----------|-----|------|---------|-------------|
| loki | base_url | string | https://loki-gateway... | Loki API endpoint |
| thresholds | highly_relevant | int | 80 | Score for highly relevant (0-100) |
| thresholds | relevant | int | 60 | Score for relevant (0-100) |
| thresholds | potentially_relevant | int | 40 | Score for potentially relevant |
| thresholds | batch_size | int | 10 | Batch size for analysis |
| paths | analysis_output | string | app/comprehensive_analysis | Output directory |
| paths | verification_output | string | app/verification_reports | Verification output |
| negate_rules | terms | json | [...] | Terms to exclude from Loki queries |

### 2. `context_rules` - RAG Context Rules

Defines what patterns are important vs ignorable for different contexts.

```sql
CREATE TABLE context_rules (
    id SERIAL PRIMARY KEY,
    context VARCHAR(100) NOT NULL,    -- e.g., 'mfs', 'bkash', 'transactions'
    important TEXT,                    -- Comma-separated important patterns
    ignore TEXT,                       -- Comma-separated patterns to ignore
    description TEXT,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

### 3. `projects` and `environments` - Project Configuration

Already documented in previous guides. Used for:
- `get_loki_namespace(project, env)` - Returns Loki namespace for project
- `get_log_base_path(project, env)` - Returns file path for file-based projects

---

## API Endpoints (To Be Implemented)

The following endpoints should be created for admin management:

### Settings API

```
GET    /api/admin/settings                    # List all settings
GET    /api/admin/settings/{category}         # List settings by category
GET    /api/admin/settings/{category}/{key}   # Get specific setting
PUT    /api/admin/settings/{category}/{key}   # Update setting
POST   /api/admin/settings                    # Create new setting
DELETE /api/admin/settings/{category}/{key}   # Deactivate setting
```

### Context Rules API

```
GET    /api/admin/context-rules               # List all rules
GET    /api/admin/context-rules/{id}          # Get specific rule
POST   /api/admin/context-rules               # Create new rule
PUT    /api/admin/context-rules/{id}          # Update rule
DELETE /api/admin/context-rules/{id}          # Deactivate rule
```

---

## TypeScript Types

```typescript
// Settings
interface AppSetting {
  id: number;
  category: string;
  setting_key: string;
  setting_value: string;
  typed_value: any;  // Parsed value based on value_type
  value_type: 'string' | 'int' | 'float' | 'bool' | 'json';
  description?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

interface SettingUpdate {
  value: string | number | boolean | any[];
  description?: string;
}

// Context Rules
interface ContextRule {
  id: number;
  context: string;
  important: string;  // Comma-separated
  ignore: string;     // Comma-separated
  description?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

interface ContextRuleCreate {
  context: string;
  important: string;
  ignore: string;
  description?: string;
}

// Negate Rules (stored in app_settings as JSON)
interface NegateRules {
  terms: string[];
}
```

---

## Admin UI Components

### 1. Settings Manager

```tsx
// SettingsManager.tsx
import React, { useState, useEffect } from 'react';

interface SettingsByCategory {
  [category: string]: AppSetting[];
}

export function SettingsManager() {
  const [settings, setSettings] = useState<SettingsByCategory>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchSettings();
  }, []);

  async function fetchSettings() {
    const response = await fetch('/api/admin/settings');
    const data = await response.json();

    // Group by category
    const grouped = data.reduce((acc: SettingsByCategory, setting: AppSetting) => {
      if (!acc[setting.category]) acc[setting.category] = [];
      acc[setting.category].push(setting);
      return acc;
    }, {});

    setSettings(grouped);
    setLoading(false);
  }

  async function updateSetting(category: string, key: string, value: any) {
    await fetch(`/api/admin/settings/${category}/${key}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ value }),
    });
    fetchSettings();
  }

  return (
    <div className="settings-manager">
      {Object.entries(settings).map(([category, items]) => (
        <SettingCategory
          key={category}
          category={category}
          settings={items}
          onUpdate={updateSetting}
        />
      ))}
    </div>
  );
}

function SettingCategory({ category, settings, onUpdate }) {
  return (
    <div className="setting-category">
      <h3>{category}</h3>
      <table>
        <thead>
          <tr>
            <th>Key</th>
            <th>Value</th>
            <th>Type</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {settings.map(setting => (
            <SettingRow
              key={setting.setting_key}
              setting={setting}
              onUpdate={(value) => onUpdate(category, setting.setting_key, value)}
            />
          ))}
        </tbody>
      </table>
    </div>
  );
}
```

### 2. Context Rules Editor

```tsx
// ContextRulesEditor.tsx
export function ContextRulesEditor() {
  const [rules, setRules] = useState<ContextRule[]>([]);

  async function fetchRules() {
    const response = await fetch('/api/admin/context-rules');
    setRules(await response.json());
  }

  async function saveRule(rule: ContextRuleCreate) {
    await fetch('/api/admin/context-rules', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(rule),
    });
    fetchRules();
  }

  return (
    <div className="context-rules-editor">
      <h2>Context Rules</h2>
      <p>Define what patterns are important vs. ignorable for each context.</p>

      <table>
        <thead>
          <tr>
            <th>Context</th>
            <th>Important Patterns</th>
            <th>Ignore Patterns</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {rules.map(rule => (
            <tr key={rule.id}>
              <td>{rule.context}</td>
              <td>
                <TagList tags={rule.important.split(',')} />
              </td>
              <td>
                <TagList tags={rule.ignore.split(',')} />
              </td>
              <td>
                <button onClick={() => editRule(rule)}>Edit</button>
                <button onClick={() => deleteRule(rule.id)}>Delete</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <button onClick={() => openNewRuleModal()}>Add Rule</button>
    </div>
  );
}
```

### 3. Negate Terms Manager

```tsx
// NegateTermsManager.tsx
export function NegateTermsManager() {
  const [terms, setTerms] = useState<string[]>([]);
  const [newTerm, setNewTerm] = useState('');

  useEffect(() => {
    fetchTerms();
  }, []);

  async function fetchTerms() {
    const response = await fetch('/api/admin/settings/negate_rules/terms');
    const data = await response.json();
    setTerms(data.typed_value || []);
  }

  async function saveTerms(updatedTerms: string[]) {
    await fetch('/api/admin/settings/negate_rules/terms', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ value: updatedTerms }),
    });
    setTerms(updatedTerms);
  }

  function addTerm() {
    if (newTerm && !terms.includes(newTerm)) {
      saveTerms([...terms, newTerm]);
      setNewTerm('');
    }
  }

  function removeTerm(term: string) {
    saveTerms(terms.filter(t => t !== term));
  }

  return (
    <div className="negate-terms-manager">
      <h2>Negate Terms</h2>
      <p>Terms excluded from Loki log queries (noise filtering).</p>

      <div className="terms-list">
        {terms.map(term => (
          <div key={term} className="term-tag">
            {term}
            <button onClick={() => removeTerm(term)}>×</button>
          </div>
        ))}
      </div>

      <div className="add-term">
        <input
          value={newTerm}
          onChange={(e) => setNewTerm(e.target.value)}
          placeholder="New term to exclude..."
        />
        <button onClick={addTerm}>Add</button>
      </div>
    </div>
  );
}
```

---

## Threshold Configuration UI

```tsx
// ThresholdConfigurator.tsx
export function ThresholdConfigurator() {
  const [thresholds, setThresholds] = useState({
    highly_relevant: 80,
    relevant: 60,
    potentially_relevant: 40,
  });

  return (
    <div className="threshold-configurator">
      <h2>Relevance Thresholds</h2>

      <div className="threshold-visual">
        {/* Visual representation of thresholds */}
        <div className="threshold-bar">
          <div
            className="zone highly-relevant"
            style={{ left: `${thresholds.highly_relevant}%` }}
          >
            Highly Relevant ({thresholds.highly_relevant}+)
          </div>
          <div
            className="zone relevant"
            style={{
              left: `${thresholds.relevant}%`,
              width: `${thresholds.highly_relevant - thresholds.relevant}%`
            }}
          >
            Relevant ({thresholds.relevant}-{thresholds.highly_relevant})
          </div>
          <div
            className="zone potentially-relevant"
            style={{
              left: `${thresholds.potentially_relevant}%`,
              width: `${thresholds.relevant - thresholds.potentially_relevant}%`
            }}
          >
            Potentially ({thresholds.potentially_relevant}-{thresholds.relevant})
          </div>
          <div
            className="zone not-relevant"
            style={{ width: `${thresholds.potentially_relevant}%` }}
          >
            Not Relevant (0-{thresholds.potentially_relevant})
          </div>
        </div>
      </div>

      <div className="threshold-inputs">
        <label>
          Highly Relevant Threshold:
          <input
            type="range"
            min="0"
            max="100"
            value={thresholds.highly_relevant}
            onChange={(e) => updateThreshold('highly_relevant', e.target.value)}
          />
          <span>{thresholds.highly_relevant}</span>
        </label>
        {/* Similar for other thresholds */}
      </div>
    </div>
  );
}
```

---

## Feature Flags

The frontend should check feature flags to show/hide admin UI:

```typescript
interface FeatureFlags {
  USE_DB_SETTINGS: boolean;
  USE_DB_PROJECTS: boolean;
  USE_DB_PROMPTS: boolean;
  USE_PERSISTENT_CONVERSATIONS: boolean;
}

// Check if settings management should be shown
async function getFeatureFlags(): Promise<FeatureFlags> {
  const response = await fetch('/api/config/features');
  return response.json();
}
```

---

## Cache Considerations

Settings are cached on the backend. After making changes:

1. **Automatic:** Cache expires after TTL (default 5 minutes)
2. **Manual:** Call cache invalidation endpoint (to be implemented)

```typescript
async function invalidateSettingsCache(category?: string) {
  await fetch('/api/admin/settings/cache/invalidate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ category }),
  });
}
```

---

## Error Handling

```typescript
async function updateSetting(category: string, key: string, value: any) {
  try {
    const response = await fetch(`/api/admin/settings/${category}/${key}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ value }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to update setting');
    }

    // Show success notification
    showNotification('Setting updated successfully');

  } catch (error) {
    // Show error notification
    showNotification(`Error: ${error.message}`, 'error');
  }
}
```

---

## Summary

| Component | Database Table | Feature Flag |
|-----------|---------------|--------------|
| App Settings | `app_settings` | `USE_DB_SETTINGS` |
| Context Rules | `context_rules` | `USE_DB_SETTINGS` |
| Negate Rules | `app_settings` (JSON) | `USE_DB_SETTINGS` |
| Projects | `projects` | `USE_DB_PROJECTS` |
| Environments | `environments` | `USE_DB_PROJECTS` |

Admin APIs need to be implemented. The frontend should provide:
1. Settings manager grouped by category
2. Context rules editor with tag-based input
3. Negate terms manager
4. Visual threshold configurator
5. Cache invalidation controls
