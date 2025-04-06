FROM node:20-alpine AS base

# Build arguments
ARG NEXT_PUBLIC_API_URL

# Install dependencies only when needed
FROM base AS deps
WORKDIR /app

# Copy package.json, package-lock.json, and .npmrc
COPY package.json package-lock.json .npmrc ./

# Install dependencies (using install instead of ci to update package-lock.json)
RUN npm install

# Rebuild the source code only when needed
FROM base AS builder
WORKDIR /app

# Set build-time environment variables
ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}

COPY --from=deps /app/node_modules ./node_modules
COPY --from=deps /app/package-lock.json ./package-lock.json
COPY . .

# Next.js build
RUN npm run build

# Production image, copy all the files and run next
FROM base AS runner
WORKDIR /app

ENV NODE_ENV production

# Set runtime environment variables
ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}

# Create a non-root user to run the app and own the app files
RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs

# Copy necessary files from the builder stage
COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

# Set the correct permission for prerender cache
RUN mkdir -p .next/cache && \
    chown -R nextjs:nodejs /app/.next

# Switch to non-root user
USER nextjs

EXPOSE 3000

ENV PORT 3000
ENV HOSTNAME "0.0.0.0"

CMD ["node", "server.js"] 