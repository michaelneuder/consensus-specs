# [DRAFT] `MAX_EFFECTIVE_BALANCE` increase - Spec

## Table of contents

<!-- TOC -->
<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->

- [Introduction](#introduction)
- [Constants](#constants)
  - [Withdrawal prefixes](#withdrawal-prefixes)
  - [Gwei values](#gwei-values)
- [Containers](#containers)
  - [New containers](#new-containers)
  - [Extended Containers](#extended-containers)
    - [`BeaconState`](#beaconstate)
- [Helpers](#helpers)
  - [Predicates](#predicates)
    - [updated `is_eligible_for_activation_queue`](#updated-is_eligible_for_activation_queue)
    - [new `has_compounding_withdrawal_credential`](#new-has_compounding_withdrawal_credential)
    - [updated  `is_fully_withdrawable_validator`](#updated--is_fully_withdrawable_validator)
    - [new `get_validator_excess_balance`](#new-get_validator_excess_balance)
    - [updated  `is_partially_withdrawable_validator`](#updated--is_partially_withdrawable_validator)
  - [Beacon state accessors](#beacon-state-accessors)
    - [updated  `get_validator_churn_limit`](#updated--get_validator_churn_limit)
  - [Beacon state mutators](#beacon-state-mutators)
    - [updated  `initiate_validator_exit`](#updated--initiate_validator_exit)
- [Genesis](#genesis)
    - [updated  `initialize_beacon_state_from_eth1`](#updated--initialize_beacon_state_from_eth1)
- [Beacon chain state transition function](#beacon-chain-state-transition-function)
  - [Epoch processing](#epoch-processing)
    - [updated  `process_registry_updates`](#updated--process_registry_updates)
  - [Block processing](#block-processing)
    - [updated  `get_expected_withdrawals`](#updated--get_expected_withdrawals)
    - [Operations](#operations)
      - [Deposits](#deposits)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->
<!-- /TOC -->

## Introduction

See [a modest proposal](https://notes.ethereum.org/@mikeneuder/increase-maxeb), the [diff view](https://github.com/michaelneuder/consensus-specs/pull/3/files) and 
[security considerations](https://notes.ethereum.org/@fradamt/meb-increase-security).

*Note:* This specification is built upon [Deneb](../../deneb/beacon-chain.md).

## Constants

The following values are (non-configurable) constants used throughout the specification.

### Withdrawal prefixes

| Name | Value |
| - | - |
| `BLS_WITHDRAWAL_PREFIX` | `Bytes1('0x00')` |
| `ETH1_ADDRESS_WITHDRAWAL_PREFIX` | `Bytes1('0x01')` |
| `COMPOUNDING_WITHDRAWAL_PREFIX` | `Bytes1('0x02')` |

### Gwei values

| Name | Value |
| - | - |
| `MIN_ACTIVATION_BALANCE` | `Gwei(2**5 * 10**9)`  (32 ETH) |
| `MAX_EFFECTIVE_BALANCE_MAXEB` | `Gwei(2**11 * 10**9)` (2048 ETH) |

## Containers

### New containers

### Extended Containers

#### `BeaconState`

*Note*: adding `activation_validator_balance` and `exit_queue_churn` fields to
aid in rate limiting of activation and exit queue based on ETH rather than
validator counts.

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

    # --- NEW --- #
    activation_validator_balance: Gwei
    exit_queue_churn: Gwei 
    # --- END NEW --- #

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

### Predicates

#### updated `is_eligible_for_activation_queue`

*Note*: Use `>= MIN_ACTIVATION_BALANCE` instead of `== MAX_EFFECTIVE_BALANCE`

```python
def is_eligible_for_activation_queue(validator: Validator) -> bool:
    """
    Check if ``validator`` is eligible to be placed into the activation queue.
    """
    return (
        validator.activation_eligibility_epoch == FAR_FUTURE_EPOCH
        # --- MODIFIED --- #
        and validator.effective_balance >= MIN_ACTIVATION_BALANCE
        # --- END MODIFIED --- #
    )
```

#### new `has_compounding_withdrawal_credential`

```python
def has_compounding_withdrawal_credential(validator: Validator) -> bool:
    """
    Check if ``validator`` has an 0x02 prefixed "compounding" withdrawal credential.
    """
    return validator.withdrawal_credentials[:1] == COMPOUNDING_WITHDRAWAL_PREFIX
```

#### updated  `is_fully_withdrawable_validator`

*Note*: now calls `has_compounding_withdrawal_credential` too.  

```python
def is_fully_withdrawable_validator(validator: Validator, balance: Gwei, epoch: Epoch) -> bool:
    """
    Check if ``validator`` is fully withdrawable.
    """
    return (
        # --- MODIFIED --- #
        (has_eth1_withdrawal_credential(validator) or has_compounding_withdrawal_credential(validator))
        # --- END MODIFIED --- #
        and validator.withdrawable_epoch <= epoch
        and balance > 0
    )
```

#### new `get_validator_excess_balance`

```python
def get_validator_excess_balance(validator: Validator, balance: Gwei) -> Gwei:
    """
    Get excess balance for partial withdrawals for ``validator``.
    """
    if has_compounding_withdrawal_credential(validator) and balance > MAX_EFFECTIVE_BALANCE_MAXEB:
        return balance - MAX_EFFECTIVE_BALANCE_MAXEB
    elif has_eth1_withdrawal_credential(validator) and balance > MIN_ACTIVATION_BALANCE:
        return balance - MIN_ACTIVATION_BALANCE
    return Gwei(0)
```

####  updated  `is_partially_withdrawable_validator`
*Note*: now calls `has_withdrawalable_credential` and gets ceiling from `get_balance_ceiling`.

```python
def is_partially_withdrawable_validator(validator: Validator, balance: Gwei) -> bool:
    """
    Check if ``validator`` is partially withdrawable.
    """
    # --- MODIFIED --- #
    return get_validator_excess_balance(validator, balance) > 0
    # --- END MODIFIED --- #
```

### Beacon state accessors
#### updated  `get_validator_churn_limit`

*Note*: updated to return a Gwei amount of amount of churn per epoch.

```python
def get_validator_churn_limit(state: BeaconState) -> Gwei:
    total_balance = get_total_active_balance(state)
    return max(MIN_PER_EPOCH_CHURN_LIMIT, total_balance // CHURN_LIMIT_QUOTIENT)
```

### Beacon state mutators

#### updated  `initiate_validator_exit`

*Note*: Modification to make validator exits constrained by the balance
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
    # Compute exit queue epoch
    exit_epochs = [v.exit_epoch for v in state.validators if v.exit_epoch != FAR_FUTURE_EPOCH]
    exit_queue_epoch = max(exit_epochs + [compute_activation_exit_epoch(get_current_epoch(state))])

    # --- MODIFIED --- #
    exit_balance_to_consume = validator.effective_balance
    per_epoch_churn_limit = get_validator_churn_limit(state)
    if state.exit_queue_churn + exit_balance_to_consume <= per_epoch_churn_limit:
        state.exit_queue_churn += exit_balance_to_consume
    else:  # Exit balance rolls over to subsequent epoch(s)
        exit_balance_to_consume -= (per_epoch_churn_limit - state.exit_queue_churn)
        exit_queue_epoch += Epoch(1)
        while exit_balance_to_consume >= per_epoch_churn_limit:
            exit_balance_to_consume -= per_epoch_churn_limit
            exit_queue_epoch += Epoch(1)
        state.exit_queue_churn = exit_balance_to_consume
    # --- END MODIFIED --- #

    # Set validator exit epoch and withdrawable epoch
    validator.exit_epoch = exit_queue_epoch
    validator.withdrawable_epoch = Epoch(validator.exit_epoch + MIN_VALIDATOR_WITHDRAWABILITY_DELAY)
```

## Genesis
####  updated  `initialize_beacon_state_from_eth1`
*Note*: Replace `== MAX_EFFECTIVE_BALANCE` with `>= MIN_ACTIVATION_BALANCE` when 
checking for activation processing.
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
        validator.effective_balance = min(balance - balance % EFFECTIVE_BALANCE_INCREMENT, MAX_EFFECTIVE_BALANCE_MAXEB)
        
        # --- MODIFIED --- #
        if validator.effective_balance >= MIN_ACTIVATION_BALANCE: 
            validator.activation_eligibility_epoch = GENESIS_EPOCH
            validator.activation_epoch = GENESIS_EPOCH
        # --- END MODIFIED --- #
    # Set genesis validators root for domain separation and chain versioning
    state.genesis_validators_root = hash_tree_root(state.validators)
    return state
```

## Beacon chain state transition function
### Epoch processing
#### updated  `process_registry_updates`
*Note*: changing the dequed validators to depend on the weight of activation up to the
churn limit. 
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
    # Dequeue validators for activation up to churn limit [MODIFIED TO BE WEIGHT-SENSITIVE]
    
    # --- MODIFIED --- #
    activation_balance_to_consume = get_validator_churn_limit(state)
    for index in activation_queue:
        validator = state.validators[index]
        # Validator can now be activated
        if state.activation_validator_balance + activation_balance_to_consume >= validator.effective_balance:
            activation_balance_to_consume -= (validator.effective_balance - state.activation_validator_balance)
            state.activation_validator_balance = Gwei(0)
            validator.activation_epoch = compute_activation_exit_epoch(get_current_epoch(state))
        else:  
            state.activation_validator_balance += activation_balance_to_consume
            break
    # --- END MODIFIED --- #
```

### Block processing
####  updated  `get_expected_withdrawals`
*Note*: now calls `get_validator_excess_balance.`.
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
            withdrawals.append(Withdrawal(
                index=withdrawal_index,
                validator_index=validator_index,
                address=ExecutionAddress(validator.withdrawal_credentials[12:]),
                # --- MODIFIED --- #
                amount=get_validator_excess_balance(validator, balance),
                # --- END MODIFIED --- #
            ))
            withdrawal_index += WithdrawalIndex(1)
        if len(withdrawals) == MAX_WITHDRAWALS_PER_PAYLOAD:
            break
        validator_index = ValidatorIndex((validator_index + 1) % len(state.validators))
    return withdrawals
```

#### Operations 

##### Deposits

**updated  `apply_deposit`**

*Note*: updated to cap top-offs at 32 ETH to avoid skipping activation queue.

```python
def apply_deposit(state: BeaconState,
                  pubkey: BLSPubkey,
                  withdrawal_credentials: Bytes32,
                  amount: uint64,
                  signature: BLSSignature) -> None:
    validator_pubkeys = [v.pubkey for v in state.validators]
    if pubkey not in validator_pubkeys:
        # Verify the deposit signature (proof of possession) which is not checked by the deposit contract
        deposit_message = DepositMessage(
            pubkey=pubkey,
            withdrawal_credentials=withdrawal_credentials,
            amount=amount,
        )
        domain = compute_domain(DOMAIN_DEPOSIT)  # Fork-agnostic domain since deposits are valid across forks
        signing_root = compute_signing_root(deposit_message, domain)
        if not bls.Verify(pubkey, signing_root, signature):
            return

        # Add validator and balance entries
        state.validators.append(get_validator_from_deposit(pubkey, withdrawal_credentials, amount))
        state.balances.append(amount)
    else:

        # --- MODIFIED --- #
        # Increase balance by deposit amount, up to MIN_ACTIVATION_BALANCE
        index = ValidatorIndex(validator_pubkeys.index(pubkey))
        increase_balance(state, index, min(amount, MIN_ACTIVATION_BALANCE - state.balances[index]))
        # --- END MODIFIED --- #
```