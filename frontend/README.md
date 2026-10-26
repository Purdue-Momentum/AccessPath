# AccessPath frontend

React + Vite + Tailwind CSS v4 + React Router v7. Talks to the Django/DRF backend
over a same-origin dev proxy (cookie/session auth).

## Quick start

```bash
cd frontend
npm install       # first time only
npm run dev       # http://localhost:5173
```

To connect to real data, start the backend too (from `backend/`):

```bash
python manage.py runserver   # http://localhost:8000
```

Then log in with the demo accounts (created by `manage.py seed_demo`):

- `prof@demo.edu` / `demo-password-123`
- `ta@demo.edu` / `demo-password-123`

## How the frontend talks to the backend

The Vite dev server proxies `/api/*` to `http://localhost:8000` (`vite.config.js`),
so every API call is same-origin from the browser's perspective. Session cookies
flow automatically and no CORS config is needed on the backend locally.

Mutating requests (POST/PATCH/DELETE) need Django's CSRF token — read the
`csrftoken` cookie and send it as the `X-CSRFToken` header on unsafe methods.

## Scripts

| Script | What it does |
|---|---|
| `npm run dev` | Start the Vite dev server on :5173 |
| `npm run build` | Build a production bundle into `dist/` |
| `npm run preview` | Serve the production build locally |
| `npm run lint` | Run ESLint |

## Project structure

```
frontend/
├── index.html
├── vite.config.js    # Vite + Tailwind plugin + /api proxy to :8000
├── eslint.config.js
├── package.json
├── public/
│   └── favicon.svg
└── src/
    ├── main.jsx      # entry — mounts React + BrowserRouter
    ├── App.jsx       # top-level Routes
    └── index.css     # Tailwind import + base styles
```

## Tooling

React 19, Vite 8, Tailwind CSS v4 (CSS-first, no config file needed),
React Router v7, ESLint 10 flat config with React Hooks rules. Plain JSX — no TypeScript.
