## Deployment 

### Quickstart


__local__

```console 
$ docker compose up --build -d
$ curl http://localhost:8070/api/health                    # → {"status":"ok"}
$ curl -X POST http://localhost:8070/api/upload/json \
   -H "Content-Type: application/json" \
   -d @server/test/000_layout.json -o /tmp/test.xlsx -w "%{http_code}"  # → 200
$ docker compose down
```

__prod__

```console 
$ cd deploy && ./setup.sh && ./deploy.sh
$ source outputs.env
$ curl "${APIGW_URL}/api/health"                           # → 200
$ curl -X POST "${APIGW_URL}/api/upload" -w "%{http_code}" # → 401

$ ./add-user.sh user@foo.com password
 # Get token:
$ TOKEN=$(aws cognito-idp admin-initiate-auth \
   --user-pool-id ap-south-1_28HVATwK2 \
   --client-id 1j0f2k3top2af4m8da7nbmeu63 \
   --auth-flow ADMIN_USER_PASSWORD_AUTH \
   --auth-parameters USERNAME=testuser@example.com,PASSWORD=SomePassword123 \
   --query 'AuthenticationResult.IdToken' --output text)
$ curl -X POST "${APIGW_URL}/api/upload/json" \
   -H "Authorization: Bearer ${TOKEN}" \
   -H "Content-Type: application/json" \
   -d @server/test/000_layout.json -o /tmp/lambda.xlsx -w "%{http_code}"  # → 200
```


### Scripts breakdown 

1. `deploy/build.sh` — build image + optional smoke test: 

- docker build -t form-idable-server:latest ./server/
- With --test: run container, curl /api/health, stop

2. `deploy/push.sh` - ECR login, tag, push, create/update Lambda

- If Lambda exists, update-function-code, else create-function (512MB, 60s timeout)
- aws lambda wait function-active-v2

3. `deploy/deploy.sh` - orchestrator

Runs build.sh --test then push.sh, prints API Gateway URL.

4. `deploy/add-user.sh <email> <password>` - new users 

Mirrors fomomon admin pattern:
```console 
aws cognito-idp admin-create-user --username "$EMAIL" --temporary-password "$PASS" --message-action SUPPRESS ...
aws cognito-idp admin-set-user-password --username "$EMAIL" --password "$PASS" --permanent ...
```
No temp password email, no forced reset. User logs in directly.

5. `deploy/trust-policy.json + deploy/lambda-policy.json`

