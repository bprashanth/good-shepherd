# Client Integration Guide

How to authenticate with and call the form-idable server API from any client
(web app, Flutter, CLI scripts, etc.).

## Base URL

| Environment | URL |
|---|---|
| Local dev | `http://localhost:8070` |
| Production | `https://{APIGW_ID}.execute-api.ap-south-1.amazonaws.com/prod` |

The production URL is written to `server/deploy/outputs.env` after running
`setup.sh`. You can also find `APIGW_ID` via the AWS console.

## Authentication

All endpoints except `/api/health` require a Cognito JWT token.

### 1. Get Cognito config

All apps use the same shared Cognito User Pool. The pool/client IDs are
published at a public S3 URL:

```
GET https://fomomon.s3.ap-south-1.amazonaws.com/auth_config.json
```

Response:
```json
{
  "userPoolId": "ap-south-1_XXXXXXXXX",
  "clientId": "abcdef123456"
}
```

Fetch this at app startup. The URL is overridable via `AUTH_CONFIG_URL` env var.

### 2. Authenticate the user

Users are created by an admin (`server/deploy/add-user.sh` or the fomomon
admin UI). There is no self-signup.

**Web/mobile apps** — use `USER_SRP_AUTH` via the Cognito SDK:
```javascript
import { CognitoUserPool, CognitoUser, AuthenticationDetails } from 'amazon-cognito-identity-js'

const pool = new CognitoUserPool({ UserPoolId: config.userPoolId, ClientId: config.clientId })
const user = new CognitoUser({ Username: email, Pool: pool })
user.authenticateUser(new AuthenticationDetails({ Username: email, Password: password }), {
  onSuccess(session) {
    const token = session.getIdToken().getJwtToken()
    // Use this token in API calls
  },
})
```

**CLI/scripts** — use `USER_PASSWORD_AUTH` via the AWS CLI:
```bash
TOKEN=$(aws cognito-idp initiate-auth \
  --client-id "$CLIENT_ID" \
  --auth-flow USER_PASSWORD_AUTH \
  --auth-parameters "USERNAME=${EMAIL},PASSWORD=${PASSWORD}" \
  --region ap-south-1 \
  --query 'AuthenticationResult.IdToken' --output text)
```

### 3. Send the token

Pass the ID token in the `Authorization` header on every API request:

```
Authorization: Bearer eyJraWQiOi...
```

Auth is enforced at the API Gateway level (JWT authorizer). The FastAPI server
itself has no auth middleware — locally, endpoints work without a token.

### 4. Handle token expiry

Cognito returns three tokens on login:

| Token | Lifetime | Purpose |
|---|---|---|
| **ID token** | 1 hour | The JWT sent as `Authorization: Bearer`. This is what API Gateway validates. |
| **Access token** | 1 hour | For Cognito user-management APIs (not used by this server). |
| **Refresh token** | 30 days | Used to silently get new ID/access tokens without re-entering a password. |

The Cognito SDK (`amazon-cognito-identity-js`) stores all three in
**localStorage** automatically. The user only has to re-enter their password
when the refresh token expires (30 days), or if an admin revokes/disables the
user.

Your client needs to handle two scenarios:

**Scenario A — User returns after closing the tab (stale ID token):**

On app startup / page load, try to restore the session before routing:

```
on_app_load:
    user = pool.getCurrentUser()          # reads from localStorage
    if not user:
        redirect to /login
        return
    session = user.getSession()           # SDK auto-refreshes if ID token
                                          # expired but refresh token valid
    if session.isValid():
        id_token = session.getIdToken()   # fresh token, good for 1 hour
    else:
        redirect to /login                # refresh token also expired (30d)
```

**Scenario B — User stays on page past the 1-hour ID token expiry:**

Wrap all API calls with a 401-retry layer:

```
api_fetch(url, options):
    response = fetch(url, headers: { Authorization: "Bearer " + id_token })
    if response.status == 401:
        session = user.getSession()       # SDK uses refresh token
        if session.isValid():
            id_token = session.getIdToken()
            response = fetch(url, headers: { Authorization: "Bearer " + id_token })
        else:
            redirect to /login
    return response
```

The key insight: `getSession()` is not just a local check — if the ID token
has expired, the SDK automatically uses the refresh token to call Cognito and
get a fresh ID token. This is invisible to the user.

**When does the user actually see a login screen?**
- Refresh token expired (30 days by default)
- Admin disabled or deleted the user
- Admin changed the user's password
- User explicitly logged out (clears localStorage)

The refresh token lifetime is configurable (up to 10 years) on the Cognito
app client.

The scribe PWA (`useCognitoAuth.js` and `useApi.js` composables) implements
both patterns. Use them as a reference for any new Vue 3 client.


## Putting it together 


There are 3 components to this authentication system.
1. Composing the auth
2. Login screen and routing 
3. API fetches 

### Composable Auth

See [useCognitoAuth.js](useCognitoAuth.js) for a reference implementation. Reusable across any Vue 3 app. Uses `amazon-cognito-identity-js`.

```js
// Fetches config from S3 at init (same URL as Dart app)
// https://fomomon.s3.ap-south-1.amazonaws.com/auth_config.json

init()              // fetch S3 config → create CognitoUserPool
login(user, pass)   // USER_PASSWORD_AUTH → session → store idToken ref
refreshSession()    // getSession() auto-refreshes via localStorage refresh token
logout()            // signOut() + clear refs

// Exports
idToken             // ref — JWT for API Gateway Authorization header
isAuthenticated     // computed
authError           // ref
```

### Login screen and routing 

- Username + password + org fields
- Submit -> login() -> on success redirect to capture
- Error text for wrong credentials
- No password reset, no signup - admin manages users
- Add logout button → logout() → redirect to /login.

No `NEW_PASSWORD_REQUIRED` handling - admin sets permanent passwords.

### API fetches 

The API is exposed to the static frontend via a `VITE_API_BASE_URL` env var, ideally set in the frontend itself or exported via eg netlify (or a `.env` file). Some APIs, like the APIs that aggregate sessions, require `org` in addition to the user credentials. 

```js
// VITE_API_BASE_URL=https://<api-id>.execute-api.ap-south-1.amazonaws.com/prod
export async function apiFetch(path, options = {}) {
   const baseUrl = import.meta.env.VITE_API_BASE_URL || ''
   // Attach Bearer token from useCognitoAuth
   // On 401: refreshSession() then retry once
 }
```
In dev (`VITE_API_BASE_URL` empty) -> vite proxy -> localhost:8070. 
In prod -> API Gateway URL.

This would require one to replace `fetch('/api/upload', ...)` with `apiFetch('/api/upload', ...)`

See [../docs/api.md](../docs/api.md) for a deeper description of the API.



