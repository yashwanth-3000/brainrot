# Draftr Landing Page

This project is a Next.js App Router implementation of the Draftr SaaS landing page.

## Development

```bash
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

## Scripts

- `npm run dev` starts the Next.js development server
- `npm run build` creates the production build
- `npm run start` runs the production server
- `npm run lint` runs ESLint

## Railway

Deploy the website and backend as separate Railway services with their repo roots set to:

- `website`
- `Backend`

Set `BRAINROT_BACKEND_URL` on the website service to the backend service URL. On Railway this should be a reference variable to the backend service domain, for example:

```bash
BRAINROT_BACKEND_URL=https://${{Backend.RAILWAY_PUBLIC_DOMAIN}}
```

The website no longer falls back to `127.0.0.1` in production, so this variable must be set in deployed environments.
