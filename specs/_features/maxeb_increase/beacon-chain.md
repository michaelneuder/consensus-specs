# [DRAFT] MAX_EFFECTIVE_BALANCE increase

## Table of contents

<!-- TOC -->
<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->

- [Introduction](#introduction)
- [Constants](#constants)
  - [Withdrawal prefixes](#withdrawal-prefixes)
- [Beacon chain state transition function](#beacon-chain-state-transition-function)
  - [Block processing](#block-processing)
    - [New `process_compounding_withdrawal`](#new-process_compounding_withdrawal)

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
| <span style="background-color: #FFFF00">updated</span> `MAX_EFFECTIVE_BALANCE` | `Gwei(2**11 * 10**9)` (= 2,048,000,000,000) (2048 ETH) |
| <span style="background-color: #FFFF00">new</span> `MIN_ACTIVATION_BALANCE` | `Gwei(2**5 * 10**9)` (= 32,000,000,000) (32 ETH) |

## Containers

### New containers

#### <span style="background-color: #FFFF00">new</span> `ExecutionToCompoundingChange`

```python
class ExecutionToCompoundingChange(Container):
    validator_index: ValidatorIndex
    balance_ceiling: uint16 # denominated in ETH, must be a power of 2 and less than 2^11.    
```

#### <span style="background-color: #FFFF00">new</span>  `SignedExecutionToCompoundingChange`

```python
class SignedExecutionToCompoundingChange(Container):
    message: ExecutionToCompoundingChange
    signature: BLSSignature
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


### Misc

#### <span style="background-color: #FFFF00">new</span>  `calculate_balance_ceiling`

```python
def calculate_balance_ceiling(validator: Validator) -> Gwei:
    """
    Return the shuffled index corresponding to ``seed`` (and ``index_count``).
    """
    if not has_compounding_withdrawal_credential(validator):
        return MIN_ACTIVATION_BALANCE
    # With compounding credential bytes [1-2] are the ceiling in ETH.
    return bytes_to_uint16(validator.withdrawal_credential[1:3]) * EFFECTIVE_BALANCE_INCREMENT
```

### Predicates

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

```python
def is_fully_withdrawable_validator(validator: Validator, balance: Gwei, epoch: Epoch) -> bool:
    """
    Check if ``validator`` is fully withdrawable.
    """
    return (
        has_withdrawalable_credential(validator)
        and validator.withdrawable_epoch <= epoch
        and balance > 0
    )
```

####  <span style="background-color: #FFFF00">updated</span>  `is_partially_withdrawable_validator`

```python
def is_partially_withdrawable_validator(validator: Validator, balance: Gwei) -> bool:
    """
    Check if ``validator`` is partially withdrawable.
    """
    if not has_withdrawable_credential(validator):
        return false
    
    ceiling = calculate_balance_ceiling(validator)
    has_ceiling_effective_balance = validator.effective_balance == ceiling
    has_excess_balance = balance > ceiling
    return has_withdrawable_credential(validator) and has_ceiling_effective_balance and has_excess_balance
```

## Beacon chain state transition function

### Block processing

####  <span style="background-color: #FFFF00">updated</span>  `get_expected_withdrawals`
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
            ceiling = calculate_balance_ceiling(validator)
            withdrawals.append(Withdrawal(
                index=withdrawal_index,
                validator_index=validator_index,
                address=ExecutionAddress(validator.withdrawal_credentials[12:]),
                amount=balance - ceiling,
            ))
            withdrawal_index += WithdrawalIndex(1)
        if len(withdrawals) == MAX_WITHDRAWALS_PER_PAYLOAD:
            break
        validator_index = ValidatorIndex((validator_index + 1) % len(state.validators))
    return withdrawals
```


#### <span style="background-color: #FFFF00">new</span>  `process_compounding_withdrawal`

```python
def process_compounding_withdrawal(state: BeaconState,
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