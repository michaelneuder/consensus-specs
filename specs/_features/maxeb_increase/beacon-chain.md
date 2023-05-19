# [DRAFT] `MAX_EFFECTIVE_BALANCE` increase - Spec

### *Open questions*

[a] **Should slashing penalties (and whistleblower rewards) no longer depend on the effective balance?**
Currently, we have [`slash_validator`](https://github.com/ethereum/consensus-specs/blob/dev/specs/bellatrix/beacon-chain.md#modified-slash_validator) which calculates the slashing penalty as
```python
slashing_penalty = validator.effective_balance // MIN_SLASHING_PENALTY_QUOTIENT_BELLATRIX
```
where `MIN_SLASHING_PENALTY_QUOTIENT_BELLATRIX=32`, so the max a validator can be slashed is
1 ETH if they have an effective balance of 32. If we leave this unchanged, then a validator with an 
effective balance of 2048 ETH could get slashed 2048 / 32 = 64 ETH, which seems a bit harsh. Especially
given the validator is exited after the slashing. To me, it feels like the slashing penalties should 
no longer depend on the validator effective balance, and should just be constant (e.g., 1 ETH for an
equivocating proposal, no matter the stake). If an attacker was planning to equivocate and they wanted 
to avoid a higher equivocation penalty incurred form using a larger validator effective balance, they
could simply activate many validators and only face a max of 1 ETH slashing while still controlling
the same number of slots (and actually having more opportunities to equivocate). 

[b] **Should the proposer reward no longer depend on the effective balance?** Currently, [`get_base_reward`](https://github.com/ethereum/consensus-specs/blob/dev/specs/altair/beacon-chain.md#get_base_reward), a function that depends on the effective balance of a validator
is used to calculate the attestation and proposer rewards. For attestation rewards,
no change is necessary because a higher stake proposer is only assigned to a single attesting committee
(e.g., a 64 ETH validator should earn 2x a 32 ETH validator for an attestation). 
This is because attesting committee selection is done without replacement (it partitions
the validator set). For proposer rewards, however, the sampling is done with replacement based on the 
effective balance of the validators. Thus a 64 ETH validator will be selected twice as often as a 
32 ETH validator, and thus each proposer reward should *not* be worth more. 


## Table of contents

<!-- TOC -->
<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->

- [Introduction](#introduction)
- [Custom types](#custom-types)
  - [Domain types](#domain-types)
- [Preset](#preset)
  - [Max operations per block](#max-operations-per-block)
- [Constants](#constants)
  - [Withdrawal prefixes](#withdrawal-prefixes)
  - [Gwei values](#gwei-values)
- [Configuration](#configuration)
  - [Validator cycle](#validator-cycle)
- [Containers](#containers)
  - [New containers](#new-containers)
    - [<span style="background-color: #FFFF00">new</span> `ExecutionToCompoundingChange`](#span-stylebackground-color-ffff00newspan-executiontocompoundingchange)
    - [<span style="background-color: #FFFF00">new</span>  `SignedExecutionToCompoundingChange`](#span-stylebackground-color-ffff00newspan--signedexecutiontocompoundingchange)
  - [Extended Containers](#extended-containers)
    - [<span style="background-color: #FFFF00">updated</span> `BeaconBlockBody`](#span-stylebackground-color-ffff00updatedspan-beaconblockbody)
- [Helpers](#helpers)
  - [Math](#math)
    - [<span style="background-color: #FFFF00">new</span> `is_power_of_two`](#span-stylebackground-color-ffff00newspan-is_power_of_two)
    - [<span style="background-color: #FFFF00">new</span> `bytes_to_uint16`](#span-stylebackground-color-ffff00newspan-bytes_to_uint16)
  - [Predicates](#predicates)
    - [<span style="background-color: #FFFF00">updated</span> `is_eligible_for_activation_queue`](#span-stylebackground-color-ffff00updatedspan-is_eligible_for_activation_queue)
    - [<span style="background-color: #FFFF00">new</span> `has_compounding_withdrawal_credential`](#span-stylebackground-color-ffff00newspan-has_compounding_withdrawal_credential)
    - [<span style="background-color: #FFFF00">new</span> `has_withdrawalable_credential`](#span-stylebackground-color-ffff00newspan-has_withdrawalable_credential)
    - [<span style="background-color: #FFFF00">updated</span>  `is_fully_withdrawable_validator`](#span-stylebackground-color-ffff00updatedspan--is_fully_withdrawable_validator)
    - [<span style="background-color: #FFFF00">updated</span>  `is_partially_withdrawable_validator`](#span-stylebackground-color-ffff00updatedspan--is_partially_withdrawable_validator)
  - [Misc](#misc)
    - [<span style="background-color: #FFFF00">new</span>  `get_balance_ceiling`](#span-stylebackground-color-ffff00newspan--get_balance_ceiling)
  - [Beacon state accessors](#beacon-state-accessors)
    - [<span style="background-color: #FFFF00">updated</span>  `get_validator_churn_limit`](#span-stylebackground-color-ffff00updatedspan--get_validator_churn_limit)
  - [Beacon state mutators](#beacon-state-mutators)
    - [<span style="background-color: #FFFF00">updated</span>  `initiate_validator_exit`](#span-stylebackground-color-ffff00updatedspan--initiate_validator_exit)
- [Genesis](#genesis)
    - [<span style="background-color: #FFFF00">updated</span>  `initialize_beacon_state_from_eth1`](#span-stylebackground-color-ffff00updatedspan--initialize_beacon_state_from_eth1)
- [Beacon chain state transition function](#beacon-chain-state-transition-function)
  - [Epoch processing](#epoch-processing)
    - [<span style="background-color: #FFFF00">updated</span>  `process_registry_updates`](#span-stylebackground-color-ffff00updatedspan--process_registry_updates)
  - [Block processing](#block-processing)
    - [<span style="background-color: #FFFF00">updated</span>  `get_expected_withdrawals`](#span-stylebackground-color-ffff00updatedspan--get_expected_withdrawals)
    - [<span style="background-color: #FFFF00">updated</span>   `process_operations`](#span-stylebackground-color-ffff00updatedspan---process_operations)
    - [<span style="background-color: #FFFF00">new</span>  `process_execution_to_compounding_change`](#span-stylebackground-color-ffff00newspan--process_execution_to_compounding_change)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->
<!-- /TOC -->

## Introduction

See [a modest proposal](https://notes.ethereum.org/@mikeneuder/Hkyw_cDE2) and 
[security considerations](https://notes.ethereum.org/@fradamt/meb-increase-security).

*Note:* This specification is built upon [Deneb](../../deneb/beacon-chain.md) and is under active development.

## Custom types

### Domain types

| Name | Value |
| - | - |
| <span style="background-color: #FFFF00">new</span> `DOMAIN_EXECUTION_TO_COMPOUNDING_CHANGE` | `DomainType('0x0B000000')` |

## Preset

### Max operations per block

| Name | Value |
| - | - |
| `MAX_EXECUTION_TO_COMPOUNDING_CHANGES` | `2**4` (= 16) |


## Constants

The following values are (non-configurable) constants used throughout the specification.

### Withdrawal prefixes

| Name | Value |
| - | - |
| `BLS_WITHDRAWAL_PREFIX` | `Bytes1('0x00')` |
| `ETH1_ADDRESS_WITHDRAWAL_PREFIX` | `Bytes1('0x01')` |
| <span style="background-color: #FFFF00">new</span> `COMPOUNDING_WITHDRAWAL_PREFIX` | `Bytes1('0x02')` |

### Gwei values

| Name | Value |
| - | - |
| <span style="background-color: #FFFF00">updated</span> `MAX_EFFECTIVE_BALANCE` | `Gwei(2**11 * 10**9)` (2048 ETH) |
| <span style="background-color: #FFFF00">new</span> `MIN_ACTIVATION_BALANCE` | `Gwei(2**5 * 10**9)`  (32 ETH) |

## Configuration

### Validator cycle

| Name | Value |
| - | - |
| <span style="background-color: #FFFF00">updated</span> `MIN_PER_EPOCH_CHURN_LIMIT` | `Gwei(2**7 * 10**9)` (128 ETH) |

## Containers

### New containers

#### <span style="background-color: #FFFF00">new</span> `ExecutionToCompoundingChange`

```python
class ExecutionToCompoundingChange(Container):
    validator_index: ValidatorIndex
    balance_ceiling: uint16 # denominated in ETH, must be a power of 2 and <=2^11.    
```

#### <span style="background-color: #FFFF00">new</span>  `SignedExecutionToCompoundingChange`

```python
class SignedExecutionToCompoundingChange(Container):
    message: ExecutionToCompoundingChange
    signature: BLSSignature
```

### Extended Containers

#### <span style="background-color: #FFFF00">updated</span> `BeaconBlockBody`

*Note*: adding `execution_to_compounding_changes` field.

```python
class BeaconBlockBody(Container):
    randao_reveal: BLSSignature
    eth1_data: Eth1Data
    graffiti: Bytes32 
    proposer_slashings: List[ProposerSlashing, MAX_PROPOSER_SLASHINGS]
    attester_slashings: List[AttesterSlashing, MAX_ATTESTER_SLASHINGS]
    attestations: List[Attestation, MAX_ATTESTATIONS]
    deposits: List[Deposit, MAX_DEPOSITS]
    voluntary_exits: List[SignedVoluntaryExit, MAX_VOLUNTARY_EXITS]
    sync_aggregate: SyncAggregate
    execution_payload: ExecutionPayload
    bls_to_execution_changes: List[SignedBLSToExecutionChange, MAX_BLS_TO_EXECUTION_CHANGES] 
    execution_to_compounding_changes: List[SignedExecutionToCompoundingChange, MAX_EXECUTION_TO_COMPOUNDING_CHANGES] # new
    blob_kzg_commitments: List[KZGCommitment, MAX_BLOBS_PER_BLOCK] 
```

#### `BeaconState`

*Note*: adding `exit_queue_churn` field, keeping track of the total balance of validators whose exit epoch is the latest assigned one.

```python
class BeaconState(Container):
    # Versioning
    genesis_time: uint64
    genesis_validators_root: Root
    slot: Slot
    fork: Fork
    # History
    latest_block_header: BeaconBlockHeader
    block_roots: Vector[Root, SLOTS_PER_HISTORICAL_ROOT]
    state_roots: Vector[Root, SLOTS_PER_HISTORICAL_ROOT]
    historical_roots: List[Root, HISTORICAL_ROOTS_LIMIT]
    # Eth1
    eth1_data: Eth1Data
    eth1_data_votes: List[Eth1Data, EPOCHS_PER_ETH1_VOTING_PERIOD * SLOTS_PER_EPOCH]
    eth1_deposit_index: uint64
    # Registry
    validators: List[Validator, VALIDATOR_REGISTRY_LIMIT]
    balances: List[Gwei, VALIDATOR_REGISTRY_LIMIT]
    exit_queue_churn: Gwei # new
    # Randomness
    randao_mixes: Vector[Bytes32, EPOCHS_PER_HISTORICAL_VECTOR]
    # Slashings
    slashings: Vector[Gwei, EPOCHS_PER_SLASHINGS_VECTOR]  # Per-epoch sums of slashed effective balances
    # Participation
    previous_epoch_participation: List[ParticipationFlags, VALIDATOR_REGISTRY_LIMIT]
    current_epoch_participation: List[ParticipationFlags, VALIDATOR_REGISTRY_LIMIT]
    # Finality
    justification_bits: Bitvector[JUSTIFICATION_BITS_LENGTH]  # Bit set for every recent justified epoch
    previous_justified_checkpoint: Checkpoint
    current_justified_checkpoint: Checkpoint
    finalized_checkpoint: Checkpoint
    # Inactivity
    inactivity_scores: List[uint64, VALIDATOR_REGISTRY_LIMIT]
    # Sync
    current_sync_committee: SyncCommittee
    next_sync_committee: SyncCommittee
    # Execution
    latest_execution_payload_header: ExecutionPayloadHeader
```

## Helpers

*Note*: The definitions below are for specification purposes and are not necessarily optimal implementations.

### Math

#### <span style="background-color: #FFFF00">new</span> `is_power_of_two`

```python
def is_power_of_two(n: uint16) -> bool:
    return (n != 0) and (n & (n-1) == 0)
```

#### <span style="background-color: #FFFF00">new</span> `bytes_to_uint16`

```python
def bytes_to_uint16(data: bytes) -> uint16:
    """
    Return the integer deserialization of ``data`` interpreted as ``ENDIANNESS``-endian.
    """
    return uint16(int.from_bytes(data, ENDIANNESS))
```

### Predicates

#### <span style="background-color: #FFFF00">updated</span> `is_eligible_for_activation_queue`

*Note*: Use `>= MIN_ACTIVATION_BALANCE` instead of `== MAX_EFFECTIVE_BALANCE`

```python
def is_eligible_for_activation_queue(validator: Validator) -> bool:
    """
    Check if ``validator`` is eligible to be placed into the activation queue.
    """
    return (
        validator.activation_eligibility_epoch == FAR_FUTURE_EPOCH
        and validator.effective_balance >= MIN_ACTIVATION_BALANCE # modfied
    )
```

#### <span style="background-color: #FFFF00">new</span> `has_compounding_withdrawal_credential`

```python
def has_compounding_withdrawal_credential(validator: Validator) -> bool:
    """
    Check if ``validator`` has an 0x02 prefixed "compounding" withdrawal credential.
    """
    return validator.withdrawal_credentials[:1] == COMPOUNDING_WITHDRAWAL_PREFIX
```

#### <span style="background-color: #FFFF00">new</span> `has_withdrawalable_credential`

```python
def has_withdrawalable_credential(validator: Validator) -> bool:
    """
    Check if ``validator`` has a withdrawable credential.
    """
    return has_eth1_withdrawal_credential(validator) or has_compounding_withdrawal_credential(validator)
```

#### <span style="background-color: #FFFF00">updated</span>  `is_fully_withdrawable_validator`

*Note*: now calls `has_withdrawalable_credential`.  

```python
def is_fully_withdrawable_validator(validator: Validator, balance: Gwei, epoch: Epoch) -> bool:
    """
    Check if ``validator`` is fully withdrawable.
    """
    return (
        has_withdrawalable_credential(validator) # modified
        and validator.withdrawable_epoch <= epoch
        and balance > 0
    )
```

####  <span style="background-color: #FFFF00">updated</span>  `is_partially_withdrawable_validator`
*Note*: now calls `has_withdrawalable_credential` and gets ceiling from `get_balance_ceiling`.

```python
def is_partially_withdrawable_validator(validator: Validator, balance: Gwei) -> bool:
    """
    Check if ``validator`` is partially withdrawable.
    """
    if not has_withdrawable_credential(validator):
        return false
    
    ceiling = get_balance_ceiling(validator)
    has_ceiling_effective_balance = validator.effective_balance == ceiling
    has_excess_balance = balance > ceiling
    return has_ceiling_effective_balance and has_excess_balance
```


### Misc

#### <span style="background-color: #FFFF00">new</span>  `get_balance_ceiling`

```python
def get_balance_ceiling(validator: Validator) -> Gwei:
    """
    Return the balance ceiling for a validator.
    """
    if not has_compounding_withdrawal_credential(validator):
        return MIN_ACTIVATION_BALANCE
    # With compounding credential bytes [1-2] are the ceiling in ETH.
    return bytes_to_uint16(validator.withdrawal_credential[1:3]) * EFFECTIVE_BALANCE_INCREMENT
```

### Beacon state accessors
#### <span style="background-color: #FFFF00">updated</span>  `get_validator_churn_limit`

*Note*: updated to do a weight based calculation of the amount of validators that 
can exit per epoch. This is based on the new value of `MIN_PER_EPOCH_CHURN_LIMIT=128 ETH`,
which is equivalent to four 32 ETH validators. `CHURN_LIMIT_QUOTIENT` remains unchanged,
because it denotes the fraction of total weight that we are comfortable losing per epoch:
$1/65536$

```python
def get_validator_churn_limit(state: BeaconState) -> Gwei:
    total_balance = get_total_active_balance(state)
    return max(MIN_PER_EPOCH_CHURN_LIMIT, total_balance // CHURN_LIMIT_QUOTIENT)
```

### Beacon state mutators

#### <span style="background-color: #FFFF00">updated</span>  `initiate_validator_exit`

*Note*: Large modification to make validator exits constrained by the balance
of the exiting validators. 

```python
def initiate_validator_exit(state: BeaconState, index: ValidatorIndex) -> None:
    """
    Initiate the exit of the validator with index ``index``.
    """
    # Return if validator already initiated exit
    validator = state.validators[index]
    if validator.exit_epoch != FAR_FUTURE_EPOCH:
        return

    # ---- BELOW IS UPDATED ----
    # Compute exit queue epoch
    exit_epochs = [v.exit_epoch for v in state.validators if v.exit_epoch != FAR_FUTURE_EPOCH]
    exit_queue_epoch = max(exit_epochs + [compute_activation_exit_epoch(get_current_epoch(state))])
    if exit_queue_epoch > max(exit_epochs): 
        state.exit_queue_churn = Gwei(0)
    churn_limit = get_validator_churn_limit(state)
    if state.exit_queue_churn + validator.effective_balance <= churn_limit: # the validator fits within the churn of the current exit_queue_epoch
        state.exit_queue_churn += validator.effective_balance # the full effective balance of the validator contributes to the churn in the exit queue epoch 
    else: # the validator fits within the churn of the current exit_queue_epoch
        future_epochs_churn_contribution = validator.effective_balance - (churn_limit - state.exit_queue_churn)
        exit_queue_epoch += Epoch((future_epochs_churn_contribution + churn_limit - 1) // churn_limit # (numerator + denominator - 1) // denominator rounds up. 
        # the validator contributes to the churn in the exit queue epoch, based on how much balance is left over at that point 
        if future_epochs_churn_contribution % churn_limit == 0:
            state.exit_queue_churn = churn_limit
        else:
            state.exit_queue_churn = future_epochs_churn_contribution % churn_limit

    # Set validator exit epoch and withdrawable epoch
    validator.exit_epoch = exit_queue_epoch
    validator.withdrawable_epoch = Epoch(validator.exit_epoch + MIN_VALIDATOR_WITHDRAWABILITY_DELAY)
```

## Genesis

####  <span style="background-color: #FFFF00">updated</span>  `initialize_beacon_state_from_eth1`

*Note*: Replace `== MAX_EFFECTIVE_BALANCE` with `>= MIN_ACTIVATION_BALANCE` when checking
for activation processing.

```python
def initialize_beacon_state_from_eth1(eth1_block_hash: Hash32,
                                      eth1_timestamp: uint64,
                                      deposits: Sequence[Deposit]) -> BeaconState:
    fork = Fork(
        previous_version=GENESIS_FORK_VERSION,
        current_version=GENESIS_FORK_VERSION,
        epoch=GENESIS_EPOCH,
    )
    state = BeaconState(
        genesis_time=eth1_timestamp + GENESIS_DELAY,
        fork=fork,
        eth1_data=Eth1Data(block_hash=eth1_block_hash, deposit_count=uint64(len(deposits))),
        latest_block_header=BeaconBlockHeader(body_root=hash_tree_root(BeaconBlockBody())),
        randao_mixes=[eth1_block_hash] * EPOCHS_PER_HISTORICAL_VECTOR,  # Seed RANDAO with Eth1 entropy
    )

    # Process deposits
    leaves = list(map(lambda deposit: deposit.data, deposits))
    for index, deposit in enumerate(deposits):
        deposit_data_list = List[DepositData, 2**DEPOSIT_CONTRACT_TREE_DEPTH](*leaves[:index + 1])
        state.eth1_data.deposit_root = hash_tree_root(deposit_data_list)
        process_deposit(state, deposit)

    # Process activations
    for index, validator in enumerate(state.validators):
        balance = state.balances[index]
        validator.effective_balance = min(balance - balance % EFFECTIVE_BALANCE_INCREMENT, MAX_EFFECTIVE_BALANCE)
        if validator.effective_balance >= MIN_ACTIVATION_BALANCE: # updated
            validator.activation_eligibility_epoch = GENESIS_EPOCH
            validator.activation_epoch = GENESIS_EPOCH

    # Set genesis validators root for domain separation and chain versioning
    state.genesis_validators_root = hash_tree_root(state.validators)

    return state
```

## Beacon chain state transition function

### Epoch processing

#### <span style="background-color: #FFFF00">updated</span>  `process_registry_updates`

*Note*: changing the dequed validators to depend on the weight of activation up to the
churn limit. Only the last 8 lines of the function are updated.

```python
def process_registry_updates(state: BeaconState) -> None:
    # Process activation eligibility and ejections
    for index, validator in enumerate(state.validators):
        if is_eligible_for_activation_queue(validator):
            validator.activation_eligibility_epoch = get_current_epoch(state) + 1

        if (
            is_active_validator(validator, get_current_epoch(state))
            and validator.effective_balance <= EJECTION_BALANCE
        ):
            initiate_validator_exit(state, ValidatorIndex(index))

    # Queue validators eligible for activation and not yet dequeued for activation
    activation_queue = sorted([
        index for index, validator in enumerate(state.validators)
        if is_eligible_for_activation(state, validator)
        # Order by the sequence of activation_eligibility_epoch setting and then index
    ], key=lambda index: (state.validators[index].activation_eligibility_epoch, index))
    # ---- BELOW IS UPDATED ----
    # Dequeue validators for activation up to churn limit [MODIFIED TO BE WEIGHT-SENSITIVE]
    max_churn_left = get_validator_churn_limit(state) # This is now a Gwei amount
    for index in activation_queue:
        validator = state.validators[index]
        max_churn_left -= validator.effective_balance
        if max_churn_left < 0:
            break
        validator.activation_epoch = compute_activation_exit_epoch(get_current_epoch(state))
```

### Block processing

####  <span style="background-color: #FFFF00">updated</span>  `get_expected_withdrawals`

*Note*: only two lines changed in the elif, marked with `# modified`.

```python
def get_expected_withdrawals(state: BeaconState) -> Sequence[Withdrawal]:
    epoch = get_current_epoch(state)
    withdrawal_index = state.next_withdrawal_index
    validator_index = state.next_withdrawal_validator_index
    withdrawals: List[Withdrawal] = []
    bound = min(len(state.validators), MAX_VALIDATORS_PER_WITHDRAWALS_SWEEP)
    for _ in range(bound):
        validator = state.validators[validator_index]
        balance = state.balances[validator_index]
        if is_fully_withdrawable_validator(validator, balance, epoch):
            withdrawals.append(Withdrawal(
                index=withdrawal_index,
                validator_index=validator_index,
                address=ExecutionAddress(validator.withdrawal_credentials[12:]),
                amount=balance,
            ))
            withdrawal_index += WithdrawalIndex(1)
        elif is_partially_withdrawable_validator(validator, balance):
            ceiling = get_balance_ceiling(validator) # modified
            withdrawals.append(Withdrawal(
                index=withdrawal_index,
                validator_index=validator_index,
                address=ExecutionAddress(validator.withdrawal_credentials[12:]),
                amount=balance - ceiling, # modified
            ))
            withdrawal_index += WithdrawalIndex(1)
        if len(withdrawals) == MAX_WITHDRAWALS_PER_PAYLOAD:
            break
        validator_index = ValidatorIndex((validator_index + 1) % len(state.validators))
    return withdrawals
```

#### <span style="background-color: #FFFF00">updated</span>   `process_operations`
Note: The function `process_operations` is modified to process `SignedExecutionToCompoundingChange` operations included in the block.

```python
def process_operations(state: BeaconState, body: BeaconBlockBody) -> None:
    # Verify that outstanding deposits are processed up to the maximum number of deposits
    assert len(body.deposits) == min(MAX_DEPOSITS, state.eth1_data.deposit_count - state.eth1_deposit_index)

    def for_ops(operations: Sequence[Any], fn: Callable[[BeaconState, Any], None]) -> None:
        for operation in operations:
            fn(state, operation)

    for_ops(body.proposer_slashings, process_proposer_slashing)
    for_ops(body.attester_slashings, process_attester_slashing)
    for_ops(body.attestations, process_attestation)
    for_ops(body.deposits, process_deposit)
    for_ops(body.voluntary_exits, process_voluntary_exit)
    for_ops(body.bls_to_execution_changes, process_bls_to_execution_change)
    for_ops(body.execution_to_compounding_changes, process_execution_to_compounding_change) # new
```

#### <span style="background-color: #FFFF00">new</span>  `process_execution_to_compounding_change`

```python
def process_execution_to_compounding_change(state: BeaconState,
                                       signed_compounding_change: SignedExecutionToCompoundingChange) -> None:
    compounding_change = signed_compounding_change.message

    assert compounding_change.validator_index < len(state.validators)

    assert validator.withdrawal_credentials[:1] == ETH1_ADDRESS_WITHDRAWAL_PREFIX

    # Check that balance_ceiling is a power of 2.
    assert is_power_of_two(compounding_change.balance_ceiling)

    # Check that balance_ceiling is greater than MIN_ACTIVATION_BALANCE.
    assert compounding_change.balance_ceiling >= MIN_ACTIVATION_BALANCE

    # Check that balance_ceiling is less than MaxEB.
    assert compounding_change.balance_ceiling <= MAX_EFFECTIVE_BALANCE

    # Write balance from uint16 into Bytes2.
    ceiling_bytes = uint_to_bytes(compounding_change.balance_ceiling)

    # Last 20 bytes are still the withdrawal address.
    address = validator.withdrawal_credentials[12:]

    # Fork-agnostic domain since compounding changes are valid across forks.
    domain = compute_domain(DOMAIN_EXECUTION_TO_COMPOUNDING_CHANGE, genesis_validators_root=state.genesis_validators_root)
    signing_root = compute_signing_root(compounding_change, domain)
    assert bls.Verify(validator.pubkey, signing_root, signed_compounding_change.signature)

    validator.withdrawal_credentials = (
        COMPOUNDING_WITHDRAWAL_PREFIX # byte 0
        + ceiling_bytes               # bytes [1,2]
        + b'\x00' * 9                 # bytes [3,11]
        + address                     # bytes [12,31]
    )

```
