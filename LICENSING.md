# Licensing Documentation

## Overview

This repository is licensed under the **Functional Source License, Version 1.1, with Apache License 2.0 Future Grant (FSL-1.1-ALv2)**.

All GitHub work in this repository is properly linked to this license through:
1. SPDX license identifiers in all source files
2. Copyright notices in file headers
3. Automated license verification via GitHub Actions
4. Clear license terms in LICENSE.md

## License Information

- **License:** FSL-1.1-ALv2
- **Copyright Holder:** Kase Branham
- **Copyright Year:** 2025
- **Future License:** Apache License 2.0 (effective 2 years from initial publication)

## What This License Means

### Current Terms (FSL-1.1)

The Functional Source License allows:
- ✓ Internal use and access
- ✓ Non-commercial education
- ✓ Non-commercial research
- ✓ Professional services using the software

The license restricts:
- ✗ Using the software in a competing commercial product
- ✗ Offering the software as a substitute service
- ✗ Creating competing functionality

### Future Terms (Apache 2.0)

After 2 years from initial publication, all code automatically becomes available under the Apache License 2.0, which is a permissive open-source license allowing commercial use.

## File Headers

All Python source files in this repository include SPDX license headers:

```python
# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
```

For files with shebang lines:

```python
#!/usr/bin/env python3
#
# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
```

## Verifying License Compliance

### Manual Verification

Run the license verification script:

```bash
python scripts/verify_license.py
```

This script checks:
- LICENSE.md exists and contains required content
- All Python files have proper SPDX headers
- All files include copyright notices
- Documentation references the license

### Automated Verification

The repository includes a GitHub Actions workflow (`.github/workflows/license-verification.yml`) that automatically verifies license compliance on:
- Every push to main branches
- Every pull request
- Manual workflow dispatch

The workflow:
1. Checks LICENSE.md existence
2. Verifies FSL-1.1-ALv2 identifier
3. Confirms copyright notices
4. Runs the full verification script
5. Generates a license compliance report

## Adding License Headers

### For New Files

When creating new Python files, always add the license header at the top:

```python
# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
```

### Bulk Addition

To add headers to multiple files, use the provided script:

```bash
python scripts/add_license_headers.py
```

This script:
- Finds all Python files in the repository
- Checks if they already have license headers
- Adds headers to files that don't have them
- Handles shebang lines correctly
- Skips excluded directories (`.git`, `__pycache__`, etc.)

## Contributing

When contributing to this repository:

1. **New Files:** Always include the license header
2. **Modified Files:** Preserve existing license headers
3. **Verification:** Run `python scripts/verify_license.py` before committing
4. **Documentation:** Update this file if license practices change

## License Linking

### How GitHub Work is Linked to the License

Every contribution to this repository is automatically linked to the FSL-1.1-ALv2 license through:

1. **Git Commits:**
   - All committed code includes SPDX headers
   - Git history preserves copyright information
   - Commit metadata links to contributors

2. **File Headers:**
   - SPDX-License-Identifier clearly identifies the license
   - Copyright notice establishes ownership
   - Headers are machine-readable for compliance tools

3. **Repository Root:**
   - LICENSE.md in root directory applies to entire repository
   - GitHub automatically detects and displays the license
   - License appears on repository page and API responses

4. **Automated Verification:**
   - GitHub Actions ensures compliance on every push
   - Pull requests can't merge without passing license checks
   - License reports are generated and archived

### Compliance Chain

```
Contribution → Git Commit → File with SPDX Header → Repository with LICENSE.md → Verified by CI/CD → Licensed under FSL-1.1-ALv2
```

## Tools and Scripts

### verify_license.py

Location: `scripts/verify_license.py`

Verifies license compliance across the entire repository.

**Usage:**
```bash
python scripts/verify_license.py
```

**Exit Codes:**
- `0` - All checks passed
- `1` - Verification failed

### add_license_headers.py

Location: `scripts/add_license_headers.py`

Adds SPDX license headers to Python files.

**Usage:**
```bash
python scripts/add_license_headers.py
```

**Features:**
- Handles shebang lines
- Skips files that already have headers
- Reports modification status

## SPDX and Machine-Readable Licenses

This repository uses SPDX (Software Package Data Exchange) identifiers for:

- **Standardization:** SPDX is an industry standard (ISO/IEC 5962:2021)
- **Machine Readability:** Tools can automatically detect licenses
- **Legal Clarity:** Unambiguous license identification
- **Compliance:** Easier to track and audit

The SPDX identifier `FSL-1.1-ALv2` maps to the Functional Source License 1.1 with Apache License 2.0 Future Grant.

## Frequently Asked Questions

### Q: Can I use this code commercially?

A: Only for permitted purposes defined in the license. You cannot use it to create a competing product or service. After 2 years, it becomes Apache 2.0 licensed and fully permissive.

### Q: Do I need to include the license in my fork?

A: Yes, the FSL-1.1 requires that you include the LICENSE.md file and retain all license details when redistributing.

### Q: What if I modify a file?

A: Keep the existing license header. The copyright remains with the original author, but you may add your own copyright line if making substantial changes.

### Q: How do I know my contribution is properly licensed?

A: The GitHub Actions workflow will verify license compliance. If it passes, your contribution is properly licensed.

## References

- **Full License Text:** [LICENSE.md](LICENSE.md)
- **Buyer Beware Notice:** [Buyer-Beware.md](Buyer-Beware.md)
- **SPDX Specification:** https://spdx.dev/
- **Functional Source License:** https://fsl.software/
- **Apache License 2.0:** https://www.apache.org/licenses/LICENSE-2.0

## Maintenance

This licensing setup should be maintained by:

1. Running verification before major releases
2. Updating copyright year when necessary
3. Ensuring new contributors understand licensing
4. Keeping this documentation current
5. Monitoring GitHub Actions for license check failures

---

**Last Updated:** 2025-12-19
**Maintained By:** RRA Module Team
