from eth2spec.test.helpers.constants import (MINIMAL, MAINNET)
from eth2spec.test.context import (
    spec_state_test,
    with_maxeb_and_later,
    with_presets, 
    always_bls,
    spec_test, single_phase,
    with_custom_state,
    scaled_churn_balances_exceed_activation_exit_churn_limit,
    default_activation_threshold,
)
from eth2spec.test.helpers.keys import pubkey_to_privkey
from eth2spec.test.helpers.consolidations import (
    run_consolidation_processing,
    sign_consolidation,
)
from eth2spec.test.helpers.withdrawals import (
    set_eth1_withdrawal_credential_with_balance,
    set_compounding_withdrawal_credential,
)

#  ***********************
#  * CONSOLIDATION TESTS *
#  ***********************

@with_maxeb_and_later
@with_custom_state(balances_fn=scaled_churn_balances_exceed_activation_exit_churn_limit, threshold_fn=default_activation_threshold)
@spec_test
@single_phase
@with_presets([MINIMAL])
def test_basic_consolidation(spec, state):
    # This state has 256 validators each with 32 ETH in MINIMAL preset, 128 ETH consolidation churn
    consolidation_churn_limit = spec.get_consolidation_churn_limit(state)
    # Set the consolidation balance to consume equal to churn limit
    state.consolidation_balance_to_consume = consolidation_churn_limit
    current_epoch = spec.get_current_epoch(state)
    source_index = spec.get_active_validator_indices(state, current_epoch)[0]
    target_index = spec.get_active_validator_indices(state, current_epoch)[1]
    source_privkey = pubkey_to_privkey[state.validators[source_index].pubkey]
    target_privkey = pubkey_to_privkey[state.validators[target_index].pubkey]

    # Set source and target withdrawal credentials to the same eth1 credential
    set_eth1_withdrawal_credential_with_balance(spec, state, source_index)
    set_eth1_withdrawal_credential_with_balance(spec, state, target_index)

    signed_consolidation = sign_consolidation(spec, state, 
                                             spec.Consolidation(epoch=current_epoch, source_index=source_index, target_index=target_index), 
                                             source_privkey, target_privkey)
    yield from run_consolidation_processing(spec, state, signed_consolidation)

    expected_exit_epoch = spec.compute_activation_exit_epoch(current_epoch)
    # Check consolidation churn is decremented correctly
    assert state.consolidation_balance_to_consume == consolidation_churn_limit  - spec.MIN_ACTIVATION_BALANCE
    # Check exit epoch
    assert state.validators[0].exit_epoch == expected_exit_epoch

@with_maxeb_and_later
@with_custom_state(balances_fn=scaled_churn_balances_exceed_activation_exit_churn_limit, threshold_fn=default_activation_threshold)
@spec_test
@single_phase
@with_presets([MINIMAL])
def test_consolidation_churn_limit_balance(spec, state):
    # This state has 256 validators each with 32 ETH in MINIMAL preset, 128 ETH consolidation churn
    consolidation_churn_limit = spec.get_consolidation_churn_limit(state)
    # Set the consolidation balance to consume equal to churn limit
    state.consolidation_balance_to_consume = consolidation_churn_limit
    current_epoch = spec.get_current_epoch(state)

    source_index = spec.get_active_validator_indices(state, current_epoch)[0]
    # Set source balance to consolidation churn limit
    state.balances[source_index] = consolidation_churn_limit
    target_index = spec.get_active_validator_indices(state, current_epoch)[1]
    source_privkey = pubkey_to_privkey[state.validators[source_index].pubkey]
    target_privkey = pubkey_to_privkey[state.validators[target_index].pubkey]

    # Set source and target withdrawal credentials to the same eth1 credential
    set_compounding_withdrawal_credential(spec, state, source_index)
    set_compounding_withdrawal_credential(spec, state, target_index)

    signed_consolidation = sign_consolidation(spec, state, 
                                             spec.Consolidation(epoch=current_epoch, source_index=source_index, target_index=target_index), 
                                             source_privkey, target_privkey)
    yield from run_consolidation_processing(spec, state, signed_consolidation)

    expected_exit_epoch = spec.compute_activation_exit_epoch(current_epoch)
    # Check consolidation churn is decremented correctly
    assert state.consolidation_balance_to_consume == 0
    # Check exit epoch
    assert state.validators[0].exit_epoch == expected_exit_epoch

@with_maxeb_and_later
@with_custom_state(balances_fn=scaled_churn_balances_exceed_activation_exit_churn_limit, threshold_fn=default_activation_threshold)
@spec_test
@single_phase
@with_presets([MINIMAL])
def test_consolidation_balance_larger_than_churn_limit(spec, state):
    # This state has 256 validators each with 32 ETH in MINIMAL preset, 128 ETH consolidation churn
    consolidation_churn_limit = spec.get_consolidation_churn_limit(state)
    # Set the consolidation balance to consume equal to churn limit
    state.consolidation_balance_to_consume = consolidation_churn_limit
    current_epoch = spec.get_current_epoch(state)

    source_index = spec.get_active_validator_indices(state, current_epoch)[0]
    # Set source balance higher than consolidation churn limit
    state.balances[source_index] = consolidation_churn_limit + 1
    target_index = spec.get_active_validator_indices(state, current_epoch)[1]
    source_privkey = pubkey_to_privkey[state.validators[source_index].pubkey]
    target_privkey = pubkey_to_privkey[state.validators[target_index].pubkey]

    # Set source and target withdrawal credentials to the same eth1 credential
    set_compounding_withdrawal_credential(spec, state, source_index)
    set_compounding_withdrawal_credential(spec, state, target_index)

    signed_consolidation = sign_consolidation(spec, state, 
                                             spec.Consolidation(epoch=current_epoch, source_index=source_index, target_index=target_index), 
                                             source_privkey, target_privkey)
    yield from run_consolidation_processing(spec, state, signed_consolidation)

    expected_exit_epoch = spec.compute_activation_exit_epoch(current_epoch) + 1
    # Check consolidation churn is decremented correctly
    assert state.consolidation_balance_to_consume == consolidation_churn_limit - 1
    # Check exit epoch
    assert state.validators[0].exit_epoch == expected_exit_epoch


@with_maxeb_and_later
@with_custom_state(balances_fn=scaled_churn_balances_exceed_activation_exit_churn_limit, threshold_fn=default_activation_threshold)
@spec_test
@single_phase
@with_presets([MINIMAL])
def test_consolidation_balance_twice_the_churn_limit(spec, state):
    # This state has 256 validators each with 32 ETH in MINIMAL preset, 128 ETH consolidation churn
    consolidation_churn_limit = spec.get_consolidation_churn_limit(state)
    # Set the consolidation balance to consume equal to churn limit
    state.consolidation_balance_to_consume = consolidation_churn_limit
    current_epoch = spec.get_current_epoch(state)

    source_index = spec.get_active_validator_indices(state, current_epoch)[0]
    target_index = spec.get_active_validator_indices(state, current_epoch)[1]
    source_privkey = pubkey_to_privkey[state.validators[source_index].pubkey]
    target_privkey = pubkey_to_privkey[state.validators[target_index].pubkey]

    # Set source and target withdrawal credentials to the same eth1 credential
    set_compounding_withdrawal_credential(spec, state, source_index)
    set_compounding_withdrawal_credential(spec, state, target_index)

    # Set source balance higher than consolidation churn limit
    state.balances[source_index] = 2 * consolidation_churn_limit

    signed_consolidation = sign_consolidation(spec, state, 
                                             spec.Consolidation(epoch=current_epoch, source_index=source_index, target_index=target_index), 
                                             source_privkey, target_privkey)
    yield from run_consolidation_processing(spec, state, signed_consolidation)

    # when exiting a multiple of the churn limit greater than 1, an extra exit epoch is added
    expected_exit_epoch = spec.compute_activation_exit_epoch(current_epoch) + 2
    assert state.validators[0].exit_epoch == expected_exit_epoch
    # since the earliest exit epoch moves to a new one, consolidation balance is back to full
    assert state.consolidation_balance_to_consume == consolidation_churn_limit



@with_maxeb_and_later
@with_custom_state(balances_fn=scaled_churn_balances_exceed_activation_exit_churn_limit, threshold_fn=default_activation_threshold)
@spec_test
@single_phase
@with_presets([MINIMAL])
def test_multiple_consolidations_below_churn(spec, state):
    # This state has 256 validators each with 32 ETH in MINIMAL preset, 128 ETH consolidation churn
    consolidation_churn_limit = spec.get_consolidation_churn_limit(state)
    # Set the consolidation balance to consume equal to churn limit
    state.consolidation_balance_to_consume = consolidation_churn_limit
    current_epoch = spec.get_current_epoch(state)

    yield "pre", state
    # Prepare a bunch of consolidations, based on the current state
    consolidations = []
    for i in  range(3):
        source_index = 2*i
        target_index = 2*i + 1
        source_privkey = pubkey_to_privkey[state.validators[source_index].pubkey]
        target_privkey = pubkey_to_privkey[state.validators[target_index].pubkey]
        # Set source and target withdrawal credentials to the same eth1 credential
        set_eth1_withdrawal_credential_with_balance(spec, state, source_index)
        set_eth1_withdrawal_credential_with_balance(spec, state, target_index)
        signed_consolidation = sign_consolidation(spec, state, 
                                             spec.Consolidation(epoch=current_epoch, source_index=source_index, target_index=target_index), 
                                             source_privkey, target_privkey)
        consolidations.append(signed_consolidation)

        # Now run all the consolidations
    for consolidation in consolidations:
        # the function yields data, but we are just interested in running it here, ignore yields.
        for _ in run_consolidation_processing(spec, state, consolidation):
            continue
        
    yield "post", state

    expected_exit_epoch = spec.compute_activation_exit_epoch(current_epoch)
    assert state.earliest_consolidation_epoch == expected_exit_epoch
    assert state.consolidation_balance_to_consume == consolidation_churn_limit  - 3*spec.MIN_ACTIVATION_BALANCE
    for i in range(3):
        assert state.validators[2*i].exit_epoch == expected_exit_epoch


@with_maxeb_and_later
@with_custom_state(balances_fn=scaled_churn_balances_exceed_activation_exit_churn_limit, threshold_fn=default_activation_threshold)
@spec_test
@single_phase
@with_presets([MINIMAL])
def test_multiple_consolidations_equal_churn(spec, state):
    # This state has 256 validators each with 32 ETH in MINIMAL preset, 128 ETH consolidation churn
    consolidation_churn_limit = spec.get_consolidation_churn_limit(state)
    # Set the consolidation balance to consume equal to churn limit
    state.consolidation_balance_to_consume = consolidation_churn_limit
    current_epoch = spec.get_current_epoch(state)

    yield "pre", state
    # Prepare a bunch of consolidations, based on the current state
    consolidations = []
    for i in  range(4):
        source_index = 2*i
        target_index = 2*i + 1
        source_privkey = pubkey_to_privkey[state.validators[source_index].pubkey]
        target_privkey = pubkey_to_privkey[state.validators[target_index].pubkey]
        # Set source and target withdrawal credentials to the same eth1 credential
        set_eth1_withdrawal_credential_with_balance(spec, state, source_index)
        set_eth1_withdrawal_credential_with_balance(spec, state, target_index)
        signed_consolidation = sign_consolidation(spec, state, 
                                             spec.Consolidation(epoch=current_epoch, source_index=source_index, target_index=target_index), 
                                             source_privkey, target_privkey)
        consolidations.append(signed_consolidation)

        # Now run all the consolidations
    for consolidation in consolidations:
        # the function yields data, but we are just interested in running it here, ignore yields.
        for _ in run_consolidation_processing(spec, state, consolidation):
            continue
        
    yield "post", state

    expected_exit_epoch = spec.compute_activation_exit_epoch(current_epoch)
    assert state.earliest_consolidation_epoch == expected_exit_epoch
    assert state.consolidation_balance_to_consume == 0
    for i in range(4):
        assert state.validators[2*i].exit_epoch == expected_exit_epoch


@with_maxeb_and_later
@with_custom_state(balances_fn=scaled_churn_balances_exceed_activation_exit_churn_limit, threshold_fn=default_activation_threshold)
@spec_test
@single_phase
@with_presets([MINIMAL])
def test_multiple_consolidations_above_churn(spec, state):
    # This state has 256 validators each with 32 ETH in MINIMAL preset, 128 ETH consolidation churn
    consolidation_churn_limit = spec.get_consolidation_churn_limit(state)
    # Set the consolidation balance to consume equal to churn limit
    state.consolidation_balance_to_consume = consolidation_churn_limit
    current_epoch = spec.get_current_epoch(state)

    # Prepare a bunch of consolidations, based on the current state
    consolidations = []
    for i in  range(4):
        source_index = 2*i
        target_index = 2*i + 1
        source_privkey = pubkey_to_privkey[state.validators[source_index].pubkey]
        target_privkey = pubkey_to_privkey[state.validators[target_index].pubkey]
        # Set source and target withdrawal credentials to the same eth1 credential
        set_eth1_withdrawal_credential_with_balance(spec, state, source_index)
        set_eth1_withdrawal_credential_with_balance(spec, state, target_index)
        signed_consolidation = sign_consolidation(spec, state, 
                                             spec.Consolidation(epoch=current_epoch, source_index=source_index, target_index=target_index), 
                                             source_privkey, target_privkey)
        consolidations.append(signed_consolidation)

        # Now run all the consolidations
    for consolidation in consolidations:
        # the function yields data, but we are just interested in running it here, ignore yields.
        for _ in run_consolidation_processing(spec, state, consolidation):
            continue

    # consolidate an additional validator
    source_index = spec.get_active_validator_indices(state, current_epoch)[-2]
    target_index = spec.get_active_validator_indices(state, current_epoch)[-1]
    source_privkey = pubkey_to_privkey[state.validators[source_index].pubkey]
    target_privkey = pubkey_to_privkey[state.validators[target_index].pubkey]

    # Set source and target withdrawal credentials to the same eth1 credential
    set_eth1_withdrawal_credential_with_balance(spec, state, source_index)
    set_eth1_withdrawal_credential_with_balance(spec, state, target_index)

    signed_consolidation = sign_consolidation(spec, state, 
                                             spec.Consolidation(epoch=current_epoch, source_index=source_index, target_index=target_index), 
                                             source_privkey, target_privkey)
    # This is the interesting part of the test: on a pre-state with full consolidation queue,
    #  when processing an additional consolidation, it results in an exit in a later epoch
    yield from run_consolidation_processing(spec, state, signed_consolidation)

    expected_exit_epoch = spec.compute_activation_exit_epoch(current_epoch)
    assert state.earliest_consolidation_epoch == expected_exit_epoch + 1
    assert state.consolidation_balance_to_consume == consolidation_churn_limit  - spec.MIN_ACTIVATION_BALANCE
    assert state.validators[source_index].exit_epoch == expected_exit_epoch + 1
    for i in range(4):
        assert state.validators[2*i].exit_epoch == expected_exit_epoch


@with_maxeb_and_later
@with_custom_state(balances_fn=scaled_churn_balances_exceed_activation_exit_churn_limit, threshold_fn=default_activation_threshold)
@spec_test
@single_phase
@with_presets([MINIMAL])
def test_multiple_consolidations_equal_twice_churn(spec, state):
    # This state has 256 validators each with 32 ETH in MINIMAL preset, 128 ETH consolidation churn
    consolidation_churn_limit = spec.get_consolidation_churn_limit(state)
    # Set the consolidation balance to consume equal to churn limit
    state.consolidation_balance_to_consume = consolidation_churn_limit
    current_epoch = spec.get_current_epoch(state)

    yield "pre", state
    # Prepare a bunch of consolidations, based on the current state
    consolidations = []
    for i in  range(8):
        source_index = 2*i
        target_index = 2*i + 1
        source_privkey = pubkey_to_privkey[state.validators[source_index].pubkey]
        target_privkey = pubkey_to_privkey[state.validators[target_index].pubkey]
        # Set source and target withdrawal credentials to the same eth1 credential
        set_eth1_withdrawal_credential_with_balance(spec, state, source_index)
        set_eth1_withdrawal_credential_with_balance(spec, state, target_index)
        signed_consolidation = sign_consolidation(spec, state, 
                                             spec.Consolidation(epoch=current_epoch, source_index=source_index, target_index=target_index), 
                                             source_privkey, target_privkey)
        consolidations.append(signed_consolidation)

        # Now run all the consolidations
    for consolidation in consolidations:
        # the function yields data, but we are just interested in running it here, ignore yields.
        for _ in run_consolidation_processing(spec, state, consolidation):
            continue
        
    yield "post", state

    first_exit_epoch = spec.compute_activation_exit_epoch(current_epoch)
    assert state.consolidation_balance_to_consume == 0
    assert state.earliest_consolidation_epoch == first_exit_epoch + 1
    for i in range(4):
        assert state.validators[2*i].exit_epoch == first_exit_epoch
    for i in range(4,8):
        assert state.validators[2*i].exit_epoch == first_exit_epoch + 1


