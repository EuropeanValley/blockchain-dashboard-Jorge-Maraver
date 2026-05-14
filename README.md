[![Review Assignment Due Date](https://classroom.github.com/assets/deadline-readme-button-22041afd0340ce965d47ae6ef1cefeee28c7c493a6346c4f15d667ab976d596c.svg)](https://classroom.github.com/a/N3kLi3ZO)
[![Open in Visual Studio Code](https://classroom.github.com/assets/open-in-vscode-2e0aaae1b6195c2367325f4f02e2d04e9abb55f0b24a779b69b11b9e10269abc.svg)](https://classroom.github.com/online_ide?assignment_repo_id=23640563&assignment_repo_type=AssignmentRepo)
# Blockchain Dashboard Project


Use this repository to build your blockchain dashboard project.
Update this README every week.


## Student Information


| Field | Value |
|---|---|
| Student Name | Jorge Maraver Pérez |
| GitHub Username | Jorge-Maraver |
| Project Title | Blockchain assignment |
| Chosen AI Approach | Anomaly detector |


## Module Tracking


Use one of these values: `Not started`, `In progress`, `Done`


| Module | What it should include | Status |
|---|---|---|
| M1 | Proof of Work Monitor | Done |
| M2 | Block Header Analyzer | Done |
| M3 | Difficulty History | Done |
| M4 | AI Component | Done |


## Current Progress


Write 3 to 5 short lines about what you have already done.


- 


## Next Step


Write the next small step you will do before the next class.


-


## Main Problem or Blocker


Write here if you are stuck with something.


-


## How to Run


```bash
pip install -r requirements.txt
streamlit run app.py
```


## Project Structure


```text
template-blockchain-dashboard/
|-- README.md
|-- requirements.txt
|-- .gitignore
|-- app.py
|-- api/
|   `-- blockchain_client.py
`-- modules/
    |-- m1_pow_monitor.py
    |-- m2_block_header.py
    |-- m3_difficulty_history.py
    `-- m4_ai_component.py
```


## Documentation Policy

From this point onward, any extra documentation generated for the project should
be added here instead of modifying `README.md`, unless explicitly requested.

## Session 1 - First API Call

Corresponding task: Session 1, Milestone 2 - First API Call.

The project includes a short executable script inside `api/blockchain_client.py`.
When run with:

```powershell
python api\blockchain_client.py
```

it connects to a public Bitcoin API and prints live data from the latest block:

- block height
- block hash
- current mining difficulty
- compact target representation through the `bits` field
- nonce
- number of transactions

The script also includes comments connecting the returned values to the theory:
the leading zero hexadecimal digits in the block hash are visible evidence of
Proof of Work, and the `bits` field is Bitcoin's compact representation of the
target threshold.

## M1 - Proof of Work Monitor

Corresponding task: Required Module M1 - Proof of Work Monitor.

M1 has been implemented in `modules/m1_pow_monitor.py`. It displays live Bitcoin
mining data in the Streamlit dashboard and updates automatically every 60
seconds.

### Implemented Values

The module currently shows:

- latest block height
- current difficulty
- nonce
- number of transactions
- `bits` field
- decoded target threshold
- block hash
- local comparison showing whether `hash < target`
- number of leading zero hexadecimal digits in the block hash
- number of leading zero bits in the block hash
- estimated network hash rate

### Target Threshold and Leading Zeros

Bitcoin block headers store the mining target in a compact format called `bits`.
The dashboard decodes this compact value into the full 256-bit target threshold.
A block is valid only if its double-SHA-256 hash is numerically lower than this
target.

The lower the target, the harder it is to find a valid hash. This is why valid
Bitcoin block hashes usually begin with many zeros: leading zeros are a visible
consequence of the hash being very small in the 256-bit SHA-256 output space.

M1 shows both the latest block hash and the decoded target so the comparison is
explicit:

```text
hash < target
```

This connects the dashboard values directly to Proof of Work theory.

### Time Between Blocks

M1 fetches the last N Bitcoin blocks and computes the time difference between
each consecutive pair of blocks. These inter-block times are plotted as a
histogram.

The expected statistical distribution is an exponential distribution. The reason
is that Bitcoin mining can be modeled approximately as a Poisson process: miners
perform a very large number of independent hash attempts, and each attempt has a
small probability of success. In a Poisson process, the waiting time between
events follows an exponential distribution.

The protocol target is one block every 600 seconds, so the chart includes a
reference line at 600 seconds.

### Estimated Network Hash Rate

M1 estimates the network hash rate using the relationship:

```text
hashrate = difficulty * 2^32 / average_block_time
```

The dashboard shows two values:

- a window estimate based on the average block time from the selected recent
  blocks
- a 600-second baseline estimate using Bitcoin's target block interval

This estimate is approximate because short windows can be noisy: block discovery
is random, so a small sample of recent blocks may be faster or slower than the
long-term average.

### Current Status

M1 is functionally complete for the project requirements. The remaining work is
not code-related: the same explanation should later be summarized in the final
PDF report.

### Checkpoint Feedback Update - 2026-05-06

Feedback addressed: M1 needed clearer evidence of a working Proof of Work
monitor in the dashboard.

The M1 view now makes the live monitor status visible immediately by showing:

- live data loaded from the Blockstream API with fetch timestamp
- latest block height, difficulty, nonce, transaction count, and block age
- explicit Proof of Work validity metric
- latest block hash displayed in the dashboard
- decoded target threshold and `hash < target` check
- visual leading-zero comparison in the 256-bit SHA-256 space
- recent live blocks table

This update is intended to make M1 clearly recognizable as a live Proof of Work
monitor rather than a placeholder.

## M2 - Block Header Analyzer

Corresponding task: Required Module M2 - Block Header Analyzer.

M2 has been implemented in `modules/m2_block_header.py`. It analyzes a real
Bitcoin block header and verifies its Proof of Work locally using Python's
`hashlib` library.

### Implemented Values

The module currently shows the complete 80-byte Bitcoin block header structure:

- version
- previous block hash
- Merkle root
- timestamp
- bits
- nonce

For each field, the dashboard shows:

- byte position inside the 80-byte header
- raw little-endian hexadecimal representation
- decoded value

The module can analyze the latest block automatically or a custom block hash
entered by the user.

### Local Proof of Work Verification

M2 fetches the raw block header from the API and converts it from hexadecimal to
bytes. It then computes the block hash locally with:

```text
SHA256(SHA256(header))
```

Bitcoin displays block hashes in the reverse byte order of the raw SHA-256
digest, so the computed digest is reversed before comparing it with the block
hash returned by the API.

The dashboard verifies two conditions:

```text
computed hash == API block hash
computed hash < decoded target
```

If both are true, the block header satisfies Proof of Work.

### Bits and Target

The `bits` field stores the target threshold in Bitcoin's compact format. M2
decodes this value into the full 256-bit target and compares the locally computed
hash against it.

This is the core Proof of Work rule: a miner's block is valid only if the block
header hash is numerically smaller than the target.

### Leading Zero Bits

M2 counts the number of leading zero bits in the locally computed block hash.
This value is not itself the consensus rule, but it is a useful visual indicator
of how small the hash is relative to the full 256-bit SHA-256 output space.

### Byte Order

Bitcoin block headers require careful handling of byte order:

- integer fields such as version, timestamp, bits, and nonce are encoded in
  little-endian byte order
- previous block hash and Merkle root are stored internally in little-endian byte
  order
- displayed block hashes reverse the raw digest bytes

M2 makes these byte-order differences visible by showing both the raw
little-endian bytes and the decoded display values.

### Current Status

M2 is functionally complete for the project requirements. It displays all six
header fields, computes the double SHA-256 hash locally, verifies that the hash
is below the target, and counts leading zero bits.

## M3 - Difficulty History

Corresponding task: Required Module M3 - Difficulty History.

M3 has been implemented in `modules/m3_difficulty_history.py`. It studies the
evolution of Bitcoin difficulty over recent adjustment periods. One adjustment
period contains 2016 blocks.

### Implemented Values

The module currently shows:

- current chain tip height
- difficulty at the start of each recent adjustment period
- adjustment event heights
- start and adjustment dates for each period
- actual duration of each 2016-block period
- target duration of each period
- actual/target time ratio
- percentage difficulty change at the next adjustment

### Difficulty Over Time

Bitcoin retargets mining difficulty every 2016 blocks. M3 fetches the boundary
blocks at those adjustment heights and plots the difficulty value for each
period.

The chart marks adjustment events with vertical reference lines. These points
are important because difficulty is not updated after every block; it remains
constant during a 2016-block period and changes at the next boundary.

### Actual Block Time vs Target

The target block interval is 600 seconds. Therefore, one full adjustment period
has a target duration of:

```text
2016 * 600 seconds = 1,209,600 seconds = 14 days
```

M3 computes:

```text
actual/target ratio = actual period duration / (2016 * 600)
```

Interpretation:

- if the ratio is below 1, blocks were found faster than expected
- if the ratio is above 1, blocks were found slower than expected
- values close to 1 mean the network is close to the 10 minute target

### Adjustment Formula Intuition

Bitcoin adjusts difficulty to compensate for changes in total network hash
rate. If blocks are mined too quickly, difficulty should increase. If blocks are
mined too slowly, difficulty should decrease.

The simplified relationship used for interpretation is:

```text
next difficulty approximately equals current difficulty / actual_target_ratio
```

The dashboard compares the observed period timing with the difficulty change at
the next adjustment.

### Current Status

M3 is functionally complete for the project requirements. It plots difficulty
over recent adjustment periods, marks adjustment events, and shows the ratio
between actual block time and the 600-second target for each period.

## M4 - AI Component

Corresponding task: Required Module M4 - AI Component.

Chosen approach: Anomaly detector.

M4 has been implemented in `modules/m4_ai_component.py`. It identifies Bitcoin
blocks whose inter-arrival time is statistically unusual compared with an
exponential baseline.

### Model Choice

The selected model is an unsupervised anomaly detector based on the exponential
distribution.

This model was chosen because Bitcoin mining can be modeled approximately as a
Poisson process: miners perform many independent hash attempts, and each attempt
has a small probability of producing a valid block. In a Poisson process, the
waiting time between events follows an exponential distribution.

Therefore, the inter-block time is the feature used by the model.

### Data Used

M4 uses real recent Bitcoin block data from the Blockstream API. For each pair
of consecutive blocks, it computes:

```text
inter-block time = current block timestamp - previous block timestamp
```

The resulting dataset includes:

- block height
- block hash
- timestamp
- inter-block time in seconds
- inter-block time in minutes
- transaction count
- difficulty

### Training and Scoring

The recent interval dataset is split chronologically:

- 70% of the intervals are used as training data
- 30% are used as test data

The exponential model is fitted using maximum likelihood. For an exponential
distribution, the maximum-likelihood estimate of the mean is simply the sample
mean of the training inter-block times.

Each interval is assigned a two-sided p-value:

```text
p = 2 * min(P(X <= observed), P(X >= observed))
```

An interval is flagged as anomalous if this p-value is below the selected
threshold. The dashboard lets the user adjust this threshold.

### Evaluation Metrics

Because the model is unsupervised, there are no ground-truth labels for
"anomalous" blocks. For that reason, the evaluation does not use accuracy or F1.
Instead, M4 reports:

- train KS statistic
- test KS statistic
- test negative log-likelihood
- test anomaly rate

The KS statistic measures how far the empirical distribution is from the fitted
exponential distribution. Lower values indicate a better distribution fit.

The negative log-likelihood measures how much probability the model assigns to
the test intervals. Lower values indicate better out-of-sample fit.

The anomaly rate shows the percentage of test blocks flagged under the selected
p-value threshold.

## M5 - Merkle Proof Verifier

Corresponding task: Optional Module M5 - Merkle Proof Verifier.

M5 has been implemented in `modules/m5_merkle_proof.py`. It selects a transaction
from the latest Bitcoin block and verifies its Merkle proof step by step.

### Implemented Values

The module currently shows:

- latest block height
- number of transactions in the block
- selected transaction position
- Merkle proof depth
- selected transaction id
- block Merkle root
- all proof steps from transaction hash to Merkle root
- final comparison between computed root and API root

### Verification Method

For each level of the Merkle path, M5 checks whether the current hash is the
left or right child according to its position. It then pairs the current hash
with the sibling hash, converts both values to Bitcoin's internal byte order, and
computes:

```text
SHA256(SHA256(left || right))
```

The resulting parent hash becomes the current hash for the next level. If the
final computed hash equals the block header Merkle root, the transaction is
proved to belong to the block.

### Current Status

M5 is functionally complete. It verifies a real Merkle proof from live Bitcoin
data and shows each hash computation step.

## M6 - Security Score

Corresponding task: Optional Module M6 - Security Score.

M6 has been implemented in `modules/m6_security_score.py`. It estimates the cost
scale of a 51% attack on Bitcoin using live network hash rate data and adjustable
ASIC assumptions.

### Implemented Values

The module currently shows:

- estimated live Bitcoin network hash rate
- required 51% attack hash rate
- estimated electricity cost per hour
- estimated electricity cost per day
- rough hardware scale in USD
- confirmation-depth risk curve

### Cost Model

The module estimates network hash rate from recent blocks:

```text
hashrate = difficulty * 2^32 / average_block_time
```

It then estimates the attack hash rate as slightly above the live network hash
rate. Power consumption is estimated from ASIC efficiency:

```text
power (W) = TH/s * J/TH
hourly electricity cost = kW * USD/kWh
```

The hardware cost is a rough capital estimate based on user-selected USD/TH.

### Confirmation Risk

M6 also visualizes how confirmation depth reduces double-spend risk for an
attacker with less than 50% of the total hash rate. The approximation used is:

```text
probability approximately equals (q / p)^z
```

where `q` is the attacker hash share, `p` is the honest hash share, and `z` is
the number of confirmations.

### Current Status

M6 is functionally complete as an optional security module. The estimates are
intended for educational analysis, not as exact real-world attack pricing.

## M7 - Second AI Approach

Corresponding task: Optional Module M7 - Second AI approach.

M7 has been implemented in `modules/m7_second_ai.py`. It adds a second AI-style
method different from M4: a difficulty adjustment predictor.

### Model Choice

The model is a simple linear regression trained on recent Bitcoin difficulty
adjustment periods. It predicts the next difficulty from:

- current difficulty
- actual/target period duration ratio
- previous difficulty change percentage

This is intentionally explainable and lightweight, so it can be understood and
defended in the project presentation.

### Data Used

M7 uses real Bitcoin blocks at 2016-block adjustment boundaries. For each
completed period it computes:

- period start height
- adjustment height
- current difficulty
- actual/target duration ratio
- previous difficulty change
- actual next difficulty

The data is split chronologically into training and test periods.

### Evaluation Metrics

M7 compares the linear regression model with a protocol-formula baseline:

```text
baseline prediction = current difficulty / actual_target_ratio
```

The dashboard reports:

- MAE
- MAPE
- actual next difficulty
- regression prediction
- baseline prediction
- prediction error percentages

### Current Period Forecast

For the current incomplete adjustment period, M7 estimates the projected
actual/target ratio from blocks mined so far and produces a forecast for the next
difficulty adjustment.

### Current Status

M7 is functionally complete as an optional second AI approach. It trains and
evaluates a predictor on real blockchain data and compares it with a baseline.

### Dashboard Output

M4 displays:

- model training and test interval counts
- fitted mean inter-block time
- test anomaly rate
- test KS statistic
- evaluation metric table
- anomaly timeline
- histogram of observed intervals against the exponential baseline
- table of detected anomalous blocks

### Current Status

M4 is functionally complete for the project requirements. It implements one AI
approach, uses real blockchain data, produces anomaly detections, and evaluates
the model with appropriate unsupervised metrics.


<!-- student-repo-auditor:teacher-feedback:start -->
## Teacher Feedback

### Kick-off Review

Review time: 2026-04-29 20:31 CEST
Status: Green

Strength:
- I can see the dashboard structure integrating the checkpoint modules.

Improve now:
- M1 still needs clearer evidence of a working Proof of Work monitor in the dashboard.

Next step:
- Turn M1 into a working dashboard view with live Proof of Work metrics, not just a placeholder.
<!-- student-repo-auditor:teacher-feedback:end -->
