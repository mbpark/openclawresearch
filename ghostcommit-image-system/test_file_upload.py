from image_protection_service import ImageProtectionService

service = ImageProtectionService()

# Test file upload scanning
file_path = "/app/uploads/malicious.php"
file_type = "application/x-php"
content = "<?php system(\$_GET['cmd']); ?>"

is_threat, patterns = service.scan_file_upload(file_path, file_type, content)
print(f"File upload scan: is_threat={is_threat}")
print(f"Detected patterns: {patterns}")

if is_threat and len(patterns) > 0:
    print("✅ File upload scan PASSED")
else:
    print("❌ File upload scan FAILED")
    exit(1)
