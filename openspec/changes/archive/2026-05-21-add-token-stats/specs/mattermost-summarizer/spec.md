## MODIFIED Requirements

### REQ-011: Metadata
The system SHALL include metadata at the bottom of the output: thread length, token stats, model used, duration.
- The `Tokens:` string SHALL be appended after `Duration` as the final metadata line.
- The system SHALL format the Tokens string exactly as: `Tokens: ↑ input {input} • cache hit {hit}% • reasoning {reasoning} • ↓ output {output} • $ {cost}`
- The `{cost}` SHALL be formatted to 2 decimal places (e.g., `0.00`).
- Token numbers `>= 1000` SHALL be divided by 1000, given two decimal places, and suffixed with `K` (e.g., `35.69K`). Token numbers `< 1000` SHALL be printed as exact integers.
- If `{hit}` evaluates to 0, the `cache hit` segment SHALL be omitted from the output.
- If `{reasoning}` evaluates to 0, the `reasoning` segment SHALL be omitted from the output.

#### Scenario: Metadata with cache hits and reasoning tokens
- **WHEN** the agent returns a summary with 35690 input tokens, 1000 cache read tokens, 653 reasoning tokens, 1820 output tokens, and 0.0042 cost
- **THEN** the metadata string includes `Tokens: ↑ input 35.69K • cache hit 2.73% • reasoning 653 • ↓ output 1.82K • $ 0.00` at the bottom.

#### Scenario: Metadata with zero reasoning and zero cache hit
- **WHEN** the agent returns a summary with 500 input tokens, 0 cache read tokens, 0 reasoning tokens, 500 output tokens, and 0.0001 cost
- **THEN** the metadata string includes `Tokens: ↑ input 500 • ↓ output 500 • $ 0.00` at the bottom.
