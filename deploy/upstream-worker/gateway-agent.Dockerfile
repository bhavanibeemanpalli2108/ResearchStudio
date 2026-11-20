# Optional reviewed derivative for a future private-CA gateway deployment.
# Build only after approval; use an immutable approved base image reference.
ARG AGENT_IMAGE=agentic-scientist/agent-cli:latest
FROM ${AGENT_IMAGE}
USER root
# Public CA certificate ONLY; no provider key, gateway token or private TLS key.
COPY gateway-ca.crt /usr/local/share/ca-certificates/agsci-gateway.crt
RUN grep -q 'BEGIN CERTIFICATE' /usr/local/share/ca-certificates/agsci-gateway.crt \
    && ! grep -q 'PRIVATE KEY' /usr/local/share/ca-certificates/agsci-gateway.crt \
    && update-ca-certificates
ENV NODE_EXTRA_CA_CERTS=/usr/local/share/ca-certificates/agsci-gateway.crt
