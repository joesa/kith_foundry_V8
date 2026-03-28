FROM node:20-alpine

# curl needed for health checks / debugging
RUN apk add --no-cache curl

WORKDIR /app

# Copy bootstrap script
COPY bootstrap.mjs .

# Pre-create workspace dir
RUN mkdir -p /workspace

EXPOSE 3000

CMD ["node", "/app/bootstrap.mjs"]
