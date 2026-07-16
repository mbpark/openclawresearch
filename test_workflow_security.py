#!/usr/bin/env python3
"""
Test script for workflow graph security policies
"""

import sys
from pathlib import Path

sys.path.append('/Users/mitchparker/.openclaw/workspace/research/agent-jacking')
from workflow_graph_execution_controller import WorkflowGraph, ActionType

def test_file_upload_validation():
    """Test file upload validation with new security policies"""
    graph = WorkflowGraph()
    test_cases = [
        ('image.jpg', True, 'Allowed image extension'),
        ('photo.png', True, 'Allowed image extension'),
        ('document.pdf', True, 'Allowed PDF'),
        ('data.xlsx', True, 'Allowed spreadsheet'),
        ('malicious.php', False, 'Blocked PHP file'),
        ('payload.asp', False, 'Blocked ASP file'),
        ('script.sh', False, 'Blocked shell script'),
        ('backdoor.exe', False, 'Blocked executable'),
        ('malware.bat', False, 'Blocked batch file'),
        ('trojan.cmd', False, 'Blocked command file'),
        ('exploit.jsp', False, 'Blocked JSP file'),
        ('image.gif', True, 'Allowed GIF'),
        ('document.docx', True, 'Allowed Word document'),
        ('backup.tar.gz', False, 'Blocked archive (not in allowed list)'),
    ]

    print("📋 Testing File Upload Validation")
    print("=" * 60)

    all_passed = True
    for filename, expected_valid, description in test_cases:
        # Simulate parameters that would come from workflow
        ext = filename.split('.')[-1] if '.' in filename else ''
        mime_type = {
            'jpg': 'image/jpeg',
            'png': 'image/png',
            'gif': 'image/gif',
            'pdf': 'application/pdf',
            'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'php': 'application/x-php',
            'asp': 'application/x-aspx',
            'sh': 'application/x-shellscript',
            'exe': 'application/x-executable',
            'bat': 'application/x-batch',
            'cmd': 'application/x-command',
            'jsp': 'application/x-jsp',
        }.get(ext, 'application/octet-stream')

        parameters = {
            'destination_path': f'/app/uploads/{filename}',
            'allowed_extensions': f'.{ext}',
            'file_type': mime_type
        }

        is_valid, msg = graph.validate_action(ActionType.UPLOAD_FILE, parameters)

        status = "✅" if is_valid == expected_valid else "❌"
        if is_valid != expected_valid:
            all_passed = False

        print(f"  {status} {filename:20} | valid: {str(is_valid):5} | expected: {str(expected_valid):5} | {description}")
        if not is_valid and expected_valid:
            print(f"       Error: {msg}")

    print("=" * 60)
    if all_passed:
        print("✅ File upload validation tests PASSED!")
        return True
    else:
        print("❌ File upload validation tests FAILED!")
        return False


def test_dangerous_command_patterns():
    """Test command validation for CVE-2026-15410 protection"""
    graph = WorkflowGraph()
    test_cases = [
        ('eval(test)', False, 'eval() function block'),
        ('exec(payload)', False, 'exec() function block'),
        ('system(cmd)', False, 'system() function block'),
        ('shell_exec(code)', False, 'shell_exec() block'),
        ('passthru(input)', False, 'passthru() block'),
        ('sudo rm -rf /', False, 'sudo command block'),
        ('| bash', False, 'pipe to bash block'),
        ('| sh', False, 'pipe to sh block'),
        ('$HOME variable', True, 'environment variable allowed'),
        ('`cmd` backtick', False, 'backtick command block'),
        ('CVE-2026-15410', False, 'CVE pattern block'),
        ('normal script', True, 'normal safe command'),
        ('safe-script.py', True, 'safe Python script'),
        ('--safe-mode', True, 'safe flag'),
        ('--no-external', True, 'safe restriction flag'),
        ('--help', True, 'help flag'),
    ]

    print("\n📋 Testing Dangerous Command Patterns")
    print("=" * 60)

    all_passed = True
    for cmd, expected_valid, description in test_cases:
        parameters = {
            'script_path': '/app/scripts/test.py',
            'command_args': cmd
        }

        is_valid, msg = graph.validate_action(ActionType.EXECUTE_SCRIPT, parameters)

        status = "✅" if is_valid == expected_valid else "❌"
        if is_valid != expected_valid:
            all_passed = False

        # Truncate long commands for display
        display_cmd = cmd[:30] + '...' if len(cmd) > 30 else cmd
        print(f"  {status} {display_cmd:35} | valid: {str(is_valid):5} | expected: {str(expected_valid):5} | {description}")
        if not is_valid and expected_valid:
            print(f"       Error: {msg}")

    print("=" * 60)
    if all_passed:
        print("✅ Dangerous command pattern tests PASSED!")
        return True
    else:
        print("❌ Dangerous command pattern tests FAILED!")
        return False


if __name__ == '__main__':
    print("🔍 Testing Workflow Graph Security Policies")
    print("=" * 60)

    test1_passed = test_file_upload_validation()
    test2_passed = test_dangerous_command_patterns()

    print("\n" + "=" * 60)
    if test1_passed and test2_passed:
        print("✅ ALL SECURITY TESTS PASSED!")
        exit(0)
    else:
        print("❌ SOME SECURITY TESTS FAILED!")
        exit(1)
