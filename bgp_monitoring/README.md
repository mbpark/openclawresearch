# BGP Monitoring & Threat Intelligence

## Overview

This directory contains tools for BGP monitoring and threat intelligence integration.

## Components

### 1. `bgp_hijack_monitor_v2.py`
Main BGP hijack detection script using RouteViews data.

**Features:**
- Downloads BGP tables from RouteViews archive
- Detects potential hijacking patterns
- Risk assessment (CRITICAL, HIGH, MEDIUM, MINIMAL)
- RFC1918 private IP filtering

**Output:** `bgp_report_YYYYMMDD_HHMMSS.json`

### 2. `bgp_cross_check.py`
Multi-source cross-validation script.

**Features:**
- Compares RouteViews, RIPE RIS, and BGPView data
- Helps validate BGP events across different feeds
- Generates cross-check reports

### 3. `integrate_threat_intel.py`
Hybrid threat intelligence integration.

**Features:**
- **ASN/Prefix feeds** (Team Cymru style) - matches BGP origin ASNs and prefixes
- **Domain feeds** (alphaMountain style) - maps domains to IPs, checks BGP prefixes
- Cache management (24-hour refresh)
- Combined threat report generation

**Outputs:**
- `cymru_cache.json` - Cached Team Cymru data
- `alphamountain_cache.json` - Cached alphaMountain domains
- `threat_report_YYYYMMDD_HHMMSS.json` - Threat intelligence report

### 4. `generate_security_dashboard.py`
Consolidates BGP monitoring and threat intelligence into a unified dashboard.

**Output:** `security_dashboard_YYYYMMDD_HHMMSS.txt`

## Data Sources

### Available Sources
- ✅ **RouteViews** - Global BGP routing table snapshots
- ✅ **AlphaMountain** - 1,000 malicious domains with risk scores
- ❌ **Team Cymru** - GitHub mirror is currently dead (404)
- ⚠️ **RIPE RIS** - Not available for recent dates in archive
- ❌ **BGPView** - DNS resolution blocked by firewall

### Feed Status

| Source | Type | Status | Notes |
|--------|------|--------|-------|
| RouteViews | BGP Tables | ✅ Active | Local file mode |
| AlphaMountain | Domain Threats | ✅ Active | 1,000 domains |
| Team Cymru | ASN/Prefix | ❌ Inactive | URL dead |
| RIPE RIS | BGP Tables | ⚠️ Partial | Archive gaps |
| BGPView | API | ❌ Blocked | DNS resolution fails |

## Usage

### Run BGP Monitoring
```bash
cd /Users/mitchparker/.openclaw/workspace/research/bgp_monitoring
python3 bgp_hijack_monitor_v2.py
```

### Run Threat Intelligence Integration
```bash
python3 integrate_threat_intel.py
```

### Generate Security Dashboard
```bash
python3 generate_security_dashboard.py
```

## Integration Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Security Monitoring                       │
└─────────────────────────────────────────────────────────────┘
                           │
        ┌──────────────────┴──────────────────┐
        │                                     │
┌───────▼───────┐                   ┌───────▼───────┐
│ BGP Monitoring │                   │ Threat Intel │
└───────┬───────┘                   └───────┬───────┘
        │                                     │
        │ RouteViews                          │ AlphaMountain
        │ (BGP Tables)                        │ (Domain Feeds)
        │                                     │
        │ CIF (Common Information Format)    │ CIF (Common Information Format)
        │                                     │
        └──────────────────┬──────────────────┘
                           │
                    ┌──────▼──────┐
                    │ Dashboard   │
                    │ Combined    │
                    │ View        │
                    └─────────────┘
```

## Output Files

- `bgp_report_*.json` - BGP monitoring results
- `threat_report_*.json` - Threat intelligence matches
- `security_dashboard_*.txt` - Combined security overview
- `bgp_crosscheck_*.json` - Multi-source validation
- `cymru_cache.json` - Cached threat feeds
- `alphamountain_cache.json` - Cached threat feeds

## Notes

1. **Network Restrictions:**
   - RouteViews works in single-file mode (no broker access needed)
   - BGPView API blocked by firewall (DNS resolution fails)
   - AlphaMountain feed accessible via HTTPS

2. **Threat Intelligence Matching:**
   - ASN/Prefix matches work directly with BGP data
   - Domain matches require DNS resolution (may be blocked)
   - Consider adding DNS resolver or using external API

3. **Cache Management:**
   - Threat data cached for 24 hours
   - Expired caches automatically refreshed on next run

## Future Enhancements

1. Add DNS resolution for domain-to-IP mapping
2. Integrate with other threat feeds (CRIF, VirusTotal, etc.)
3. Real-time BGP monitoring with live streams
4. Alerting and notifications
5. SIEM integration

## Related Research

- BGP Hijacking Detection Techniques
- Threat Intelligence Feeds for Security Monitoring
- RouteViews Data Analysis
- BGP Security Standards (RPKI, BGPsec)
