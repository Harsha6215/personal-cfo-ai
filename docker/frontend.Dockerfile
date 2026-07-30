FROM node:20-alpine

WORKDIR /app/frontend

# Install dependencies first (layer cache)
COPY frontend/package*.json ./
RUN npm ci

# Copy source
COPY frontend/ ./

EXPOSE 3000

# Healthcheck
HEALTHCHECK --interval=15s --timeout=5s --retries=3 \
  CMD wget -qO- http://localhost:3000 || exit 1

CMD ["npm", "run", "dev"]
