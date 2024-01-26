# MAXEB - Spec

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

#### new `PendingBalanceDeposit`

```python
class PendingBalanceDeposit(Container):
    index: ValidatorIndex
    amount: Gwei
```

#### new `PartialWithdrawal`

```python
class PartialWithdrawal(Container):
    index: ValidatorIndex
    amount: Gwei
    withdrawable_epoch: Epoch
```
#### new `ExecutionLayerWithdrawRequest`

```python
class ExecutionLayerWithdrawRequest(Container):
    source_address: ExecutionAddress
    validator_pubkey: BLSPubkey
    amount: Gwei
```

### Extended Containers

#### `BeaconState`

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
    # Withdrawals
    next_withdrawal_index: WithdrawalIndex
    next_withdrawal_validator_index: ValidatorIndex
    # Deep history valid from Capella onwards
    historical_summaries: List[HistoricalSummary, HISTORICAL_ROOTS_LIMIT]
    # --- NEW --- #
    deposit_balance_to_consume: Gwei
    exit_balance_to_consume: Gwei  # Should be initialized with get_validator_churn_limit(state)
    earliest_exit_epoch: Epoch  # Should be initialized with the max([v.exit_epoch for v in state.validators if v.exit_epoch != FAR_FUTURE_EPOCH]) + 1
    pending_balance_deposits: List[PendingBalanceDeposit, 100000]
    pending_partial_withdrawals: List[PartialWithdrawal, 100000]
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

####  updated  `is_partially_withdrawable_validator`
*Note*: now calls `has_compounding_withdrawal_credential` and gets ceiling from `get_balance_ceiling`.

```python
def is_partially_withdrawable_validator(validator: Validator, balance: Gwei) -> bool:
    """
    Check if ``validator`` is partially withdrawable.
    """
    if not (has_eth1_withdrawal_credential(validator) or has_compounding_withdrawal_credential(validator)):
        return False
    return get_validator_excess_balance(validator, balance) > 0
```


### Beacon state accessors


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

#### updated  `get_validator_churn_limit`

*Note*: updated to return a Gwei amount of amount of churn per epoch.

```python
def get_validator_churn_limit(state: BeaconState) -> Gwei:
    churn = max(MIN_PER_EPOCH_CHURN_LIMIT * MIN_ACTIVATION_BALANCE, get_total_active_balance(state) // CHURN_LIMIT_QUOTIENT)
    return churn - churn % EFFECTIVE_BALANCE_INCREMENT
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
    exit_queue_epoch = compute_exit_epoch_and_update_churn(state, validator.effective_balance)

    # Set validator exit epoch and withdrawable epoch
    validator.exit_epoch = exit_queue_epoch
    validator.withdrawable_epoch = Epoch(validator.exit_epoch + MIN_VALIDATOR_WITHDRAWABILITY_DELAY)
```

#### new `compute_exit_epoch_and_update_churn`


```python
def compute_exit_epoch_and_update_churn(state: BeaconState, exit_balance: Gwei) -> Epoch:
    earliest_exit_epoch = compute_activation_exit_epoch(get_current_epoch(state))
    per_epoch_churn = get_validator_churn_limit(state)
    # New epoch for exits.
    if state.earliest_exit_epoch < earliest_exit_epoch:
        state.earliest_exit_epoch = earliest_exit_epoch
        state.exit_balance_to_consume = per_epoch_churn

    # Exit fits in the current earliest epoch.
    if exit_balance <= state.exit_balance_to_consume:
        state.exit_balance_to_consume -= exit_balance
    else: # Exit doesn't fit in the current earliest epoch.
        balance_to_process = exit_balance - state.exit_balance_to_consume
        additional_epochs, remainder = divmod(balance_to_process, per_epoch_churn)
        state.earliest_exit_epoch += additional_epochs + 1
        state.exit_balance_to_consume = per_epoch_churn - remainder
    return state.earliest_exit_epoch
```

## Beacon chain state transition function
### Epoch processing

#### updated `process_epoch`
```python
def process_epoch(state: BeaconState) -> None:
    process_justification_and_finalization(state)
    process_inactivity_updates(state)
    process_rewards_and_penalties(state)
    process_registry_updates(state)
    process_slashings(state)
    process_eth1_data_reset(state)
    process_pending_balance_deposits(state) # New
    process_effective_balance_updates(state)
    process_slashings_reset(state)
    process_randao_mixes_reset(state)
```

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

    # Activate all eligible validators
    activation_epoch = compute_activation_exit_epoch(get_current_epoch(state))
    for validator in state.validators:
        if is_eligible_for_activation(state, validator):
            validator.activation_epoch = activation_epoch
```

#### new `process_pending_balance_deposits`

```python
def process_pending_balance_deposits(state: BeaconState) -> None:
    state.deposit_balance_to_consume += get_validator_churn_limit(state)
    next_pending_deposit_index = 0
    for pending_balance_deposit in state.pending_balance_deposits:
        if state.deposit_balance_to_consume < pending_balance_deposit.amount:
            break

        state.deposit_balance_to_consume -= pending_balance_deposit.amount
        increase_balance(state, pending_balance_deposit.index, pending_balance_deposit.amount)
        next_pending_deposit_index += 1

    state.pending_balance_deposits = state.pending_balance_deposits[next_pending_deposit_index:]
```

#### updated `process_effective_balance_updates`

```python
def process_effective_balance_updates(state: BeaconState) -> None:
    # Update effective balances with hysteresis
    for index, validator in enumerate(state.validators):
        balance = state.balances[index]
        HYSTERESIS_INCREMENT = uint64(EFFECTIVE_BALANCE_INCREMENT // HYSTERESIS_QUOTIENT)
        DOWNWARD_THRESHOLD = HYSTERESIS_INCREMENT * HYSTERESIS_DOWNWARD_MULTIPLIER
        UPWARD_THRESHOLD = HYSTERESIS_INCREMENT * HYSTERESIS_UPWARD_MULTIPLIER
        EFFECTIVE_BALANCE_LIMIT = MAX_EFFECTIVE_BALANCE_MAXEB if has_compounding_withdrawal_credential(validator) else MIN_ACTIVATION_BALANCE
        if (
            balance + DOWNWARD_THRESHOLD < validator.effective_balance
            or validator.effective_balance + UPWARD_THRESHOLD < balance
        ):
            validator.effective_balance = min(balance - balance % EFFECTIVE_BALANCE_INCREMENT, EFFECTIVE_BALANCE_LIMIT)
```

### Block processing

#### updated `process_operations`

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
    for_ops(body.execution_payload.withdraw_request, process_execution_layer_withdraw_request) # New
```

#### new `process_execution_layer_withdraw_request`

```python
def process_execution_layer_withdraw_request(
        state: BeaconState,
        execution_layer_withdraw_request: ExecutionLayerWithdrawRequest
    ) -> None:
    validator_pubkeys = [v.pubkey for v in state.validators]
    validator_index = ValidatorIndex(validator_pubkeys.index(execution_layer_withdraw_request.validator_pubkey))
    validator = state.validators[validator_index]

    # Same conditions as in EIP7002 https://github.com/ethereum/consensus-specs/pull/3349/files#diff-7a6e2ba480d22d8bd035bd88ca91358456caf9d7c2d48a74e1e900fe63d5c4f8R223
    # Verify withdrawal credentials
    is_execution_address = validator.withdrawal_credentials[:1] == ETH1_ADDRESS_WITHDRAWAL_PREFIX
    is_correct_source_address = validator.withdrawal_credentials[12:] == execution_layer_withdraw_request.source_address
    if not (is_execution_address and is_correct_source_address):
        return
    # Verify the validator is active
    if not is_active_validator(validator, get_current_epoch(state)):
        return
    # Verify exit has not been initiated, and slashed
    if validator.exit_epoch != FAR_FUTURE_EPOCH:
        return
    # Verify the validator has been active long enough
    if get_current_epoch(state) < validator.activation_epoch + SHARD_COMMITTEE_PERIOD:
        return

    pending_balance_to_withdraw = sum(item.amount for item in state.pending_partial_withdrawals if item.index == validator_index)
    amount = execution_layer_withdraw_request.amount
    # amount = 0 indicates an exit, but only exit if there are no other pending withdrawals
    if amount == 0 and pending_balance_to_withdraw == 0:
        initiate_validator_exit(state, validator_index)
    elif state.balances[validator_index] > MIN_ACTIVATION_BALANCE + pending_balance_to_withdraw:
        to_withdraw = min(state.balances[validator_index] - MIN_ACTIVATION_BALANCE - pending_balance_to_withdraw, amount)
        exit_queue_epoch = compute_exit_epoch_and_update_churn(state, to_withdraw)
        withdrawable_epoch = Epoch(exit_queue_epoch + MIN_VALIDATOR_WITHDRAWABILITY_DELAY)
        state.pending_partial_withdrawals.append(PartialWithdrawal(
            index=validator_index,
            amount=to_withdraw,
            withdrawable_epoch=withdrawable_epoch,
        ))
```

####  updated  `get_expected_withdrawals`

```python
def get_expected_withdrawals(state: BeaconState) -> Sequence[Withdrawal]:
    epoch = get_current_epoch(state)
    withdrawal_index = state.next_withdrawal_index
    validator_index = state.next_withdrawal_validator_index
    withdrawals: List[Withdrawal] = []
    consumed = 0
    for withdrawal in state.pending_partial_withdrawals:
        if withdrawal.withdrawable_epoch > epoch or len(withdrawals) == MAX_WITHDRAWALS_PER_PAYLOAD // 2:
            break

        validator = state.validators[withdrawal.index]
        if validator.exit_epoch == FAR_FUTURE_EPOCH and state.balances[withdrawal.index] > MIN_ACTIVATION_BALANCE:
            withdrawable_balance = min(state.balances[withdrawal.index] - MIN_ACTIVATION_BALANCE, withdrawal.amount)
            withdrawals.append(Withdrawal(
                index=withdrawal_index,
                validator_index=withdrawal.index,
                address=ExecutionAddress(validator.withdrawal_credentials[12:]),
                amount=withdrawable_balance,
            ))
            withdrawal_index += WithdrawalIndex(1)
            consumed += 1

    state.pending_partial_withdrawals = state.pending_partial_withdrawals[consumed:] 

    # Sweep for remaining.
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
                amount=get_validator_excess_balance(validator, balance),
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
    validator_pubkeys = [validator.pubkey for validator in state.validators]
    if pubkey not in validator_pubkeys:
        # Verify the deposit signature (proof of possession) which is not checked by the deposit contract
        deposit_message = DepositMessage(
            pubkey=pubkey,
            withdrawal_credentials=withdrawal_credentials,
            amount=amount,
        )
        domain = compute_domain(DOMAIN_DEPOSIT)  # Fork-agnostic domain since deposits are valid across forks
        signing_root = compute_signing_root(deposit_message, domain)
        # Initialize validator if the deposit signature is valid
        if bls.Verify(pubkey, signing_root, signature):
            state.validators.append(get_validator_from_deposit(pubkey, withdrawal_credentials))
            state.balances.append(0)
            # [New in Altair]
            state.previous_epoch_participation.append(ParticipationFlags(0b0000_0000))
            state.current_epoch_participation.append(ParticipationFlags(0b0000_0000))
            state.inactivity_scores.append(uint64(0))
            index = len(state.validators) - 1
            state.pending_balance_deposits.append(PendingBalanceDeposit(index=index, amount=amount))
    else:
        index = ValidatorIndex(validator_pubkeys.index(pubkey))
        state.pending_balance_deposits.append(PendingBalanceDeposit(index=index, amount=amount))
```

#### updated `get_validator_from_deposit`

```python
def get_validator_from_deposit(pubkey: BLSPubkey, withdrawal_credentials: Bytes32) -> Validator:
    return Validator(
        pubkey=pubkey,
        withdrawal_credentials=withdrawal_credentials,
        activation_eligibility_epoch=FAR_FUTURE_EPOCH,
        activation_epoch=FAR_FUTURE_EPOCH,
        exit_epoch=FAR_FUTURE_EPOCH,
        withdrawable_epoch=FAR_FUTURE_EPOCH,
        effective_balance=0,
    )
```