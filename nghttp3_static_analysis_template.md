# nghttp3 QPACK Static Analysis Template

## 🔍 **Analysis Methodology**

### **Target Files to Review**
1. `lib/nghttp3_qpack.c` - Main QPACK implementation
2. `lib/nghttp3_qpack_decoder.c` - Decoder logic
3. `lib/nghttp3_qpack_encoder.c` - Encoder logic  
4. `lib/nghttp3_qpack.h` - Header definitions
5. `lib/nghttp3_qpack_dtable.h` - Dynamic table implementation

### **Key Questions to Answer**

#### **1. Ring Buffer Implementation**
```c
// Look for structures like this:
typedef struct {
    uint8_t *buf;       // Buffer pointer
    size_t  capacity;   // Total capacity
    size_t  used;       // Bytes used
    size_t  start;      // Start offset
    size_t  end;        // End offset
} nghttp3_ringbuf;
```

**Check for:**
- Wrap-around/truncated buffer layout
- Power-of-2 capacity sizing
- Offset calculations using masking

#### **2. Resize Logic Patterns**
```c
// Look for resize functions:
static int nghttp3_ringbuf_resize(..., size_t new_capacity) {
    // Allocate new buffer
    uint8_t *new_buf = malloc(new_capacity);
    
    // Copy data from old to new buffer
    // CHECK: 4-branch logic based on truncation patterns
    // CHECK: Capacity variable usage in calculations
}
```

**Vulnerability Indicators:**
- ❌ Using `new_capacity` instead of `old_capacity` in any branch
- ❌ Inconsistent offset calculations between branches
- ❌ Missing boundary checks on copy lengths
- ❌ Size_t overflow/underflow risks

#### **3. QPACK Dynamic Table Management**
```c
// Look for QPACK table operations:
int nghttp3_qpack_set_dynamic_table_capacity(..., size_t capacity);
int nghttp3_qpack_insert(..., ...);
void nghttp3_qpack_evict(...);
```

**Check for:**
- Capacity validation logic
- Table resizing mechanics
- Memory safety checks

---

## 🔬 **Step-by-Step Analysis Procedure**

### **Step 1: Extract Source Code**

**Methods:**
1. **GitHub API** (preferred):
   ```bash
   curl https://api.github.com/repos/nghttp2/nghttp3/contents/lib/nghttp3_qpack.c
   ```

2. **Raw GitHub URL**:
   ```bash
   curl -L https://raw.githubusercontent.com/nghttp2/nghttp3/master/lib/nghttp3_qpack.c
   ```

3. **Git Clone** (if repository accessible):
   ```bash
   git clone https://github.com/nghttp2/nghttp3.git
   ```

### **Step 2: Search for Vulnerable Patterns**

**grep commands to run:**

```bash
# Find all capacity comparisons
grep -n "capacity" lib/nghttp3_qpack.c | head -50

# Find resize functions
grep -n "resize" lib/nghttp3_qpack.c

# Find memory copies
grep -n "memcpy\|memmove" lib/nghttp3_qpack.c

# Find truncation/wrap-around logic
grep -n "trunc\|wrap\|offset" lib/nghttp3_qpack.c

# Find conditional branches with capacity checks
grep -n "if.*capacity" lib/nghttp3_qpack.c

# Find mathematical operations on capacities
grep -n "capacity.*[+\-*/]" lib/nghttp3_qpack.c
```

### **Step 3: Manual Code Review**

**Focus areas:**

1. **Ring buffer resize implementation**
   - Locate the resize function
   - Map all 4 branches (continuous, truncated, etc.)
   - Trace variable usage in each branch
   - Identify capacity variable mixing

2. **QPACK instruction processing**
   - SET_DYNAMIC_TABLE_CAPACITY handler
   - INSERT operations
   - Capacity change sequences

3. **Memory safety checks**
   - Array bounds validation
   - Integer overflow protection
   - Null pointer checks

### **Step 4: Comparative Analysis**

**Compare with XQUIC:**
```c
// XQUIC buggy code (confirmed vulnerable):
} else {
    size_t new_sz1 = mcap - soffset_new;
    size_t ori_sz1 = mcap - soffset_ori;  // BUG: uses mcap (new cap)
    // ...
}
```

**Check nghttp3 for similar pattern:**
- Look for `new_cap - soffset` pattern
- Verify old capacity is used where appropriate
- Check all branches use consistent capacity variables

---

## 🎯 **Specific Code Patterns to Hunt**

### **Pattern A: Capacity Variable Mix-up**
```c
// VULNERABLE PATTERN (XQUIC style)
size_t old_bytes_to_copy = new_capacity - old_offset;
// Should be:
size_t old_bytes_to_copy = old_capacity - old_offset;
```

### **Pattern B: Inconsistent Offset Calculations**
```c
// VULNERABLE PATTERN
if (both_truncated) {
    size_t first_block = new_cap - new_start;
    size_t second_block = new_cap - old_start;  // Should use old_cap
}
```

### **Pattern C: Underflow in Size Calculations**
```c
// VULNERABLE PATTERN
size_t tail_copy = used - new_block_size;  // If used < new_block_size, underflow
// Should have:
if (used >= new_block_size) {
    size_t tail_copy = used - new_block_size;
}
```

---

## 📋 **Analysis Checklist**

### **File: nghttp3_qpack.c**
- [ ] Locate ring buffer struct definition
- [ ] Find resize function implementation
- [ ] Identify truncation branch logic
- [ ] Map capacity variable usage
- [ ] Check for FORTIFY_SOURCE usage
- [ ] Review error handling paths

### **File: nghttp3_qpack_decoder.c**
- [ ] QPACK instruction parsing
- [ ] Capacity change handling
- [ ] Table size validation
- [ ] Memory allocation checks

### **File: nghttp3_qpack_encoder.c**
- [ ] Dynamic table management
- [ ] Header insertion logic
- [ ] Capacity resize triggers
- [ ] Boundary condition checks

---

## 🛠️ **Automated Analysis Tools**

### **1. Static Analysis with Semgrep**
```yaml
# semgrep.yaml for nghttp3
rules:
  - id: quic-xring-similar-pattern
    patterns:
      - pattern: |-
          $SIZE1 = $NEW_CAP - $OFFSET;
          ...
          $SIZE2 = $OLD_CAP - $OFFSET;
    message: "Potential capacity variable mix-up in ring buffer resize"
    languages: [c]
    severity: ERROR
```

### **2. Fuzzing Test Case**
```c
// Test payload for nghttp3
// 260 bytes: XRING sequence
uint8_t payload[] = {
    // SET_DYNAMIC_TABLE_CAPACITY = 64
    0x20, 0x40,
    // 61 insert operations (1-byte name/value)
    // 1 insert operation (5-byte name/value)
    // SET_DYNAMIC_TABLE_CAPACITY = 65
};
```

### **3. Memory Analysis with ASAN**
```bash
# Compile with AddressSanitizer
gcc -fsanitize=address -g -O1 nghttp3_qpack.c -o test_qpack
./test_qpack  # Run with XRING payload
```

---

## 📊 **Analysis Results Template**

### **Findings Summary**
| File | Function | Pattern Found | Risk Level | Status |
|------|----------|---------------|------------|--------|
| nghttp3_qpack.c | ringbuf_resize | Mixed capacity usage | 🔴 High | ❌ Vulnerable |
| nghttp3_qpack.c | qpack_set_capacity | Missing validation | ⚠️ Medium | 🟡 Needs review |
| nghttp3_qpack.c | qpack_insert | Safe (bounds checked) | 🟢 Low | ✅ Safe |

### **Code Examples**
```c
// Vulnerable code snippet
// File: lib/nghttp3_qpack.c, line XXX
size_t ori_sz1 = new_cap - soffset_ori;  // ❌ Should use old_cap
// Impact: Potential heap overflow
// Fix: Replace with rmem->capacity
```

---

## 🚨 **Immediate Actions if Vulnerability Found**

1. **Confirm with PoC** - Generate and test XRING payload
2. **Document the bug** - Create detailed analysis report
3. **Develop patch** - Submit fix to nghttp3 maintainers
4. **Coordinate disclosure** - Follow responsible disclosure process
5. **Update security framework** - Add detection signature

---

## 🔗 **Reference: XQUIC Bug Pattern**

```c
// XQUIC xqc_ring_mem.c - Line 13 (problematic branch)
} else {
    /* bytes are both truncated in new and original buffer */
    size_t new_sz1 = mcap - soffset_new;    /* size of first block in new buffer */
    size_t ori_sz1 = mcap - soffset_ori;    /* BUG: should use rmem->capacity */
    if (new_sz1 >= ori_sz1) {
        xqc_memcpy(buf + soffset_new, rmem->buf + soffset_ori, ori_sz1);
        xqc_memcpy(buf + soffset_new + ori_sz1, rmem->buf, new_sz1 - ori_sz1);
        xqc_memcpy(buf, rmem->buf + new_sz1 - ori_sz1, rmem->used - new_sz1);
    }
}
```

**Key Indicator:** `size_t ori_sz1 = mcap - soffset_ori;` uses `mcap` (new capacity) instead of `rmem->capacity` (old capacity).

---

*Template generated: July 10, 2026 | For systematic analysis of nghttp3 QPACK implementation*
