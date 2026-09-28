"""Developer-only durable synthetic proof builder and offline replay entry.

Use caller-pinned inventory bytes and repository-owned synthetic verifiers.
An inventory is evidence, never executable code or real admission authority.
Historical proofs require their pinned validator, schemas and helper sources.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys
from unittest.mock import patch

from research_workbench.evaluation.harness_analysis import (
    AnalysisContext, MetricContext, validate_harness_analysis,
)
from research_workbench.evaluation.harness_execution import HarnessContext
from research_workbench.evaluation.harness_review import FreezeContext, ReviewContext
from research_workbench.evaluation.pins import EvaluationInputs, require
from tests import harness_analysis_data
from tests.harness_analysis_data import AUTH

FORMAT = 'm5-harness-synthetic-proof-v1'


def ref(root, path):
    path = Path(path)
    return {'path': path.relative_to(root).as_posix(),
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def save(root, relative, document):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(json.dumps(document, ensure_ascii=False, indent=2).encode('utf-8') + b'\n')
    return ref(root, path)


def replay_sources():
    # Trusted installed/repository module locations, never paths supplied by evidence.
    return {name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in (
        ('tests/harness_proof.py', Path(__file__)),
        ('tests/harness_analysis_data.py', Path(harness_analysis_data.__file__)),
    )}


def decode_context(value):
    value = dict(value)
    metric = dict(value['metrics'])
    review = dict(metric['review'])
    review['harness'] = HarnessContext(**review['harness'])
    metric['review'] = ReviewContext(**review)
    metric['freeze'] = FreezeContext(**metric['freeze'])
    value['metrics'] = MetricContext(**metric)
    return AnalysisContext(**value)


def build_proof(root, schema_root):
    # Lazy import: cold replay never imports the generator or qualified Tool loader.
    from research_workbench.adapters.models import ProviderError, ProviderErrorCategory
    from tests.harness_analysis_fixtures import build_analysis_chain

    root = Path(root).resolve()
    require(not root.exists() or not any(root.iterdir()), 'proof destination must be empty')
    root.mkdir(parents=True, exist_ok=True)
    previous = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        fixture, context, analysis_ref, document = build_analysis_chain(root, provider_errors=(
            ProviderError(ProviderErrorCategory.TRANSIENT, 'Synthetic H5 transient failure'),
        ))
    finally:
        sys.dont_write_bytecode = previous
    # Fixture contracts select the repository schema root. Fail if the caller selected another identity.
    require(EvaluationInputs(root, schema_root).schema_hashes == fixture.inputs().schema_hashes,
            'proof generation schema identity substitution')
    request_ref = save(root, 'analysis/replay-request.json', {
        'format': FORMAT, 'purpose': 'synthetic-contract-proof',
        'analysis_ref': analysis_ref, 'analysis_id': document['analysis_id'],
        'context': asdict(context),
    })
    files = [ref(root, path) for path in sorted(root.rglob('*')) if path.is_file()]
    inventory_ref = save(root, 'proof-inventory.json', {
        'format': FORMAT, 'purpose': 'synthetic-contract-proof',
        'request_ref': request_ref, 'replay_sources': replay_sources(), 'files': files,
    })
    return inventory_ref


def replay_proof(root, schema_root, inventory_ref, *, verifiers=None):
    inputs = EvaluationInputs(root, schema_root)
    inventory = inputs.read(inventory_ref)
    require(set(inventory) == {'format', 'purpose', 'request_ref', 'replay_sources', 'files'}
            and inventory['format'] == FORMAT and inventory['purpose'] == 'synthetic-contract-proof',
            'unsupported synthetic proof inventory')
    require(inventory['replay_sources'] == replay_sources(), 'proof replay source identity drift')
    files = inventory['files']
    require(isinstance(files, list) and files and len({r['path'] for r in files}) == len(files),
            'proof inventory must have unique file paths')
    require(inventory['request_ref'] in files, 'proof request omitted from inventory')
    for item in files:
        inputs.read_bytes(item)
    request = inputs.read(inventory['request_ref'])
    require(set(request) == {'format', 'purpose', 'analysis_ref', 'analysis_id', 'context'}
            and request['format'] == FORMAT and request['purpose'] == 'synthetic-contract-proof',
            'unsupported synthetic replay request')
    require(request['analysis_ref'] in files, 'analysis omitted from proof inventory')
    context = decode_context(request['context'])
    # These guards also apply to same-process developer use. The CLI adds an audit hook.
    with patch('research_workbench.evaluation.harness_execution.run_baseline_session',
               side_effect=AssertionError('Provider execution during proof replay')), \
         patch('research_workbench.evaluation.harness_runtime.execute_frozen_view',
               side_effect=AssertionError('Host execution during proof replay')):
        document = validate_harness_analysis(inputs,
            expected_analysis_ref=request['analysis_ref'], expected_analysis_id=request['analysis_id'],
            context=context, **(AUTH if verifiers is None else verifiers))
    inputs.recheck()
    return document


def summary(root, schema_root, document):
    inputs = EvaluationInputs(root, schema_root)
    metrics = inputs.read(document['metrics_ref'])
    return {
        'purpose': document['purpose'], 'analysis_id': document['analysis_id'],
        'arms': sorted({c['target']['arm_id'] for c in metrics['cells']}),
        'cells': len(metrics['cells']), 'pairs': len(document['pairs']),
        'lifecycles': {name: sum(a['lifecycle'] == name for c in metrics['cells'] for a in c['attempts'])
                       for name in ('completed', 'post-call-failed', 'not-started')},
        'all_metrics_unavailable': all(m['status'] == 'unavailable' and m['value'] is None
                                      for p in document['pairs'] for m in p['metrics']),
        'primary_confirmatory_eligible': any(p['primary_confirmatory_eligible'] for p in document['pairs']),
    }


def deny_execution(root):
    root = Path(root).resolve()
    def audit(event, args):
        if event.startswith('socket.') or event in {'subprocess.Popen', 'os.system', 'os.posix_spawn', 'os.fork', 'os.exec', 'os.spawn', 'os.startfile'}:
            raise AssertionError('network/process execution during synthetic proof replay')
        if event == 'exec':
            source = Path(args[0].co_filename).resolve()
            if source.is_relative_to(root):
                raise AssertionError('proof-directory code execution during replay')
    sys.addaudithook(audit)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('build', 'replay'))
    parser.add_argument('--root', required=True, type=Path)
    parser.add_argument('--schemas', required=True, type=Path)
    parser.add_argument('--inventory-ref', type=json.loads)
    args = parser.parse_args()
    if args.operation == 'build':
        require(args.inventory_ref is None, 'build cannot reuse an inventory')
        result = build_proof(args.root, args.schemas)
    else:
        require(args.inventory_ref is not None, 'replay needs caller-pinned inventory bytes')
        deny_execution(args.root)
        result = summary(args.root, args.schemas, replay_proof(args.root, args.schemas, args.inventory_ref))
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
