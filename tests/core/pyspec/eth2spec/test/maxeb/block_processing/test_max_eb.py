from eth2spec.test.context import (
    spec_state_test,
    with_maxeb_and_later,
)

#  ********************
#  * EXIT QUEUE TESTS *
#  ********************

@with_maxeb_and_later
@spec_state_test
def test_exit_queue_churn_32eth_validators(spec, state):
    # This state has 64 validators each with 32 ETH
    single_validator_balance = spec.MIN_ACTIVATION_BALANCE
    expected_exit_epoch = spec.compute_activation_exit_epoch(spec.get_current_epoch(state))
    
    # Withdraw validators, all which fit in the churn limit
    for i in range(spec.config.MIN_PER_EPOCH_CHURN_LIMIT):
        validator_index = i
        spec.initiate_validator_exit(state, validator_index)
        # Check exit queue churn is set
        assert state.exit_queue_churn == single_validator_balance * (i + 1)
        # Check exit epoch
        assert state.validators[validator_index].exit_epoch == expected_exit_epoch

    # Withdraw an additional validator, doesn't fit in the churn limit, so exit
    # epoch is incremented
    validator_index = spec.config.MIN_PER_EPOCH_CHURN_LIMIT
    spec.initiate_validator_exit(state, validator_index)
    # Check exit epoch
    assert state.validators[validator_index].exit_epoch == expected_exit_epoch + 1
    # Check exit queue churn is set
    assert state.exit_queue_churn == single_validator_balance


@with_maxeb_and_later
@spec_state_test
def test_exit_queue_churn_large_validator(spec, state):
    cl = spec.get_validator_churn_limit(state)
    assert cl == spec.MIN_ACTIVATION_BALANCE * spec.config.MIN_PER_EPOCH_CHURN_LIMIT

    # Set 0th validator effective balance to 2048 ETH
    state.validators[0].effective_balance = spec.MAX_EFFECTIVE_BALANCE_MAXEB

    expected_exit_epoch = spec.compute_activation_exit_epoch(spec.get_current_epoch(state))
    # Validator consumes exit churn for an additional 16 epochs
    expected_exit_epoch += spec.MAX_EFFECTIVE_BALANCE_MAXEB // cl

    validator_index = 0
    spec.initiate_validator_exit(state, validator_index)
    # Check exit epoch
    assert state.validators[validator_index].exit_epoch == expected_exit_epoch
    # Check exit queue churn is 0
    assert state.exit_queue_churn == 0


@with_maxeb_and_later
@spec_state_test
def test_exit_queue_churn_large_validator_existing_churn(spec, state):
    cl = spec.get_validator_churn_limit(state)
    assert cl == spec.MIN_ACTIVATION_BALANCE * spec.config.MIN_PER_EPOCH_CHURN_LIMIT

    # Set the churn to 1 ETH
    state.exit_queue_churn = 1000000000

    # Set 0th validator effective balance to the churn limit
    state.validators[0].effective_balance = cl

    expected_exit_epoch = spec.compute_activation_exit_epoch(spec.get_current_epoch(state))
    # The existing 1 ETH churn will push an extra epoch
    expected_exit_epoch += 1

    validator_index = 0
    spec.initiate_validator_exit(state, validator_index)
    # Check exit epoch
    assert state.validators[validator_index].exit_epoch == expected_exit_epoch
    # Check exit queue churn is the remainder 1 ETH
    assert state.exit_queue_churn == 1000000000


@with_maxeb_and_later
@spec_state_test
def test_exit_queue_churn_large_validator_existing_churn_2epochs(spec, state):
    cl = spec.get_validator_churn_limit(state)
    assert cl == spec.MIN_ACTIVATION_BALANCE * spec.config.MIN_PER_EPOCH_CHURN_LIMIT

    # Set the churn to 1 ETH.
    state.exit_queue_churn = 1000000000

    # Set 0th validator effective balance to the churn limit
    state.validators[0].effective_balance = 2*cl

    expected_exit_epoch = spec.compute_activation_exit_epoch(spec.get_current_epoch(state))
    # Two extra epochs will be necessary
    expected_exit_epoch += 2

    validator_index = 0
    spec.initiate_validator_exit(state, validator_index)
    # Check exit epoch
    assert state.validators[validator_index].exit_epoch == expected_exit_epoch
    # Check exit queue churn is the remainder 1 ETH
    assert state.exit_queue_churn == 1000000000
    


#  **************************
#  * ACTIVATION QUEUE TESTS *
#  **************************

def mark_validators_eligible_for_activation(spec, state):
    for v in state.validators:
        v.activation_eligibility_epoch = 0
        v.activation_epoch = spec.FAR_FUTURE_EPOCH

@with_maxeb_and_later
@spec_state_test
def test_activation_queue_churn_32eth_validators(spec, state):
    mark_validators_eligible_for_activation(spec, state)

    expected_activation_epoch = spec.compute_activation_exit_epoch(spec.get_current_epoch(state))
    
    # Activate validators, 4 should fit
    spec.process_registry_updates(state)

    for i in range(spec.config.MIN_PER_EPOCH_CHURN_LIMIT):
        # Check exit epoch
        assert state.validators[i].activation_epoch == expected_activation_epoch
    
    # Check activation validator balance is 0
    assert state.activation_validator_balance == 0

    # Check that the next validator has not been dequeued
    assert state.validators[spec.config.MIN_PER_EPOCH_CHURN_LIMIT+1].activation_epoch == spec.FAR_FUTURE_EPOCH

@with_maxeb_and_later
@spec_state_test
def test_activation_queue_churn_large_validator(spec, state):
    mark_validators_eligible_for_activation(spec, state)

    cl = spec.get_validator_churn_limit(state)
    assert cl == spec.MIN_ACTIVATION_BALANCE * spec.config.MIN_PER_EPOCH_CHURN_LIMIT

    # Set 0th validator effective balance to 2048 ETH
    state.validators[0].effective_balance = spec.MAX_EFFECTIVE_BALANCE_MAXEB

    # Process updates, should just consume the churn limit
    assert state.activation_validator_balance == 0
    spec.process_registry_updates(state)
    assert state.activation_validator_balance == cl
    # Activation epoch should not be set
    assert state.validators[0].activation_epoch == spec.FAR_FUTURE_EPOCH

    # Validator consumes activation churn for an additional 16 epochs
    activation_epochs_consumed = spec.MAX_EFFECTIVE_BALANCE_MAXEB // cl
    for i in range(1, activation_epochs_consumed-1):
        spec.process_registry_updates(state)
   
    # Balance should be one churn limit away
    assert state.activation_validator_balance == cl * (activation_epochs_consumed-1)
    # Activation epoch should still not be set
    assert state.validators[0].activation_epoch == spec.FAR_FUTURE_EPOCH

    # Process updates, dequeues the validator
    spec.process_registry_updates(state)
    assert state.activation_validator_balance == 0
    # Activation epoch is now set
    assert state.validators[0].activation_epoch == spec.compute_activation_exit_epoch(spec.get_current_epoch(state))

    # Check that the next validator has not been dequeued
    assert state.validators[1].activation_epoch == spec.FAR_FUTURE_EPOCH

@with_maxeb_and_later
@spec_state_test
def test_activation_queue_churn_existing_churn(spec, state):
    mark_validators_eligible_for_activation(spec, state)

    cl = spec.get_validator_churn_limit(state)
    assert cl == spec.MIN_ACTIVATION_BALANCE * spec.config.MIN_PER_EPOCH_CHURN_LIMIT

    # Set 0th validator effective balance to churn limit + 1
    state.validators[0].effective_balance = cl + 1000000000
    # Set the activation validator balance to 1 ETH.
    state.activation_validator_balance = 1000000000

    # Process updates, should activate the validator
    spec.process_registry_updates(state)
    assert state.activation_validator_balance == 0
    # Activation epoch should be set
    assert state.validators[0].activation_epoch == spec.compute_activation_exit_epoch(spec.get_current_epoch(state))

    # Check that the next validator has not been dequeued
    assert state.validators[1].activation_epoch == spec.FAR_FUTURE_EPOCH