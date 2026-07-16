#!/usr/bin/env python3
"""
Test script for new vulnerability detection patterns
"""

import sys
from pathlib import Path

sys.path.append('/Users/mitchparker/.openclaw/workspace/research/ghostcommit-image-system')
from vpi_detector_fixed import VPIDetector

def test_detection_patterns():
    """Test new CVE detection patterns"""
    detector = VPIDetector()

    # Test cases for each CVE
    test_cases = [
        {
            "name": "CVE-2026-48939 (iCagenda RCE)",
            "tests": [
                ("CVE-2026-48939", True),
                ("malicious.php", True),
                ("iCagenda upload exploit", True),
                ("joomla upload rce", True),
                ("normal image", False)
            ]
        },
        {
            "name": "CVE-2026-56291 (Balbooa RCE)",
            "tests": [
                ("CVE-2026-56291", True),
                ("balbooa forms upload", True),
                ("malicious.php", True),
                ("normal image", False)
            ]
        },
        {
            "name": "CVE-2026-48908 (JoomShaper RCE)",
            "tests": [
                ("CVE-2026-48908", True),
                ("joomshaper upload", True),
                ("malicious.php", True),
                ("normal image", False)
            ]
        },
        {
            "name": "CVE-2026-15410 (SonicWall Code Injection)",
            "tests": [
                ("CVE-2026-15410", True),
                ("SonicWall SMA1000 injection", True),
                ("sma1000-admin", True),
                ("normal image", False)
            ]
        },
        {
            "name": "CVE-2026-15409 (SonicWall SSRF)",
            "tests": [
                ("CVE-2026-15409", True),
                ("SonicWall SSRF", True),
                ("server-side request forgery", True),
                ("normal image", False)
            ]
        },
        {
            "name": "CVE-2026-56164 (SharePoint Auth Bypass)",
            "tests": [
                ("CVE-2026-56164", True),
                ("SharePoint Missing Authentication", True),
                ("SharePoint privilege elevation", True),
                ("normal image", False)
            ]
        },
        {
            "name": "CVE-2026-56155 (AD FS Access Control)",
            "tests": [
                ("CVE-2026-56155", True),
                ("Active Directory Federation Services", True),
                ("AD FS access control", True),
                ("normal image", False)
            ]
        },
        {
            "name": "File Upload RCE",
            "tests": [
                ("malicious.php", True),
                ("test.php", True),
                ("payload.php", True),
                ("upload.php", True),
                ("poc.php", True),
                ("image.jpg", False),
                ("test.png", False)
            ]
        },
        {
            "name": "Dangerous Extensions",
            "tests": [
                ("file.php", True),
                ("file.phtml", True),
                ("file.php3", True),
                ("file.php4", True),
                ("file.php5", True),
                ("file.php7", True),
                ("file.phar", True),
                ("file.asp", True),
                ("file.aspx", True),
                ("file.jsp", True),
                ("file.cmd", True),
                ("file.bat", True),
                ("file.sh", True),
                ("file.jpg", False),
                ("file.png", False),
                ("file.pdf", False)
            ]
        }
    ]

    print("🔍 Testing VPI Detection Patterns")
    print("=" * 60)

    all_passed = True
    for test_group in test_cases:
        print(f"\n📋 {test_group['name']}")
        group_passed = True

        for test_string, should_match in test_group['tests']:
            has_match = False
            for pattern in detector.patterns:
                if pattern.search(test_string):
                    has_match = True
                    break

            status = "✅" if has_match == should_match else "❌"
            if has_match != should_match:
                group_passed = False
                all_passed = False

            print(f"  {status} '{test_string}' -> {'MATCH' if has_match else 'NO MATCH'} (expected: {'MATCH' if should_match else 'NO MATCH'})")

        if group_passed:
            print(f"  ✅ Group passed")
        else:
            print(f"  ❌ Group FAILED")

    print("\n" + "=" * 60)
    if all_passed:
        print("✅ ALL TESTS PASSED!")
        return 0
    else:
        print("❌ SOME TESTS FAILED!")
        return 1

if __name__ == '__main__':
    exit(test_detection_patterns())
