# Domain model direction

This document records the initial bounded contexts. The actual PostgreSQL migrations are
created after the field and provenance rules are reviewed.

## Catalogue

- Country
- Park
- Manufacturer
- Coaster model
- Coaster
- Element
- Coaster element occurrence

## Provenance

- Source
- Source snapshot
- Extracted fact
- Fact proposal
- Proposal review
- Canonical change
- Audit event

## Identity and access

- User
- Role
- Organisation
- API consumer
- API credential
- Access plan
- Usage event

## Core distinction

A source statement, an extracted value, a proposed value and a canonical value are
different objects. They must not be collapsed into one mutable database column without
history.

