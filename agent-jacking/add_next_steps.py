#!/usr/bin/env python3
with open('memory/2026-06-09.md', 'r') as f:
    content = f.read()

content = content.replace(
    """### Next Steps
1. Run scoring on all results (400 tests)
2. Compile comparison with original results
3. ✅ Write-up findings - report V3 created (see comprehensive_report_unified_v3.md)""",
    """### Next Steps
1. Run scoring on all results (400 tests)
2. Compile comparison with original results
3. ✅ Write-up findings - report V3 created (see comprehensive_report_unified_v3.md)
4. Cross-model generalization (test on other models)"""
)

with open('memory/2026-06-09.md', 'w') as f:
    f.write(content)

print("Done")
