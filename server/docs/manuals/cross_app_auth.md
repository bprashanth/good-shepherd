# Cross-App Authentication Architecture

Read [docs/manuals/client_integration.md](docs/manuals/client_integration.md) for instructions on integrating one specific client. This doc is about allowing multiple apps/clients to authenticate and share data through s3 storage buckets. 

## Ecosystem Overview

All apps share a single Cognito User Pool. Users are admin-created via the
fomomon admin UI — no self-signup, no temp passwords.

```
┌─────────────────────────────────────────────────────────────────┐
│                        ADMIN (user management)                  │
│  fomomon admin UI (localhost:8090)                              │
│  admin_create_user + admin_set_user_password(Permanent=True)    │
│  → Cognito User Pool (ap-south-1_28HVATwK2)                    │
└────────────────────────────┬────────────────────────────────────┘
                             │ users added here
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│              COGNITO USER POOL (shared, single)                 │
│  Pool: ap-south-1_28HVATwK2                                    │
│  Client: 1j0f2k3top2af4m8da7nbmeu63                            │
│  Identity Pool: ap-south-1:33c1f27d-fe67-4109-a08d-06aaa893d649│
│  Config: s3://fomomon/auth_config.json                          │
│                                                                 │
│  All apps fetch auth_config.json from S3 at startup             │
│  All apps use the same pool/client for login                    │
│  USER_PASSWORD_AUTH flow (admin sets permanent passwords)        │
└──────┬──────────────┬──────────────┬────────────────────────────┘
       │              │              │
       ▼              ▼              ▼
┌──────────┐  ┌──────────────┐  ┌────────────────┐
│ fomomon  │  │ fomo web     │  │ scribe (PWA)   │
│ Flutter  │  │ Vue 3 app    │  │ Vue 3 PWA      │
│ mobile   │  │ dashboard    │  │ form capture   │
│          │  │              │  │                │
│ Dart SDK │  │ JS SDK       │  │ JS SDK         │
│ cognito  │  │ cognito      │  │ cognito        │
│ identity │  │ identity     │  │ identity       │
└────┬─────┘  └──────┬───────┘  └───────┬────────┘
     │               │                  │
     │  JWT token    │  JWT token       │ JWT token
     ▼               ▼                  ▼
┌─────────────────────────────────────────────────────────────────┐
│              S3 BUCKET (fomomon, IAM-protected)                 │
│  Photos, configs, sites.json, users.json, auth_config.json      │
│  Access via: presigned URLs (Flutter) or Lambda endpoint (web)  │
└─────────────────────────────────────────────────────────────────┘
     ▲                                  ▲
     │  presigned URLs                  │  Bearer JWT
     │  (Identity Pool                  │
     │   temp credentials)              │
┌────┴─────────────────┐  ┌────────────┴──────────────────────────┐
│ fomomon Flutter app  │  │  SERVERLESS BACKEND (Lambda)          │
│ uses CognitoIdentity │  │  FastAPI behind API Gateway           │
│ → temp AWS creds     │  │  JWT authorizer validates Cognito     │
│ → presigned S3 URLs  │  │  tokens at gateway level              │
│                      │  │                                       │
│                      │  │  Endpoints:                           │
│                      │  │  POST /api/upload (Textract → xlsx)   │
│                      │  │  POST /api/presign (future: S3 URLs)  │
│                      │  │  GET  /api/health (no auth)           │
└──────────────────────┘  └───────────────────────────────────────┘
```

## Cognito Pool

- **Pool ID**: `ap-south-1_28HVATwK2`
- **Client ID**: `1j0f2k3top2af4m8da7nbmeu63`
- **Identity Pool**: `ap-south-1:33c1f27d-fe67-4109-a08d-06aaa893d649`
- **Config URL**: `https://fomomon.s3.ap-south-1.amazonaws.com/auth_config.json`

All apps fetch `auth_config.json` at startup to get pool/client IDs. This
avoids hardcoding and allows config changes without redeployment.

Admin creates users via:
```bash
aws cognito-idp admin-create-user --user-pool-id ap-south-1_28HVATwK2 \
  --username user@example.com --temporary-password Pass123 \
  --message-action SUPPRESS --user-attributes Name=email,Value=user@example.com
aws cognito-idp admin-set-user-password --user-pool-id ap-south-1_28HVATwK2 \
  --username user@example.com --password Pass123 --permanent
```

This sets a permanent password immediately — no temp password email, no
`NEW_PASSWORD_REQUIRED` challenge.

## Login Flow Per App

### Flutter (fomomon mobile)

Uses Dart `amazon_cognito_identity_dart_2` package:
1. Fetch `auth_config.json` from S3
2. Create `CognitoUserPool` with pool/client IDs
3. `authenticateUser()` with `AuthenticationDetails(username, password)`
4. Get ID token → exchange for Identity Pool temp credentials
5. Use temp credentials for presigned S3 URLs

### Vue 3 (scribe PWA, fomo web)

Uses `amazon-cognito-identity-js` npm package:
1. Fetch `auth_config.json` from S3
2. Create `CognitoUserPool` with pool/client IDs
3. `authenticateUser()` with `AuthenticationDetails`
4. Get ID token → use as Bearer token for API Gateway calls

The `useCognitoAuth` composable pattern is reusable across any Vue 3 app.

## Adding Cognito Auth to a New Vue 3 App

1. Install the SDK:
   ```bash
   npm install amazon-cognito-identity-js
   ```

2. Create a `useCognitoAuth.js` composable that:
   - Fetches `auth_config.json` from S3 at init
   - Exposes `login(username, password)`, `logout()`, `refreshSession()`
   - Stores tokens in `localStorage` (the SDK does this automatically)
   - See `docs/manuals/client_integration.md` for the full auth pattern

3. Create a `LoginView.vue` with email + password fields that calls `login()`

4. Add router guard in `router.js`:
   ```js
   router.beforeEach(async (to) => {
     if (to.name === 'login') return
     const { isAuthenticated, refreshSession } = useCognitoAuth()
     if (!isAuthenticated.value) {
       await refreshSession()
       if (!isAuthenticated.value) return { name: 'login' }
     }
   })
   ```

5. Create an `apiFetch()` wrapper that attaches `Authorization: Bearer <token>`
   and retries on 401 after refreshing the session

6. Set `VITE_API_BASE_URL` in `.env.production` to point to your API Gateway

## Calling the Lambda Backend

In development, Vite's proxy forwards `/api/*` to `localhost:8070`. In
production, `VITE_API_BASE_URL` points to the API Gateway URL.

The `useApi.js` composable:
- Prepends `VITE_API_BASE_URL` to paths
- Attaches `Authorization: Bearer <idToken>` header
- On 401: refreshes the session and retries once

## S3 Access Patterns

### Flutter (presigned URLs)

Flutter uses the Identity Pool to get temporary AWS credentials, then generates
presigned S3 URLs client-side. This avoids routing large files through a Lambda.

### Web apps (Lambda proxy)

Web apps call Lambda endpoints (e.g., `/api/presign`) with a JWT token. The
Lambda generates presigned URLs server-side using its execution role.

## Example: fomo Web App

Currently uses Google OAuth whitelist. Migration path to add Cognito:
1. Install `amazon-cognito-identity-js`
2. Add `useCognitoAuth.js` composable
3. Add login view + router guard
4. Replace Google Auth check with Cognito `isAuthenticated`
5. Use `useApi.js` for backend calls
