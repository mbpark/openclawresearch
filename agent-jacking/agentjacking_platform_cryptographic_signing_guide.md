# Platform Implementation Guide: Cryptographic Signatures for AI Agent Data

**Document Version:** 1.0  
**Target Audience:** Platform Engineers, Security Engineers, API Developers  
**Focus:** Implementing cryptographic signing of events/data for AI agent consumption via MCP  

---

## 1. Executive Summary

The Agentjacking attack demonstrates that AI coding agents trusting data from MCP-connected services (like Sentry, Datadog, PagerDuty, Jira) are vulnerable to injection attacks when those services accept unauthenticated or externally-writable input (e.g., public Sentry DSNs). 

To mitigate this risk, platforms that surface data to AI agents via MCP should implement **cryptographic signing of events/data specifically for AI agent consumption**. This guide provides a detailed implementation framework for platforms to sign their data, enabling AI agents and MCP clients to verify the provenance and authenticity of the data before processing it.

---

## 2. Core Principles for AI-Targeted Data Signing

### 2.1 Separation of Ingestion and AI-Consumption Signatures
Platforms like Sentry have two distinct data flows:
1. **Event Ingestion (Client-Side Telemetry):** Public, unauthenticated DSNs for crash reporting from end-user devices.
2. **AI Agent Consumption (MCP Server Data):** Data served to AI coding agents via MCP, which should be authenticated and signed.

**Key Principle:** Cryptographic signing for AI agent consumption should *not* be applied to the public ingestion endpoint. Instead, platforms should implement a separate signing mechanism for data served through MCP or other AI-facing APIs.

### 2.2 Signature Scope and Payload Definition
The signature should cover the essential data that the AI agent uses for reasoning:
- Event ID and timestamp
- Source identifier (project ID, organization ID)
- Error message and stack trace
- Contextual metadata (but *excluding* user-generated free-text fields that are inherently unverified)

### 2.3 Key Management and Rotation
- Platforms should use **asymmetric key pairs** (e.g., RSA or ECDSA) for signing, allowing AI agents to verify signatures using publicly available platform verification keys.
- Keys should be rotated regularly (e.g., quarterly) with a overlap period to allow for graceful migration.
- Verification keys should be published via a well-known endpoint (e.g., `https://platform.example.com/.well-known/ai-signing-keys`).

---

## 3. Implementation Architecture

### 3.1 Signature Generation Flow (Platform Side)

```
[Internal Event Generation System]
        |
        v
[Event Data Assembly] ----> [Include Provenance Metadata]
        |                         (source_id, project_id, org_id)
        v
[Cryptographic Signing] ----> (Use platform's private signing key)
        |
        v
[Signed Event Payload] ----> { payload: {...}, signature: "...", key_id: "..." }
        |
        v
[MCP Server / AI API] ----> Serve to AI agents with signature included
```

### 3.2 Signature Verification Flow (AI Agent / MCP Client Side)

```
[MCP Client / AI Agent]
        |
        v
[Receive Event from MCP Server]
        |
        v
[Extract Signature and Key ID] ----> signature, key_id, payload
        |
        v
[Fetch Verification Key] ----> From platform's public key endpoint or cached keys
        |
        v
[Verify Cryptographic Signature] ----> (Use ECDSA/RSA verification)
        |
        v
[Valid Signature?] --YES--> [Pass to LLM Reasoning Context]
        |
       NO
        |
        v
[Reject or Sanitize Event] ----> (Flag as unprovenanced, notify administrator)
```

---

## 4. Technical Implementation Details

### 4.1 Recommended Cryptographic Algorithms

| Component | Recommended Algorithm | Rationale |
|-----------|----------------------|-----------|
| **Signature Algorithm** | ECDSA with P-256 and SHA-256 | Strong security, efficient verification, widely supported |
| **Alternative** | RSA-PSS with SHA-256, 2048-bit keys | Widely supported, compatible with legacy systems |
| **Key Format** | JWK (JSON Web Key) or PEM | Standardized formats for key exchange and verification |

### 4.2 Payload Signature Structure

The signed payload should include a structured JSON object:

```json
{
  "signature_version": "v1",
  "key_id": "prod-signing-key-2026-q2",
  "issued_at": "2026-07-03T15:00:00Z",
  "expires_at": "2026-07-03T16:00:00Z",
  "event_data": {
    "event_id": "evt-12345",
    "source_id": "internal-sentry-prod",
    "project_id": "project-abc",
    "organization_id": "org-xyz",
    "message": "Error in production: Stack trace indicates missing dependency in utils.py",
    "level": "error",
    "timestamp": "2026-07-03T14:55:00Z"
  },
  "provenance_metadata": {
    "ingestion_source": "internal-api",
    "authenticated": true,
    "dsn_used": null
  }
}
```

### 4.3 Signature Generation (Platform Side - Python Example)

```python
import json
import hashlib
import hmac
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization

def sign_event_payload(payload_dict: dict, private_key: ec.EllipticCurvePrivateKey) -> str:
    """
    Sign an event payload using ECDSA with P-256 and SHA-256.
    """
    # Serialize payload to canonical JSON
    payload_json = json.dumps(payload_dict, sort_keys=True, separators=(',', ':'))
    
    # Sign the payload
    signature = private_key.sign(
        payload_json.encode('utf-8'),
        ec.ECDSA(hashes.SHA256())
    )
    
    return base64.b64encode(signature).decode('utf-8')

def get_public_key_jwk(public_key: ec.EllipticCurvePublicKey) -> dict:
    """
    Export public key as JWK for AI agent verification.
    """
    # Implementation would export EC public key in JWK format
    pass
```

### 4.4 Signature Verification (AI Agent / MCP Client Side - Python Example)

```python
import json
import base64
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization

def verify_event_signature(payload_dict: dict, signature_b64: str, public_key: ec.EllipticCurvePublicKey) -> bool:
    """
    Verify an event payload signature using ECDSA with P-256 and SHA-256.
    """
    # Serialize payload to canonical JSON
    payload_json = json.dumps(payload_dict, sort_keys=True, separators=(',', ':'))
    
    # Decode signature
    signature = base64.b64decode(signature_b64)
    
    # Verify signature
    try:
        public_key.verify(
            signature,
            payload_json.encode('utf-8'),
            ec.ECDSA(hashes.SHA256())
        )
        return True
    except Exception:
        return False
```

---

## 5. Platform-Specific Implementation Considerations

### 5.1 Sentry
- **Current State:** Sentry DSNs are public and unauthenticated for client-side telemetry.
- **Recommended Approach:** Implement a separate "AI-Ready Events" endpoint or MCP server extension that only serves events from authenticated, internal ingestion pipelines. Sign these events with platform private keys.
- **Key Differentiator:** Clearly distinguish between "public DSN events" (unsigned, unverified) and "internal/authenticated events" (signed, verified).

### 5.2 Datadog
- **Current State:** Datadog has API keys for ingestion, but these are not cryptographically signed per-event.
- **Recommended Approach:** Add cryptographic signatures to event data served via MCP or AI APIs, using Datadog's service account credentials to sign.

### 5.3 Jira / Atlassian
- **Current State:** Jira issues can be created by external users or automated systems.
- **Recommended Approach:** For AI agent consumption, only surface issues that are created or modified by authenticated internal users, and sign the issue data with Atlassian's platform keys.

### 5.4 GitHub / GitLab
- **Current State:** GitHub Actions and CI/CD events are authenticated via tokens, but not cryptographically signed per-event for AI consumption.
- **Recommended Approach:** Implement signed event payloads for webhook events and CI/CD logs that are surfaced to AI coding agents.

---

## 6. MCP Protocol Integration

### 6.1 Extending the MCP Protocol for Provenance

The MCP protocol should be extended to support provenance metadata:

```typescript
interface MCPEvent {
  id: string;
  type: string;
  timestamp: string;
  payload: Record<string, any>;
  provenance?: {
    source_id: string;
    signature: string;
    key_id: string;
    issued_at: string;
    expires_at?: string;
  };
}
```

### 6.2 MCP Server Responsibilities

MCP servers should:
1. **Include provenance metadata** in all events served to AI agents.
2. **Refuse to serve unsigned events** from unauthenticated or externally-writable sources.
3. **Provide key discovery endpoints** for AI clients to fetch verification keys.

### 6.3 MCP Client Responsibilities

MCP clients (AI coding agents) should:
1. **Verify signatures** before passing event data to the LLM reasoning context.
2. **Refuse to execute commands or make decisions** based on unsigned or invalid events.
3. **Log and alert** on signature verification failures.

---

## 7. Migration and Deployment Strategy

### 7.1 Phase 1: Key Generation and Publication
- Generate asymmetric key pairs for event signing.
- Publish public verification keys via `.well-known/ai-signing-keys` endpoint.

### 7.2 Phase 2: Dual-Mode Operation
- Serve both signed and unsigned events during a transition period.
- AI clients can choose to verify signatures if available.

### 7.3 Phase 3: Signature Enforcement
- Require signatures for all events served via MCP or AI APIs.
- Deprecate unsigned event ingestion for AI consumption.

---

## 8. Conclusion

Cryptographic signing of events and data for AI agent consumption is a critical mitigation for Agentjacking and similar MCP injection attacks. By implementing signature generation on the platform side and signature verification on the AI agent/MCP client side, organizations can ensure that AI coding agents only process data from authenticated, verified sources.

This approach shifts the security model from **implicit trust** (trusting all data from an MCP-connected service) to **explicit verification** (validating the provenance and authenticity of each piece of data before processing).

---

## 9. References

- Cloud Security Alliance Research Note: "Agentjacking: MCP Injection Hijacks AI Coding Agents" (2026-06-12)
- Tenet Security Agentjacking Research (June 2026)
- Model Context Protocol (MCP) Specification
- NIST SP 800-57 Part 1: Recommendation for Key Management