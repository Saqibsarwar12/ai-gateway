# AI Gateway — Render Deployment
# Native Python runtime (no Docker)

## Setup

### 1. Push to GitHub
```bash
cd ai-gateway
git init
git add .
git commit -m "Initial commit: AI Gateway Platform"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/ai-gateway.git
git push -u origin main
```

### 2. Deploy on Render
1. Go to https://dashboard.render.com/blueprint
2. Click "New Blueprint Instance"
3. Connect your GitHub repo
4. Render auto-detects `render.yaml` — click "Apply"
5. Add your secrets:
   - `ADMIN_EMAIL` = your@email.com
   - `ADMIN_PASSWORD` = your-secure-password
6. Click "Create Blueprint"

### 3. Done!
- API URL: `https://ai-gateway.onrender.com`
- Docs: `https://ai-gateway.onrender.com/docs`
- Admin: `https://ai-gateway.onrender.com/docs` → Auth → then use `/admin/*` endpoints

## API Endpoints

### OpenAI-Compatible
- `POST /v1/chat/completions` — Chat completions
- `POST /v1/completions` — Text completions
- `GET /v1/models` — List available models

### Admin
- `POST /admin/auth/login` — Login (email + password)
- `GET /admin/providers` — List providers
- `POST /admin/providers` — Add provider
- `PUT /admin/providers/{id}` — Update provider
- `DELETE /admin/providers/{id}` — Delete provider
- `POST /admin/providers/{id}/test` — Test provider connection
- `GET /admin/routing` — List routing rules
- `POST /admin/routing` — Create routing rule
- `GET /admin/users` — List users
- `POST /admin/users` — Create user
- `GET /admin/analytics` — Get analytics
- `GET /admin/logs` — Get request logs

## Example: Add a Provider
```bash
curl -X POST https://ai-gateway.onrender.com/admin/providers \
  -H "Content-Type: application/json" \
  -d '{
    "name": "OpenAI",
    "slug": "openai",
    "base_url": "https://api.openai.com/v1",
    "api_key": "sk-your-key",
    "cost_per_1k_input": 2.5,
    "cost_per_1k_output": 10,
    "models": ["gpt-4o", "gpt-4o-mini"]
  }'
```

## Example: Chat Completion
```bash
curl -X POST https://ai-gateway.onrender.com/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{
    "model": "gpt-4o",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```
