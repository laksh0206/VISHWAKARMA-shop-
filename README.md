# Vishwakarma Hardware & Sanitary

A lightweight Node/Express storefront with a hidden, PIN-protected inventory portal.

## Run locally

```bash
npm install
npm start
```

Open `http://localhost:3000`. The management portal is intentionally not linked from the public site: visit `http://localhost:3000/admin` and sign in with `0206` (or the `ADMIN_PIN` environment variable).

## Deploy on Render

1. Push this folder to a GitHub repository.
2. In Render, choose **New +** → **Blueprint** and select the repository. Render will read `render.yaml`.
3. The default admin PIN is `0206`; you can replace `ADMIN_PIN` in Render's environment settings later if needed, then deploy.
4. The Blueprint attaches a 1 GB persistent disk, so catalogue updates made through `/admin` survive deploys and restarts. This requires a Render paid web-service plan; the configured `starter` plan supports it.

`JWT_SECRET` is generated automatically by Render. For local development it uses a safe-to-replace fallback value.

## Inventory fields

The portal supports a product name, category, description, price, availability, and an optional public image URL. The catalogue intentionally starts empty so only your own products appear.
