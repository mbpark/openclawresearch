# VLMGuard & SmoothVLM Defense Mechanisms: Research & Prototyping Report
**Date:** July 1, 2026  
**Focus:** Visual Prompt Injection Defense, Input Smoothing, Unlabeled Data Maliciousness Estimation, SVD-based Detection  

---

## 1. Executive Summary

This report synthesizes research and prototyping conducted on July 1, 2026, focusing on **VLMGuard** and **SmoothVLM**—two distinct defense mechanisms developed to address the critical vulnerability of Vision-Language Models (VLMs) to visual prompt injection attacks.

These attacks involve embedding malicious instructions within images or multimodal inputs to manipulate a VLM's behavior and generate unintended or harmful outputs (e.g., the "InkJect" vulnerability).

### Key Defense Mechanisms:

| Defense | Core Technique | Approach | Effectiveness |
|---------|----------------|----------|---------------|
| **SmoothVLM** | Input Smoothing (Randomized Smoothing) | Subtly perturb images with pixel-wise randomization to reduce adversarial patch effectiveness | Reduces patched visual prompt injector success rate to 0%-5.0%; limited against steganographic/typographic variants |
| **VLMGuard** | Unlabeled Data Maliciousness Estimation (SVD-based) | Uses Singular Value Decomposition (SVD) to derive a "maliciousness estimation score" from unlabeled training data | Addresses scarcity of labeled malicious data; practical for real-world VLM applications |
| **VLMGuard-R1** | Reasoning-Driven Prompt Rewriter | Proactive safety alignment through a reasoning-driven prompt rewriter that refines user inputs across modalities | Extension of VLMGuard for cross-modal input refinement |

---

## 2. SmoothVLM: Input Smoothing Defense

### 2.1 Core Concept
**SmoothVLM** is a novel framework designed to protect VLMs specifically against **"patched visual prompt injectors."** It operates by employing **input smoothing** techniques, particularly **randomized smoothing**.

### 2.2 How Randomized Smoothing Works
The defense mechanism leverages the insight that **adversarial patches**, when subtly perturbed with **pixel-wise randomization**, become significantly less effective. 

When an image containing an adversarial patch is passed through SmoothVLM's input smoothing layer:
1. **Pixel-wise noise is added** to the input image
2. The adversarial patch's precise pixel patterns are disrupted
3. The VLM receives a "smoothed" version of the image that retains benign semantic content but loses the precise adversarial perturbations
4. The VLM's ability to process benign images is largely preserved

### 2.3 Effectiveness
- **Reduces attack success rate** of patched visual prompt injectors on leading VLMs to a range between **0% and 5.0%**
- **Preserves model's ability** to process benign images
- **Limitation**: Effectiveness against other types of visual prompt injections, such as **steganographic and typographic variants**, is limited (these don't rely on pixel-level adversarial patches)

---

## 3. VLMGuard: Unlabeled Data Maliciousness Estimation

### 3.1 Core Concept
**VLMGuard**, published in October 2024, offers a different approach to defending VLMs against malicious prompts. Unlike methods that require extensive labeled adversarial training examples, **VLMGuard utilizes *unlabeled training data*.**

### 3.2 Maliciousness Estimation Score via SVD
VLMGuard introduces a **"maliciousness estimation score"** derived from techniques like **Singular Value Decomposition (SVD)** to differentiate between benign and malicious inputs within unlabeled data.

#### How SVD-based Maliciousness Estimation Works:
1. **Input Representation**: Multimodal inputs (images + text) are converted into vector representations using the VLM's embedding layers
2. **SVD Decomposition**: The matrix of input representations is decomposed using Singular Value Decomposition:
   - `A = U × Σ × V^T`
   - `U`: Left singular vectors (input patterns)
   - `Σ`: Singular values (importance of each pattern)
   - `V^T`: Right singular vectors (feature dimensions)
3. **Maliciousness Score Calculation**: Inputs with anomalous singular value distributions or unusual pattern structures are assigned higher "maliciousness estimation scores"
4. **Threshold-Based Classification**: Inputs exceeding a certain maliciousness score threshold are flagged or rejected before reaching the VLM

### 3.3 Advantages of Unlabeled Data Approach
- **Addresses the challenge of scarcity in labeled malicious data**: It is difficult to collect and label comprehensive datasets of all possible visual prompt injection attacks
- **Enhances practicality and flexibility**: Can be deployed in real-world VLM applications without requiring extensive labeled adversarial training examples
- **Adaptable to novel attacks**: Can detect previously unseen injection patterns based on structural anomalies in the input representation

---

## 4. VLMGuard-R1: Reasoning-Driven Prompt Rewriter

### 4.1 Core Concept
An extension of VLMGuard, **VLMGuard-R1**, focuses on **proactive safety alignment** through a **reasoning-driven prompt rewriter** that refines user inputs across modalities.

### 4.2 How VLMGuard-R1 Works
1. **Input Reception**: User input (image + text) is received
2. **Reasoning Analysis**: A reasoning engine analyzes the input for potential malicious patterns, role confusion indicators, or VPI patterns
3. **Prompt Rewriting**: The rewriter refines the user input, removing or neutralizing potentially harmful instructions while preserving benign intent
4. **Safe Input to VLM**: The rewritten, safe input is passed to the primary VLM for task execution

### 4.3 Advantages
- **Proactive safety alignment**: Rather than just detecting malicious input, it actively rewrites and sanitizes it
- **Cross-modal refinement**: Handles both visual and textual inputs, addressing multimodal prompt injection vectors

---

## 5. Prototype Implementations

### 5.1 Gatekeeper LLM Architecture Prototype
**File:** `gatekeeper_llm_architecture.py`

A prototype of the **Gatekeeper LLM Architecture** was implemented, featuring:
- Pattern-based detection for role confusion attacks (`DEBUG_MODE`, `SYSTEM_UPDATE`, `MODERATOR_OVERRIDE`, fake `<thinking>` blocks)
- System prompt leak pattern detection
- Social engineering pattern recognition
- Dual-mode operation: **BLOCKED** (for malicious inputs) or **PASSED** (for safe inputs to Primary LLM)

**Test Results:**
- ✅ Safe input: PASSED to Primary LLM
- ✅ Role Confusion Attack (DEBUG_MODE): BLOCKED
- ✅ CoT Forgery Attack: BLOCKED
- ✅ Security Thought Reinforcement Bypass (SYSTEM_UPDATE): BLOCKED
- ✅ Gatekeeper Bypass Simulation (MODERATOR_OVERRIDE): BLOCKED

### 5.2 VLMGuard SVD-Based Maliciousness Estimation Prototype
**File:** `vlmguard_svd_prototype.py`

A simplified prototype of VLMGuard's **SVD-based maliciousness estimation score** was implemented using:
- TF-IDF vectorization for text representation
- TruncatedSVD for dimensionality reduction and anomaly detection
- Reconstruction error and component variance for maliciousness scoring

**Note on Prototype Results:** The simplified TF-IDF + SVD prototype showed that detecting role confusion and social engineering patterns requires actual VLM embedding layers rather than basic TF-IDF vectorization. A full VLMGuard implementation would use the VLM's actual multimodal embedding space to calculate meaningful singular value distributions and reconstruction errors.

---

## 6. Comparative Analysis: SmoothVLM vs. VLMGuard vs. Gatekeeper Architecture

| Feature | SmoothVLM | VLMGuard | Gatekeeper LLM Architecture |
|---------|-----------|----------|----------------------------|
| **Primary Target** | Patched visual prompt injectors | Malicious prompts (text + image) | Role confusion, social engineering, VPI |
| **Core Technique** | Input smoothing (randomized pixel noise) | SVD-based maliciousness estimation from unlabeled data | Pattern-based heuristic detection + dual-LLM routing |
| **Training Data Required** | None (unsupervised smoothing) | Unlabeled data (no labeled adversarial examples needed) | None (heuristic patterns) |
| **Effectiveness Against Patches** | 0%-5.0% success rate | Not specifically designed for patches | Depends on pattern coverage |
| **Effectiveness Against Typographic/Steganographic** | Limited | High (unlabeled SVD detection adapts to novel patterns) | High (if patterns are defined) |
| **Proactive vs. Reactive** | Reactive (smoothing before VLM processing) | Reactive (classification before VLM processing) | Reactive (pattern matching before Primary LLM) |
| **Architecture** | Input pre-processing layer | Classification layer | Dual-LLM routing architecture |

---

## 7. Defensive Recommendations

Based on the research and prototyping, the following defensive strategies are recommended for VLM security:

### 7.1 Layered Defense Approach
Implement a **multi-layered defense architecture** that combines:
1. **SmoothVLM-style input smoothing** for adversarial patch detection at the image processing layer
2. **VLMGuard-style SVD-based maliciousness estimation** for detecting novel or unseen injection patterns in the embedding space
3. **Gatekeeper LLM architecture** for role confusion, social engineering, and system prompt leak detection

### 7.2 Adopt VLMGuard-R1 for Proactive Safety Alignment
- Implement **reasoning-driven prompt rewriting** to actively sanitize and refine user inputs across modalities
- Move from reactive detection to **proactive safety alignment**

### 7.3 Physical Role Separation + Gatekeeper Routing
- Combine the **Gatekeeper LLM architecture** with **physical role separation** (not just formatting tags)
- Use a low-privilege gatekeeper model to scrutinize input for role confusion patterns before it reaches the high-privilege primary model

### 7.4 Continuous Learning with Unlabeled Data
- Leverage **unlabeled data approaches** like VLMGuard's SVD-based estimation to adapt to novel attack patterns without requiring extensive labeled adversarial training examples

---

## 8. Files Generated/Modified

- `gatekeeper_llm_architecture.py` - Gatekeeper LLM Architecture prototype
- `vlmguard_svd_prototype.py` - VLMGuard SVD-based maliciousness estimation prototype
- `role_confusion_test_cases.json` - Role confusion test case definitions
- `role_confusion_test_runner.py` - Role confusion test runner for Anthropic and Gemini APIs
- `role_confusion_research_report.md` - Role confusion research report
- `comprehensive_vpi_multimodal_research_report.md` - Comprehensive VPI & multimodal research report
- `vpi_research_slides.md` - Slides presentation (Marp format)
- `VLMGuard_SmoothVLM_Research_Report.md` - This report
