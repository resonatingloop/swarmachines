# freight-in-the-fog world specification

## overview

freight-in-the-fog is a graph-based delivery world with limited agent observations. agents coordinate to move freight items from origin depots to destination depots via a network of routes and hubs. the world tracks route status (open/closed), freight locations, and delivery completion.

## world state

the world consists of:
- **depots**: named locations (west, east, south, relay-a) where freight originates or terminates
- **hubs**: intermediate routing points (relay-a) that can hold freight temporarily
- **routes**: directed edges between depots/hubs with status (open/closed) and optional bridge identifier
- **freight items**: movable cargo with type (med-kit, supplies, equipment), origin, destination, and current location
- **delivery jobs**: records of requested deliveries with status (pending, in-transit, delivered, stuck)

## ADDED Requirements

### Requirement: World Graph Integrity

the world maintains a connected graph of depots and hubs with routes as edges.

#### Scenario: Initial World State

**WHEN** the world initializes with the default freight-in-the-fog configuration
**THEN** it SHALL have at least three depots (west, east, south), one hub (relay-a), and routes connecting them with all routes initially open.

### Requirement: Freight Item Lifecycle

freight items move through states: pending → in-transit → delivered (or stuck).

#### Scenario: Freight Routing

**WHEN** an agent commits a route_freight action for a freight item at its current location
**THEN** the freight SHALL move to the next location along a valid open route toward its destination, and the delivery job status SHALL update to in-transit.

#### Scenario: Freight Delivery

**WHEN** a freight item reaches its destination depot
**THEN** the delivery job SHALL transition to delivered status and the freight SHALL be removed from the active world state.

### Requirement: Route Validation

actions that route freight MUST validate against current world state.

#### Scenario: Legal Move

**WHEN** an agent proposes route_freight with via path that exists and is open
**THEN** the action SHALL validate as legal and commit successfully.

#### Scenario: Illegal Move - Closed Route

**WHEN** an agent proposes route_freight using a route that is closed
**THEN** the action SHALL validate as illegal, reject with reason "route closed", and the freight SHALL NOT move.

#### Scenario: Illegal Move - Invalid Path

**WHEN** an agent proposes route_freight with via path that does not exist in the graph
**THEN** the action SHALL validate as illegal, reject with reason "invalid route", and the freight SHALL NOT move.

### Requirement: Partial Observations

agents receive limited local views, not global state.

#### Scenario: Agent Observation Scope

**WHEN** an agent observes the world at turn n
**THEN** it SHALL see only: (1) freight at its assigned depot(s), (2) routes incident to its assigned depot(s), (3) known closures within two hops, (4) pending requests at its assigned depot(s).

#### Scenario: Observation Determinism

**WHEN** two runs use the same seed and turn number
**THEN** the observation returned to agent X at turn n SHALL be byte-identical across runs.

### Requirement: Capacity Limits

hubs and depots have bounded capacity for holding freight.

#### Scenario: Hub Capacity

**WHEN** a hub reaches its capacity limit
**THEN** additional route_freight actions targeting that hub SHALL reject with reason "capacity exceeded" until freight moves out.

### Requirement: Disturbance Integration

the world SHALL integrate with the runner's disturbance scheduler.

#### Scenario: Relay-Loss Effect on World

**WHEN** relay-loss disturbance is applied to agent c at turn 8
**THEN** agent c's messages SHALL be blocked (undelivered), but agent c's route_freight actions SHALL still validate and commit normally (communication loss does not stop local action).

### Requirement: Delivery Tracking

the world SHALL track delivery outcomes for analysis.

#### Scenario: Delivery Count

**WHEN** the run ends at turn 16
**THEN** the run.end event SHALL report deliveries_completed (count of delivered jobs) and deliveries_stuck (count of jobs not delivered by horizon).

## out of scope

- dynamic route closures (day-2 extension)
- multi-freight optimization (agents handle one freight at a time)
- scoring beyond delivery count
- agent learning or adaptation
