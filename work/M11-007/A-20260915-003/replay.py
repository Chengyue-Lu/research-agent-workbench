import json,sys
from research_workbench.execution import validate_skill_execution_receipt
r=validate_skill_execution_receipt(sys.argv[1],expected_sha256=sys.argv[2],project_root=sys.argv[3])
print(json.dumps({'status':r.document['status'],'completion_claim':r.document['completion_claim'],'task_completion':r.document['boundaries']['task_completion'],'receipt_sha256':r.receipt_sha256}))
