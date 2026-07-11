# XRING Vulnerability: Deep Dive Analysis

## 🔬 **PoC Code Analysis**

### **Attack Vector Breakdown**

The PoC (`remote-client/main.go`) reveals the exact QPACK instruction sequence needed to trigger the crash:

```go
func buildPayload() []byte {
    var buf []byte
    buf = append(buf, prefixedInt(64, 5, 0x20)...)  // Set Dynamic Table Capacity = 64
    for range 61 {
        buf = append(buf, insert("x", "y")...)       // Insert 61 entries (x→y)
    }
    buf = append(buf, insert("AAAAA", "BBBBB")...)   // Insert final entry (AAAAA→BBBBB)
    buf = append(buf, prefixedInt(65, 5, 0x20)...)  // Set Dynamic Table Capacity = 65
    return buf
}
```

### **QPACK Frame Format**

**Set Dynamic Table Capacity (0x20 prefix):**
```
| 0x20 | 64 (encoded) |
```

**Insert with Name/Value (0x40 prefix for name, 0x00 for value length):**
```
0x40 | name_len | name | value_len | value
```

**Key Insight:** The payload is **260 bytes** total - just enough to create a specific memory layout in the ring buffer.

---

## 🧠 **Memory Layout Construction**

### **Initial State (64-byte table)**
1. **Start with empty table**
2. **Set capacity to 64 bytes** (allocates 64-byte ring buffer)
3. **Insert 61 entries** of 1-byte name + 1-byte value each
   - Each `insert("x", "y")` = 1 byte name + 1 byte value + 2 length bytes = 4 bytes actual content
   - But QPACK stores in ring buffer with metadata
4. **Final insert** `insert("AAAAA", "BBBBB")` = 5-byte name + 5-byte value = 10 bytes

**Result:** The ring buffer becomes **truncated** (wrapped layout):
- Data doesn't fit linearly; it wraps around the buffer boundary
- `sidx` (start index) and `eidx` (end index) create a wrap pattern

### **Attack Trigger**
**Resize to 65 bytes:**
- Allocates 65-byte buffer (power of 2 = 128 bytes)
- **Both old and new buffers are truncated** (wrapped)
- **Problematic branch** executes:

```c
if (new_sz1 >= ori_sz1) {
    xqc_memcpy(buf + soffset_new, rmem->buf + soffset_ori, ori_sz1);
    xqc_memcpy(buf + soffset_new + ori_sz1, rmem->buf, new_sz1 - ori_sz1);
    xqc_memcpy(buf, rmem->buf + new_sz1 - ori_sz1, rmem->used - new_sz1);  // BUG HERE!
}
```

### **The Bug (Line 13 in problematic branch)**
```c
xqc_memcpy(buf, rmem->buf + new_sz1 - ori_sz1, rmem->used - new_sz1);
```

**Correct logic should be:**
```c
xqc_memcpy(buf, rmem->buf + new_sz1 - ori_sz1, rmem->used - new_sz1);
```

Wait - that's the same! Let me re-analyze...

Actually, the bug is in the **third memcpy's source offset**. Let's trace:

**Expected:** The tail bytes are at `rmem->buf + (rmem->used - new_sz1)`
**But:** `new_sz1 - ori_sz1` is calculated **against the NEW buffer capacity** instead of the OLD buffer capacity!

---

## 🔍 **Detailed Bug Analysis**

### **Variable Meanings**

| Variable | Meaning |
|----------|---------|
| `mcap` | New buffer capacity (rounded to power of 2) |
| `soffset_new` | Start offset in new buffer (sidx & mask) |
| `soffset_ori` | Start offset in old buffer (sidx & old_mask) |
| `new_sz1` | `mcap - soffset_new` - size of first block in NEW buffer |
| `ori_sz1` | `mcap - soffset_ori` - **BUG: should be `rmem->capacity - soffset_ori`** |

### **The Flaw**

**Line:** `size_t ori_sz1 = mcap - soffset_ori;`

**Should be:** `size_t ori_sz1 = rmem->capacity - soffset_ori;`

**Why this matters:**
- `mcap` is the **new** (larger) buffer capacity
- `rmem->capacity` is the **old** (smaller) buffer capacity
- When computing how many bytes to copy from the **old buffer's tail**, we should use the **old buffer's capacity**

### **Example Calculation**

Assume:
- Old capacity: 64 bytes
- New capacity: 65 bytes (rounded to 128)
- `soffset_new` = 63 (start at end of new buffer)
- `soffset_ori` = 63 (start at end of old buffer)

```
new_sz1 = 128 - 63 = 65
ori_sz1 = 128 - 63 = 65  // WRONG! Should be 64 - 63 = 1
```

**Then:**
```
xqc_memcpy(buf + soffset_new, rmem->buf + soffset_ori, ori_sz1);
// Copy 65 bytes from old to new (but old buffer only has 1 byte valid!)

xqc_memcpy(buf + soffset_new + ori_sz1, rmem->buf, new_sz1 - ori_sz1);
// new_sz1 - ori_sz1 = 65 - 65 = 0 (no copy)

xqc_memcpy(buf, rmem->buf + new_sz1 - ori_sz1, rmem->used - new_sz1);
// new_sz1 - ori_sz1 = 0, so source is rmem->buf + 0
// But this should be copying tail bytes!
```

---

## ⚡ **Exploitation Mechanics**

### **Heap Overflow Chain**

1. **Over-count** `ori_sz1` to 65 instead of 1
2. **First `memcpy`** copies 65 bytes from old to new buffer
   - But old buffer only has 1 valid byte at that offset
   - **64-byte out-of-bounds read** from old buffer (caught by `_FORTIFY_SOURCE`)
3. **Second `memcpy`** copies 0 bytes (new_sz1 - ori_sz1 = 0)
4. **Third `memcpy`**:
   - Source: `rmem->buf + new_sz1 - ori_sz1` = `rmem->buf + 0`
   - Length: `rmem->used - new_sz1` = (total used) - 65
   - If total used < 65, this length is a **huge unsigned underflow**
   - **Heap overflow** when writing to new buffer

### **Attack Reliability**

**Why this is exploitable:**
- **Deterministic** - specific QPACK instruction sequence always triggers
- **Spec-compliant** - uses valid HTTP/3 protocol frames
- **Minimal payload** - 260 bytes fits in single packet
- **No authentication** - any client can send
- **No malformed packets** - evades basic protocol validation

---

## 🛡️ **Detection & Defense Strategies**

### **Network Detection**

**Signature for XRING attack:**
```
QPACK Encoder Stream (stream type 0x02)
Contains:
1. Set Dynamic Table Capacity = 64
2. 61+ Insert operations with name_len=1, value_len=1
3. One Insert operation with name_len=5, value_len=5
4. Set Dynamic Table Capacity = 65
```

**Pattern matching:**
- Look for **rapid table capacity increases** (64→65)
- Monitor for **exactly 61 small inserts** before final capacity change
- Track **QPACK encoder stream traffic patterns**

### **Runtime Protection**

**Immediate mitigations:**
1. **Disable QPACK dynamic table:**
   ```
   SETTINGS_QPACK_MAX_TABLE_CAPACITY = 0
   ```
2. **Fallback to HTTP/2** for critical services
3. **Deploy Web Application Firewall (WAF)** with HTTP/3 inspection

### **Long-term Fixes**

**Patch requirements:**
```c
// In xqc_ring_mem_resize()
size_t ori_sz1 = rmem->capacity - soffset_ori;  // Use OLD capacity
```

**Testing:**
- **Fuzz QPACK instruction sequences**
- **Test edge cases** with truncated ring buffers
- **Validate memory safety** with ASAN/LSAN

---

## 📊 **Impact Assessment**

### **Attack Surface**
- **Protocols:** HTTP/3 over QUIC
- **Components:** XQUIC library, Tengine web server
- **Network Layer:** UDP port 443 (typically)
- **Authentication:** None required (unauthenticated remote)

### **CVSS Estimation**
- **Base Score:** 7.5 (High)
- **Attack Vector:** Network (AV:N)
- **Attack Complexity:** Low (AC:L)
- **Privileges Required:** None (PR:N)
- **User Interaction:** None (UI:N)
- **Scope:** Changed (S:C)
- **Confidentiality:** None (C:N)
- **Integrity:** None (I:N)
- **Availability:** High (A:H)

### **Real-World Risk**
- **High** due to public PoC
- **Critical infrastructure** at risk (Alibaba Cloud, Taobao, Alipay)
- **CDN/edge services** widely affected
- **HTTP/3 adoption** increasing

---

## 🔗 **Relation to Previous Research**

### **Similar Vulnerabilities**
1. **HTTP/2 Bomb (June 2026):** Remote DoS via legitimate HTTP/2 frames
2. **NGINX HTTP/3 UAF (CVE-2026-42530):** Same QPACK encoder stream attack surface
3. **Buffer overflow patterns:** Found across multiple HTTP implementations

### **Research Implications**
- **HTTP/3 implementations** still have fundamental memory safety issues
- **Protocol complexity** creates exploitation opportunities
- **Standard validation** doesn't catch logical/memory bugs
- **PoC availability** accelerates attacker tooling

---

## 🧪 **Testing Recommendations**

### **Immediate Actions**
1. **Audit HTTP/3 infrastructure** for XQUIC/Tengine usage
2. **Apply capacity=0 mitigation** on critical systems
3. **Monitor for similar QPACK patterns** in network traffic

### **Research Opportunities**
1. **Test other QUIC stacks** (quiche, nghttp3, litq3) for similar bugs
2. **Develop automated fuzzer** for QPACK instruction sequences
3. **Create protocol-level detection signatures**
4. **Study ring buffer patterns** across memory-safe implementations

---

*Generated: July 10, 2026 | Sources: FoxIO Research, XQUIC GitHub, The Hacker News*
