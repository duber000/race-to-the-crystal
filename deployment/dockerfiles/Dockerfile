# Race to the Crystal - Game Server
# Multi-stage build: transpile Kukicha → Go, compile static binary, copy to slim runtime

FROM golang:1.26.4-bookworm AS builder

ARG KUKICHA_VERSION=v0.48.3

# Install kukicha compiler
RUN go install github.com/kukichalang/kukicha/cmd/kukicha@${KUKICHA_VERSION}

WORKDIR /src

# Copy module files and vendored stdlib first for layer caching
COPY go.mod go.sum ./
COPY .kukicha/ .kukicha/
RUN go mod download

# Copy only the packages the game server depends on
COPY game/ game/
COPY shared/ shared/
COPY server/ server/

# Remove stale transpiled Go files so kukicha regenerates from .kuki source
RUN find game/ shared/ server/ -name 'main.go' -delete

# Transpile .kuki → .go per package; disable toolchain re-exec and pin-mismatch noise in CI
RUN KUKICHA_TOOLCHAIN=local KUKICHA_DISABLE_STDLIB_PIN_CHECK=1 kukicha build ./shared/constants/ && \
    KUKICHA_TOOLCHAIN=local KUKICHA_DISABLE_STDLIB_PIN_CHECK=1 kukicha build ./shared/enums/ && \
    KUKICHA_TOOLCHAIN=local KUKICHA_DISABLE_STDLIB_PIN_CHECK=1 kukicha build ./shared/errs/ && \
    KUKICHA_TOOLCHAIN=local KUKICHA_DISABLE_STDLIB_PIN_CHECK=1 kukicha build ./shared/types/ && \
    KUKICHA_TOOLCHAIN=local KUKICHA_DISABLE_STDLIB_PIN_CHECK=1 kukicha build ./game/ && \
    KUKICHA_TOOLCHAIN=local KUKICHA_DISABLE_STDLIB_PIN_CHECK=1 kukicha build ./server/

# Compile a static binary to a known path
RUN CGO_ENABLED=0 GOOS=linux go build -o /game-server ./server/


FROM debian:bookworm-slim

RUN adduser --disabled-password --gecos "" appuser && \
    apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

COPY --from=builder /game-server /usr/local/bin/game-server

USER appuser

ENV HTTP_PORT=8080

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -sf http://localhost:${HTTP_PORT}/api/games || exit 1

CMD ["/usr/local/bin/game-server"]
