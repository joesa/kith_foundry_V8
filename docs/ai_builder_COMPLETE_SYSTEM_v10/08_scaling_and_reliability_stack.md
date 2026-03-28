# Scaling and Reliability Stack (v10)

Target capacity: ~1M requests/day

Infrastructure:
- Upstash Redis
- Inngest
- OpenTelemetry
- Sentry
- CDN / WAF / bot protection

Redis:
- response caching
- artifact caching
- project summary caching
- rate limiting
- distributed locks
- request dedupe
- idempotency keys

Inngest:
- durable background jobs
- retries
- scheduling
- multi-step workflows
- event fan-out
- long-running repair/reflection flows
- timed idea-expiry workflows
- secret rotation / revocation jobs

This should be presented to users as part of the reliability story:
the system is not just smart — it is engineered to be durable, observable, and resilient.
