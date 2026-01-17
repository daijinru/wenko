## MODIFIED Requirements

### Requirement: Memory Retrieval with Fuzzy Matching

The system SHALL retrieve relevant long-term memories using a multi-stage algorithm that supports fuzzy matching:

1. **Keyword Extraction**: Extract keywords from user message with pronoun normalization
2. **Candidate Recall**:
   - Primary: FTS5 full-text search with normalized keywords
   - Fallback: Substring matching when FTS5 returns insufficient results
3. **Relevance Scoring**: Calculate scores with support for partial matches
4. **Ranking**: Return top-N results sorted by relevance score

The retrieval algorithm SHALL support the following matching modes:
- **Exact match**: Keyword fully contained in memory key/value (score: 1.0)
- **Normalized match**: Keyword matches after pronoun normalization (score: 1.0)
- **Substring match**: Keyword is a substring of memory content (score: 0.7)
- **Partial match**: Part of keyword matches memory content (score: 0.3)

#### Scenario: Pronoun-normalized matching
- **GIVEN** a memory entry with key "你喜欢的颜色" and value "蓝色"
- **WHEN** user asks "我喜欢的颜色是什么"
- **THEN** the memory entry SHALL be retrieved with high relevance score

#### Scenario: Substring matching fallback
- **GIVEN** a memory entry with key "你喜欢的颜色" and value "蓝色"
- **WHEN** user asks about "颜色"
- **THEN** the memory entry SHALL be retrieved as a candidate via substring matching

#### Scenario: Partial match scoring
- **GIVEN** a memory entry with key "编程语言偏好" and value "Python"
- **WHEN** user asks about "编程"
- **THEN** the memory entry SHALL receive a partial match score (< 1.0)

## ADDED Requirements

### Requirement: Pronoun Normalization

The system SHALL normalize personal pronouns during memory retrieval to improve matching accuracy.

The normalization SHALL map the following pronouns to a neutral form:
- "你" → normalized form
- "我" → normalized form
- "您" → normalized form
- "你的" → normalized form
- "我的" → normalized form

#### Scenario: First-person to second-person equivalence
- **WHEN** memory is stored with key containing "你"
- **AND** user query contains "我" in equivalent position
- **THEN** the query SHALL match the memory after normalization

#### Scenario: Formal pronoun handling
- **WHEN** memory is stored with key containing "您"
- **AND** user query contains "你"
- **THEN** the query SHALL match the memory after normalization

### Requirement: HITL Form Data Persistence to Working Memory

The system SHALL persist HITL form submission data to the session's working memory for context continuity.

When a user submits an HITL form:
1. The form data SHALL be stored in `working_memory.context_variables`
2. The data SHALL be keyed by the form title for identification
3. The data SHALL include a timestamp for ordering
4. The data SHALL remain accessible for the duration of the session

#### Scenario: Form data available in continuation
- **GIVEN** user submits an HITL form titled "行程安排" with fields {destination: "北京", date: "周末"}
- **WHEN** the AI generates a continuation response
- **THEN** the working memory SHALL contain the form data under key "hitl_行程安排"
- **AND** the continuation prompt SHALL include this context

#### Scenario: Multiple form submissions
- **GIVEN** user submits form "偏好设置" with {theme: "dark"}
- **AND** user later submits form "行程安排" with {destination: "上海"}
- **WHEN** building the next response context
- **THEN** both form submissions SHALL be available in working memory

### Requirement: Working Memory Context Size Limit

The system SHALL enforce a maximum size limit on `working_memory.context_variables` to prevent unbounded growth.

#### Scenario: Context size within limit
- **WHEN** adding new context data
- **AND** total context size is below the configured limit
- **THEN** the data SHALL be stored successfully

#### Scenario: Context size exceeds limit
- **WHEN** adding new context data would exceed the size limit
- **THEN** the system SHALL either:
  - Reject the addition with an error, OR
  - Remove oldest context entries to make room (LRU eviction)
