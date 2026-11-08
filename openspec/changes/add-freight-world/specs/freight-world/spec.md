# freight-in-the-fog world

## ADDED Requirements

### Requirement: world graph integrity

the world maintains a connected graph of depots and hubs with routes as edges.

#### Scenario: initial world state

- **WHEN** the world initializes with the default freight-in-the-fog configuration
- **THEN** it SHALL have at least three depots (west, east, south), one hub (relay-a), and routes connecting them with all routes initially open.

### Requirement: freight item lifecycle

freight items move through states: pending → in-transit → delivered (or stuck).

#### Scenario: freight routing

- **WHEN** an agent commits a route_freight action for a freight item at its current location
- **THEN** the freight SHALL move to the next location along a valid open route toward its destination, and the delivery job status SHALL update to in-transit.

#### Scenario: freight delivery

- **WHEN** a freight item reaches its destination depot
- **THEN** the delivery job SHALL transition to delivered status and the freight SHALL be removed from the active world state.

### Requirement: route validation

actions that route freight MUST validate against current world state.

#### Scenario: legal move

- **WHEN** an agent proposes route_freight with via path that exists and is open
- **THEN** the action SHALL validate as legal and commit successfully.

#### Scenario: illegal move - closed route

- **WHEN** an agent proposes route_freight using a route that is closed
- **THEN** the action SHALL validate as illegal, reject with reason "route closed", and the freight SHALL NOT move.

#### Scenario: illegal move - invalid path

- **WHEN** an agent proposes route_freight with via path that does not exist in the graph
- **THEN** the action SHALL validate as illegal, reject with reason "invalid route", and the freight SHALL NOT move.

### Requirement: partial observations

agents receive limited local views, not global state.

#### Scenario: agent observation scope

- **WHEN** an agent observes the world at turn n
- **THEN** it SHALL see only: (1) freight at its assigned depot(s), (2) routes incident to its assigned depot(s), (3) known closures within two hops, (4) pending requests at its assigned depot(s).

#### Scenario: observation determinism

- **WHEN** two runs use the same seed and turn number
- **THEN** the observation returned to agent X at turn n SHALL be byte-identical across runs.

### Requirement: capacity limits

hubs and depots have bounded capacity for holding freight.

#### Scenario: hub capacity

- **WHEN** a hub reaches its capacity limit
- **THEN** additional route_freight actions targeting that hub SHALL reject with reason "capacity exceeded" until freight moves out.

### Requirement: disturbance integration

the world SHALL integrate with the runner's disturbance scheduler.

#### Scenario: relay-loss effect on world

- **WHEN** relay-loss disturbance is applied to agent c at turn 8
- **THEN** agent c's messages SHALL be blocked (undelivered), but agent c's route_freight actions SHALL still validate and commit normally (communication loss does not stop local action).

### Requirement: delivery tracking

the world SHALL track delivery outcomes for analysis.

#### Scenario: delivery count

- **WHEN** the run ends at turn 16
- **THEN** the run.end event SHALL report deliveries_completed (count of delivered jobs) and deliveries_stuck (count of jobs not delivered by horizon).
