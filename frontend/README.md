# frontend/

React + TypeScript + Tailwind CSS application.

## Responsibility
All user-facing UI lives here. This layer talks exclusively to the backend REST APIs — never directly to AI services or the database.

## Stack
- **React 18** – component framework
- **TypeScript** – type safety
- **Tailwind CSS** – utility-first styling
- **React Router** – client-side routing
- **shadcn/ui** – component primitives

## Structure

```
frontend/
├── components/
│   ├── ui/          ← reusable primitives (Button, Card, Table, etc.)
│   └── layout/      ← Shell, Sidebar, TopNav
├── pages/           ← route-level page components
├── hooks/           ← custom React hooks
├── services/        ← API client functions
├── layouts/         ← page layout wrappers
├── types/           ← TypeScript interfaces and types
├── utils/           ← helper functions
├── styles/          ← global CSS, theme tokens
└── assets/          ← images, icons, fonts
```

## Getting Started

```bash
# From repo root
docker compose up frontend
```

Runs at: http://localhost:3000
