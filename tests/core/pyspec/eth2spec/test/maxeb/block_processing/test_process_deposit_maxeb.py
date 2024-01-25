from eth2spec.test.helpers.deposits import (
    build_deposit,
    prepare_state_and_deposit,
    run_deposit_processing_maxeb,
    run_deposit_processing_with_specific_fork_version,
    sign_deposit_data,
)
from eth2spec.test.helpers.keys import privkeys, pubkeys

from eth2spec.test.context import (
    spec_state_test,
    with_maxeb_and_later,
)

@with_maxeb_and_later
@spec_state_test
def test_new_deposit_under_min_activation_balance(spec, state):
    # fresh deposit = next validator index = validator appended to registry
    validator_index = len(state.validators)
    # effective balance will be 1 EFFECTIVE_BALANCE_INCREMENT smaller because of this small decrement.
    amount = spec.MIN_ACTIVATION_BALANCE - 1
    deposit = prepare_state_and_deposit(spec, state, validator_index, amount, signed=True)

    yield from run_deposit_processing_maxeb(spec, state, deposit, validator_index)

@with_maxeb_and_later
@spec_state_test
def test_new_deposit_min(spec, state):
    # fresh deposit = next validator index = validator appended to registry
    validator_index = len(state.validators)
    amount = spec.MIN_DEPOSIT_AMOUNT
    deposit = prepare_state_and_deposit(spec, state, validator_index, amount, signed=True)
    yield from run_deposit_processing_maxeb(spec, state, deposit, validator_index)

@with_maxeb_and_later
@spec_state_test
def test_new_deposit_between_min_and_max(spec, state):
    # fresh deposit = next validator index = validator appended to registry
    validator_index = len(state.validators)
    amount = spec.MAX_EFFECTIVE_BALANCE_MAXEB // 2
    deposit = prepare_state_and_deposit(spec, state, validator_index, amount, signed=True)
    yield from run_deposit_processing_maxeb(spec, state, deposit, validator_index)


@with_maxeb_and_later
@spec_state_test
def test_new_deposit_max(spec, state):
    # fresh deposit = next validator index = validator appended to registry
    validator_index = len(state.validators)
    # effective balance will be exactly the same as balance.
    amount = spec.MAX_EFFECTIVE_BALANCE_MAXEB
    deposit = prepare_state_and_deposit(spec, state, validator_index, amount, signed=True)
    yield from run_deposit_processing_maxeb(spec, state, deposit, validator_index)


@with_maxeb_and_later
@spec_state_test
def test_new_deposit_over_max(spec, state):
    # fresh deposit = next validator index = validator appended to registry
    validator_index = len(state.validators)
    amount = spec.MAX_EFFECTIVE_BALANCE_MAXEB + 1
    deposit = prepare_state_and_deposit(spec, state, validator_index, amount, signed=True)
    yield from run_deposit_processing_maxeb(spec, state, deposit, validator_index)




# @with_maxeb_and_later
# @spec_state_test
# def test_top_up__max_effective_balance(spec, state):
#     validator_index = 0
#     amount = spec.MAX_EFFECTIVE_BALANCE_MAXEB // 4
#     deposit = prepare_state_and_deposit(spec, state, validator_index, amount, signed=True)

#     state.balances[validator_index] = spec.MAX_EFFECTIVE_BALANCE_MAXEB
#     state.validators[validator_index].effective_balance = spec.MAX_EFFECTIVE_BALANCE_MAXEB

#     yield from run_deposit_processing(spec, state, deposit, validator_index)

#     assert state.balances[validator_index] == spec.MAX_EFFECTIVE_BALANCE_MAXEB + amount
#     assert state.validators[validator_index].effective_balance == spec.MAX_EFFECTIVE_BALANCE_MAXEB