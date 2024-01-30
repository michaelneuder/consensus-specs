# EIP7251 -- Networking

This document contains the networking specification for EIP7251.

The specification of these changes continues in the same format as the network specifications of previous upgrades, and assumes them as pre-requisite.

### Table of contents

<!-- TOC -->
<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->

- [Modifications in EIP7251](#modifications-in-eip7251)
  - [The gossip domain: gossipsub](#the-gossip-domain-gossipsub)
    - [Topics and messages](#topics-and-messages)
      - [Global topics](#global-topics)
        - [`consolidation`](#consolidation)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->
<!-- /TOC -->


## Modifications in EIP7251

### The gossip domain: gossipsub

A new topic is added to support the gossip of signed consolidation messages.

#### Topics and messages

Topics follow the same specification as in prior upgrades. All existing topics remain stable.

The new topics along with the type of the `data` field of a gossipsub message are given in this table:

| Name | Message Type |
| - | - |
| `consolidation` | `SignedConsolidation` |


##### Global topics

EIP7251 adds one global topic to propagate signed consolidation messages to all potential proposers of beacon blocks.

###### `consolidation`

This topic is used to propagate signed consolidation messages to be included in future blocks.

The following validations MUST pass before forwarding the `signed_consolidation` on the network:

- _[IGNORE]_ `current_epoch >= EIP_7251_FORK_EPOCH`,
  where `current_epoch` is defined by the current wall-clock time.
- _[IGNORE]_ The `signed_consolidation` is the first valid signed consolidation received
  for the validator with index `signed_consolidation.message.source_index`.
- _[REJECT]_ All of the conditions within `process_consolidation` pass validation.

