# shared/

Shared types, constants, and utilities used across frontend and backend.

## Responsibility
Code that is genuinely shared between multiple services — TypeScript types that mirror backend schemas, shared constants, utility functions that don't belong to any single service.

## Structure

```
shared/
├── types/           ← shared TypeScript interfaces (mirrors backend Pydantic schemas)
├── constants/       ← shared constants (asset types, currencies, etc.)
└── utils/           ← pure utility functions with no service dependency
```

## Rule
Nothing in this folder should import from `frontend/`, `backend/`, or `ai-services/`. It has no dependencies on other layers — only they depend on it.
