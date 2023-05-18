# [DRAFT] `MAX_EFFECTIVE_BALANCE` increase - Honest Validator

## Table of contents

<!-- TOC -->
<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->

- [Introduction](#introduction)
- [Prerequisites](#prerequisites)
- [Beacon chain responsibilities](#beacon-chain-responsibilities)
  - [Attestation aggregation](#attestation-aggregation)
    - [Aggregation Selection](#aggregation-selection)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->
<!-- /TOC -->

## Introduction

This document represents the changes to be made in the code of an "honest validator" to implement executable beacon chain proposal.

## Prerequisites

This document is an extension of the [Deneb -- Honest Validator](../deneb/validator.md) guide.
All behaviors and definitions defined in this document, and documents it extends, carry over unless explicitly noted or overridden.

## Beacon chain responsibilities

### Attestation aggregation

#### Aggregation Selection

*Note*: updated to be weight dependent. See [Security considerations](https://notes.ethereum.org/@fradamt/meb-increase-security) for more details.
```python
def is_aggregator(state: BeaconState, slot: Slot, index: CommitteeIndex, validator_index: ValidatorIndex, slot_signature: BLSSignature) -> bool:
    validator = state.validators[validator_index]
    committee = get_beacon_committee(state, slot, index)
    number_virtual_validators = validator.effective_balance // MIN_ACTIVATION_BALANCE
    committee_balance = get_total_balance(state, set(committee))
    denominator = committee_balance ** number_virtual_validators
    numerator = denominator - 
    (committee_balance -  TARGET_AGGREGATORS_PER_COMMITTEE * MIN_ACTIVATION_BALANCE) 
    ** number_virtual_validators
    modulo = denominator // numerator
    return bytes_to_uint64(hash(slot_signature)[0:8]) % modulo == 0
```