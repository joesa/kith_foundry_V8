# 09_SANDBOX_POLICY_AND_RUNTIME_RULES.md

## Disallowed local sandbox installs
- MySQL
- MariaDB
- MongoDB server
- Redis server
- Elasticsearch
- RabbitMQ
- Kafka
- self-hosted Postgres
- arbitrary system daemons
- privileged containers
- docker-in-docker style infra

## Allowed categories
- frontend frameworks
- approved language runtimes
- approved client libraries
- generated app code
- optional managed-service SDKs where policy allows

## Enforcement points
- dependency allow/block checks during codegen
- dependency allow/block checks during patch validation
- sandbox policy check before build
- build-time process monitoring

## Runtime limits
- CPU cap
- memory cap
- process cap
- ephemeral filesystem expectations
- inactivity shutdown or suspend policy

## Secret handling in sandbox
- ephemeral runtime injection only
- no persistence of raw secrets in project files where avoidable
- no raw secret logging
