gi# Auxiliary Project Report

This file is used as a parallel documentation/report file for the project. The
original `README.md` is intentionally left unchanged.

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
