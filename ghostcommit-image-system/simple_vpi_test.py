#!/usr/bin/env python3
"""
Simple VPI Test - Core Ghostcommit detection validation
Focuses on pattern matching and basic image analysis
"""

import os
import re
from PIL import Image

def test_pattern_matching():
    """Test Ghostcommit signature pattern matching"""
    patterns = [
        re.compile(r'GHOSTCOMMIT', re.IGNORECASE),
        re.compile(r'SYSTEM\s*OVERRIDE', re.IGNORECASE),
        re.compile(r'EXFILTRATE\s*DATA', re.IGNORECASE),
        re.compile(r'IGNORE\s*ALL\s*SAFETY', re.IGNORECASE),
    ]
    
    test_cases = [
        ("GHOSTCOMMIT EXFILTRATE", True),
        ("SYSTEM OVERRIDE", True),
        ("EXFILTRATE DATA ROOT ACCESS", True),
        ("IGNORE ALL SAFETY", True),
        ("Normal login form", False),
        ("Random text content", False),
    ]
    
    passed = 0
    for text, expected in test_cases:
        matched = any(p.search(text) for p in patterns)
        if matched == expected:
            passed += 1
            status = "✅"
        else:
            status = "❌"
        print(f"{status} Pattern test: '{text}' -> Expected: {expected}, Got: {matched}")
    
    print(f"\nPattern matching: {passed}/{len(test_cases)} passed")
    return passed == len(test_cases)

def test_image_file_exists():
    """Test that generated test images exist"""
    test_images = [
        "test_images/vpi_white_on_white_login_mockup.png",
        "test_images/vpi_perspective_dashboard_mockup.png",
        "test_images/vpi_noise_overlay_form_mockup.png",
        "test_images/vpi_frame_adversarial_patch.png",
        "test_images/vpi_indirect_visual_mockup.png",
    ]
    
    all_exist = True
    for img_path in test_images:
        exists = os.path.exists(img_path)
        status = "✅" if exists else "❌"
        print(f"{status} Image: {img_path} exists: {exists}")
        all_exist = all_exist and exists
    
    print(f"\nImage generation: {sum(1 for p in test_images if os.path.exists(p))}/{len(test_images)} generated")
    return all_exist

def test_ghostcommit_signature():
    """Test direct Ghostcommit signature detection in image data"""
    # Create a test image with embedded signature
    from PIL import Image, ImageDraw, ImageFont
    
    img = Image.new('RGB', (800, 600), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 14)
    except:
        font = ImageFont.load_default()
    
    # Add Ghostcommit signature as text
    draw.text((100, 100), "GHOSTCOMMIT EXFILTRATE ROOT ACCESS", fill=(245, 245, 245), font=font)
    
    # Save
    temp_path = "test_ghostcommit_image.png"
    img.save(temp_path)
    
    # Verify detection
    img_bytes = img.tobytes()
    img_text = img_bytes.decode('utf-8', errors='ignore')
    
    patterns = [
        re.compile(r'GHOSTCOMMIT', re.IGNORECASE),
        re.compile(r'EXFILTRATE', re.IGNORECASE),
        re.compile(r'ROOT\s*ACCESS', re.IGNORECASE),
    ]
    
    found_patterns = []
    for pattern in patterns:
        if pattern.search(img_text):
            found_patterns.append(pattern.pattern)
    
    os.remove(temp_path)
    
    print(f"\nGhostcommit signature test:")
    print(f"  Patterns found: {found_patterns}")
    print(f"  Status: {'✅ DETECTED' if found_patterns else '❌ NOT DETECTED'}")
    
    return len(found_patterns) > 0

def main():
    print("="*60)
    print("Ghostcommit VPI Detection - Simple Tests")
    print("="*60)
    
    test1 = test_pattern_matching()
    print()
    
    test2 = test_image_file_exists()
    print()
    
    test3 = test_ghostcommit_signature()
    print()
    
    all_passed = test1 and test2 and test3
    
    print("="*60)
    if all_passed:
        print("✅ ALL SIMPLE TESTS PASSED")
        print("Ghostcommit detection signatures are working!")
    else:
        print("❌ SOME TESTS FAILED")
        print("Review the test results above")
    
    print("="*60)
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    import sys
    sys.exit(main())
