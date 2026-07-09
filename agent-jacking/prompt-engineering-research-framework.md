# Prompt Engineering Research Framework

## Research Setup

### Environment
- **Model:** [specify model being tested]
- **Provider:** [API provider]
- **Date started:** [date]
- **Observer:** [researcher]

### Response Rating Scale

| Score | Description |
|-------|-------------|
| 0 | Completely ignored/poor response |
| 1 | Minimal impact |
| 2 | Noticeable effect |
| 3 | Strong effect |
| 4 | Near-perfect effect |

---

## Technique Categories

### 1. Baseline Controls

**What:** Standard prompts to establish baseline performance

**Example:**
```
[Simple, direct question]
```

**Track:**
- Response accuracy
- Response completeness
- Response tone
- Response length
- Time to complete

---

### 2. Chain of Thought / Explanation

**What:** Forcing the model to reason step-by-step

**Variants to test:**
- "Think through this carefully"
- "Explain your reasoning process"
- "First identify considerations, then work through each"
- "Walk me through your thinking"
- "Show your work"

**Measurement:**
- Accuracy improvement vs baseline
- Correct reasoning paths vs wrong paths that reach right answer
- Verbosity (how long does it get?)

---

### 3. Role/Persona Prompting

**What:** Assigning different identities

**Variants to test:**
- "You are a [role]"
- "As an experienced [professional]..."
- "Imagine you've worked as [role] for X years"
- "You're a [level: junior vs senior]"

**Track:**
- Tone changes
- Depth of answer
- Vocabulary changes
- Confidence level changes

---

### 4. Few-Shot / Example Prompting

**What:** Providing examples of desired output

**Variants to test:**
- Number of examples (1, 2, 3, 5, 10)
- Example quality (mix good/bad examples)
- Example relevance (directly related vs tangentially related)
- Include instructions alongside examples

**Measurement:**
- Adherence to example format
- Accuracy of response compared to example quality

---

### 5. Constraint Prompting

**What:** Adding requirements that force different output

**Variants to test:**
- Length constraints: "in exactly 50 words"
- Format constraints: "as a table", "as JSON"
- Style constraints: "explain it to a 5 year old", "in academic style"
- Point of view: "from the perspective of..."
- Perspective constraints: "consider both sides"

**Track:**
- Adherence to constraint
- Quality trade-off

---

### 6. Multi-Step / Iterative Prompting

**What:** Breaking complex tasks into dialogue

**Approaches:**
- Sequential: Each prompt builds on previous
- Refinement: "That's helpful, but expand on X"
- Challenge: "But what about this counterpoint?"
- Self-correction: "Reconsider your answer"

**Measurement:**
- Quality progression
- Does quality actually improve or just sound like it does?
- Point of diminishing returns

---

### 7. Context Window Manipulation

**What:** Testing how context volume affects responses

**Variants:**
- Minimal context
- Moderate context
- Extensive context
- Redundant information
- Conflicting information
- Hidden information (buried in noise)

**Track:**
- Information retrieval accuracy
- Response relevance
- Attention focus

---

### 8. Token Probability Games (if API available)

**What:** Using token probabilities to understand model behavior

**Methods:**
- Check top-k token probabilities
- Compare probability distributions across similar prompts
- Look for tokens with high probability that weren't selected

**Measurement:**
- How predictable is model behavior?
- Are near-selected tokens meaningful?

---

## Results Template

### Test Session Log

```markdown
## Session #[number]
Date: [date]
Model: [model name]
Temperature: [if adjustable]

### Test #[test number]
Technique: [technique name]
Goal: [what we're testing]

#### Prompt:
[exact prompt used]

#### Response:
[exact response received]

#### Analysis:
- Effectiveness (0-4): 
- Quality vs baseline: [better/same/worse]
- Notable observations:
- Reproducibility: [tried X times, worked Y times]
```

---

## Suggested Testing Order

1. **Phase 1:** Establish baselines (10-15 standard prompts)
2. **Phase 2:** Test techniques individually (one variable at a time)
3. **Phase 3:** Test technique combinations (interactions)
4. **Phase 4:** Stress test with complex/edge cases
5. **Phase 5:** Compare across different models if possible

---

## Important Research Notes

### Validating Quality

Don't just measure if it *looks* right. Actually verify answers when possible:
- Use questions with known answers
- Have human reviewers score independently
- Check against trusted sources

### Statistical Significance

- Test each technique at least 5 times
- Randomize test order
- Record failed tests, not just successes

### Documenting Failures

*Especially important:* Record when techniques fail:
- The prompt that failed
- The response received
- Your theory for why it failed
- Hypothesis for what might have worked

---

## Aggregated Data Structure

```json
{
  "session_id": 1,
  "date": "2025-01-01",
  "model": "model-name",
  "test_results": [
    {
      "test_id": 1,
      "technique": "baseline",
      "prompt_category": "factual",
      "score_effectiveness": 3,
      "quality_vs_baseline": "reference",
      "time_ms": 234,
      "token_count": 156,
      "notes": ""
    }
  ]
}
```

---

*This framework is a starting point. Adapt it to your specific research questions.*
