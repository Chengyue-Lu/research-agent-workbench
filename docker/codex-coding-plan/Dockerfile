FROM node@sha256:968df39aedcea65eeb078fb336ed7191baf48f972b4479711397108be0966920

ARG RWB_ASSET_MANIFEST_SHA256
LABEL org.opencontainers.image.title="Research Agent Workbench Codex Coding Plan runtime" \
      org.opencontainers.image.version="0.1.0" \
      org.opencontainers.image.base.digest="sha256:968df39aedcea65eeb078fb336ed7191baf48f972b4479711397108be0966920" \
      io.research-workbench.asset-manifest.sha256="${RWB_ASSET_MANIFEST_SHA256}" \
      io.research-workbench.live-policy="external-allowlisted-image-digest-required"

WORKDIR /runtime
COPY package.json package-lock.json ./
RUN npm ci --omit=dev --ignore-scripts --no-audit --no-fund \
    && npm cache clean --force \
    && test "$(node -p "require('@openai/codex/package.json').version")" = "0.124.0"

COPY entrypoint.mjs models.json asset-manifest.sha256 ./
COPY package.json package-lock.json entrypoint.mjs models.json /runtime/build-inputs/
RUN test -n "${RWB_ASSET_MANIFEST_SHA256}" \
    && echo "${RWB_ASSET_MANIFEST_SHA256}  /runtime/asset-manifest.sha256" | sha256sum -c - \
    && cd /runtime/build-inputs \
    && sed '/  Dockerfile$/d' /runtime/asset-manifest.sha256 | sha256sum -c -
RUN chmod 0555 /runtime/entrypoint.mjs \
    && chmod 0444 /runtime/models.json \
    && chown -R 0:0 /runtime

USER 65532:65532
WORKDIR /workspace
ENTRYPOINT ["/runtime/entrypoint.mjs"]
