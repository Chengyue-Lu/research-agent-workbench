FROM python@sha256:285a71327884a4d50efbea30104473b0fa43ecefa499458899670ca30dae76e5

ARG RWB_ASSET_MANIFEST_SHA256
LABEL org.opencontainers.image.title="Research Agent Workbench Codex egress proxy" \
      org.opencontainers.image.version="0.1.0" \
      org.opencontainers.image.base.name="python:3.12.14-alpine3.24" \
      org.opencontainers.image.base.digest="sha256:285a71327884a4d50efbea30104473b0fa43ecefa499458899670ca30dae76e5" \
      io.research-workbench.asset-manifest.sha256="${RWB_ASSET_MANIFEST_SHA256}" \
      io.research-workbench.live-ready="false" \
      io.research-workbench.live-policy="external-topology-attestation-required"

WORKDIR /runtime
RUN mkdir -p /runtime/research_workbench/adapters /runtime/build-inputs

COPY docker/codex-egress-proxy/dependencies.lock.json /runtime/dependencies.lock.json
COPY docker/codex-egress-proxy/asset-manifest.sha256 /runtime/asset-manifest.sha256
COPY docker/codex-egress-proxy/build-context-policy.sha256 /runtime/build-context-policy.sha256
COPY docker/codex-egress-proxy/entrypoint.py /runtime/entrypoint.py
COPY src/research_workbench/adapters/codex_egress_proxy.py /runtime/research_workbench/adapters/codex_egress_proxy.py
COPY src/research_workbench/adapters/codex_egress_server.py /runtime/research_workbench/adapters/codex_egress_server.py
COPY src/research_workbench/adapters/codex_egress_container.py /runtime/research_workbench/adapters/codex_egress_container.py

COPY docker/codex-egress-proxy/Dockerfile /runtime/build-inputs/Dockerfile
COPY docker/codex-egress-proxy/dependencies.lock.json /runtime/build-inputs/dependencies.lock.json
COPY docker/codex-egress-proxy/build-context-policy.sha256 /runtime/build-inputs/build-context-policy.sha256
COPY docker/codex-egress-proxy/entrypoint.py /runtime/build-inputs/entrypoint.py
COPY src/research_workbench/adapters/codex_egress_proxy.py /runtime/build-inputs/codex_egress_proxy.py
COPY src/research_workbench/adapters/codex_egress_server.py /runtime/build-inputs/codex_egress_server.py
COPY src/research_workbench/adapters/codex_egress_container.py /runtime/build-inputs/codex_egress_container.py

RUN test -n "${RWB_ASSET_MANIFEST_SHA256}" \
    && echo "${RWB_ASSET_MANIFEST_SHA256}  /runtime/asset-manifest.sha256" | sha256sum -c - \
    && cd /runtime/build-inputs \
    && sha256sum -c /runtime/asset-manifest.sha256 \
    && python -I -S -c "import json, pathlib, platform; p=json.loads(pathlib.Path('/runtime/dependencies.lock.json').read_text('ascii')); assert p == {'distributions': [], 'python': {'implementation': 'CPython', 'version': '3.12.14'}, 'schema': 'rwb-python-dependencies-lock/0.1'}; assert platform.python_version() == '3.12.14'"

RUN chmod 0444 /runtime/dependencies.lock.json /runtime/asset-manifest.sha256 /runtime/entrypoint.py \
    /runtime/build-context-policy.sha256 \
    /runtime/research_workbench/adapters/codex_egress_proxy.py \
    /runtime/research_workbench/adapters/codex_egress_server.py \
    /runtime/research_workbench/adapters/codex_egress_container.py \
    && chown -R 0:0 /runtime

USER 65532:65532
WORKDIR /proxy
ENTRYPOINT ["/usr/local/bin/python", "-I", "-S", "/runtime/entrypoint.py"]
