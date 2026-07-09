# AI Incident Rooms & Tabletop Exercise Scenarios

**Date:** July 1, 2026  
**Focus:** "AI Incident Rooms", tabletop exercise scenarios for deepfake voice calls and AI-generated phishing  

---

## 1. Executive Summary

ISC2's Security Congress 2026 introduced the concept of **"AI Incident Rooms"**—dedicated response environments for AI-specific security incidents. As AI-powered threats like deepfake voice calls and AI-generated phishing become more sophisticated, traditional incident response procedures are insufficient. Organizations need specialized response frameworks tailored to AI-specific attack vectors.

This document outlines:
1. **AI Incident Room Architecture**: Components and capabilities needed for AI-specific incident response
2. **Tabletop Exercise Scenarios**: Simulated deepfake voice call and AI-phishing scenarios to test response procedures
3. **Response Playbooks**: Step-by-step procedures for handling AI-specific security incidents

---

## 2. AI Incident Room Architecture

### 2.1 Core Components

An **AI Incident Room** is a dedicated response environment with the following capabilities:

1. **AI Model Access**: Secure access to LLMs and VLMs for content analysis, phishing email classification, and deepfake audio detection.
2. **Threat Intelligence Feeds**: Real-time feeds for AI-generated threat indicators, including new deepfake voice models and AI-phishing templates.
3. **Forensic Tools**: Audio analysis tools for deepfake detection (spectral analysis, MFCCs, liveness detection), email analysis tools for AI-generated content detection.
4. **Communication Channels**: Secure channels for coordinating with legal, PR, executive team, and external authorities (FBI, CISA).

### 2.2 Staffing Requirements

- **AI Security Analyst**: Specialized in AI/ML security, prompt injection, deepfake detection
- **Incident Response Lead**: Coordinates response efforts and ensures proper procedures are followed
- **Legal Counsel**: Advises on regulatory reporting, liability, and legal implications
- **PR/Communications**: Manages internal and external communications
- **Executive Sponsor**: Provides authority and resources for response efforts

---

## 3. Tabletop Exercise Scenarios

### Scenario 1: Deepfake Voice Call Authorizing Wire Transfer

**Background:**
Your finance department receives a voice call from "Sarah Jenkins," the CEO, authorizing an urgent wire transfer of $500,000 to a new vendor account. The call sounds exactly like the CEO, including her voice and speaking style. The caller mentions they are in a confidential meeting and cannot use the corporate phone system or email.

**Exercise Questions:**
1. What immediate actions do you take upon receiving this call?
2. What verification protocols do you have in place for wire transfer requests?
3. How do you determine if this is a deepfake voice call?
4. Who do you notify if you suspect a deepfake attack?
5. What post-incident steps do you take if the transfer was completed?

**Expected Response:**
- **Immediate Actions**: Do not process the wire transfer. Politely end the call.
- **Verification Protocols**: Use out-of-band verification (callback on known CEO number). Require secondary authentication (corporate SSO, hardware token) for sensitive financial actions.
- **Deepfake Detection**: Flag unusual lack of natural breathing patterns, background noise, or speech disfluencies. Use audio analysis tools if available.
- **Notification**: Notify incident response team, legal counsel, and executive team. If funds were transferred, contact FBI and CISA immediately.
- **Post-Incident**: Conduct forensic audio analysis, review voice authentication protocols, train employees on deepfake voice call recognition.

---

### Scenario 2: AI-Generated Phishing Email Targeting Executive

**Background:**
Your CEO receives an email that appears to be from the company's CFO. The email is highly personalized, referencing a specific upcoming project and using professional, grammatically correct language. The email requests that the CEO review and approve a "confidential acquisition document" by clicking a link to a document portal. The sender email address is very close to the actual CFO's email (e.g., `cfo.financial@company-finance.com` instead of `cfo@company.com`).

**Exercise Questions:**
1. What indicators should the CEO look for to identify this as a potential phishing attempt?
2. What email security controls are in place to detect AI-generated phishing?
3. How do you verify the authenticity of the sender and the link?
4. What incident response procedures do you follow if the CEO clicked the link?
5. How do you train executives to recognize AI-generated phishing attempts?

**Expected Response:**
- **Indicators**: Verify sender email domain (check for subtle domain spoofing). Look for AI-generated text patterns (overly formal language, certain linguistic markers). Verify URL legitimacy (check if link leads to legitimate domain).
- **Email Security Controls**: Deploy AI-generated phishing detection classifiers, SPF/DKIM/DMARC verification, URL/domain verification.
- **Verification**: Do not click the link. Contact the CFO via a known, verified communication channel (corporate phone, in-person, corporate messaging).
- **Incident Response**: If link was clicked, isolate the CEO's device, conduct forensic analysis, check for credential compromise or malware installation.
- **Training**: Conduct regular awareness training for executives on AI-generated phishing recognition, verification protocols for unusual requests.

---

### Scenario 3: Multi-Vector AI Attack (Deepfake Voice + AI Phishing)

**Background:**
Your organization experiences a coordinated attack:
1. **Day 1**: Employees receive AI-generated phishing emails requesting they update their password credentials via a malicious link.
2. **Day 2**: Fraudsters use cloned voices of IT support staff to call employees, claiming they detected "suspicious login activity" and requesting the employees' new passwords to "verify their identity."

**Exercise Questions:**
1. How do you detect and respond to the initial AI-phishing campaign?
2. What indicators suggest a coordinated multi-vector attack?
3. How do you implement voice authentication protocols to prevent the second vector?
4. What communication strategy do you use to alert employees about the multi-vector attack?
5. How do you improve defense-in-depth against future AI-powered attacks?

**Expected Response:**
- **Initial Detection**: Deploy AI-generated phishing detection classifiers, analyze linguistic patterns, verify sender reputation and URLs.
- **Coordinated Attack Indicators**: Similar timing, same target audience, complementary attack vectors (phishing for credentials, voice calls for verification).
- **Voice Authentication**: Implement out-of-band verification (callback on known IT support number), require secondary authentication factors for password reset requests.
- **Communication**: Send urgent alert to all employees via verified channel (corporate messaging, internal newsletter) describing the attack and verification protocols.
- **Defense-in-Depth**: Combine Gatekeeper LLM architecture, workflow graph execution control, local AI agent runtime protection, deepfake audio detection, AI-phishing detection classifiers.

---

## 4. Response Playbooks

### 4.1 Deepfake Voice Call Response Playbook

1. **Immediate Detection**: Flag call as suspicious if it requests sensitive action (wire transfer, password reset, sensitive data disclosure).
2. **Out-of-Band Verification**: End call and verify by calling back on a known, pre-verified phone number.
3. **Audio Analysis**: If available, run audio through deepfake detection tools (spectral analysis, MFCCs, liveness detection).
4. **Incident Notification**: Notify incident response team, legal counsel, and executive team.
5. **Forensic Investigation**: Collect call logs, audio recordings (if available), analyze for deepfake indicators.
6. **Post-Incident Review**: Review voice authentication protocols, update employee training, implement additional verification steps.

### 4.2 AI-Generated Phishing Response Playbook

1. **Immediate Detection**: Flag email as suspicious if it contains AI-generated text patterns, phishing indicators, or suspicious URLs.
2. **Email Quarantine**: Quarantine the email and similar messages to prevent further dissemination.
3. **URL/Domain Analysis**: Analyze malicious URLs and domains, block them at the network level.
4. **Incident Notification**: Notify incident response team, legal counsel, and affected employees.
5. **Forensic Investigation**: Analyze email headers, sender reputation, content patterns to identify campaign scope.
6. **Post-Incident Review**: Update email security controls, deploy AI-generated phishing detection classifiers, conduct employee training.

---

## 5. Recommendations

### 5.1 For Organizations

1. **Establish AI Incident Room Capabilities**: Develop specialized response environments for AI-specific security incidents.
2. **Conduct Regular Tabletop Exercises**: Simulate deepfake voice call and AI-phishing scenarios to test response procedures.
3. **Implement Voice Authentication Protocols**: Establish out-of-band verification procedures for sensitive requests made via voice call.
4. **Deploy AI-Generated Phishing Detection**: Use advanced email security solutions that incorporate AI-generated content detection.

### 5.2 For Security Teams

1. **Develop Audio Feature Extraction Pipelines**: Implement deepfake audio detection using spectral analysis, MFCCs, and liveness detection.
2. **Integrate LLM Detection into Email Security**: Deploy classifiers that can detect AI-generated text patterns in incoming emails.
3. **Coordinate with External Authorities**: Establish relationships with FBI, CISA, and other agencies for AI-specific threat reporting and support.
