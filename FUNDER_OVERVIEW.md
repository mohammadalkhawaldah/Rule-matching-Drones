# Rule-Matching Drones

## Project Summary

Rule-Matching Drones is a decentralized multi-UAV control system that converts a plain-language mission request into coordinated swarm behavior.

The project is designed for environments where:

- one operator must task multiple drones quickly
- communication may be degraded or intermittent
- central assignment should not be the only decision point
- the system must be transferable from simulation into real hardware

The core idea is simple:

1. the operator states the mission in natural language
2. the system converts that request into structured mission intent
3. required swarm roles are generated deterministically
4. each drone evaluates its own suitability locally
5. the swarm executes through a decentralized control architecture

## Why This Matters

Most practical multi-drone systems still depend heavily on centralized planning, centralized assignment, or brittle human configuration. That creates problems when:

- the number of drones increases
- mission conditions change quickly
- communication links degrade
- operators are under time pressure

This project targets a more resilient model:

- natural-language mission entry for the human operator
- deterministic machine interpretation of mission intent
- distributed role execution
- architecture aligned with future hardware deployment

Potential use cases include:

- infrastructure inspection
- corridor patrol
- search operations
- overwatch and communications relay
- agricultural or rural monitoring

## Technical Approach

The system is built in stages.

### 1. Mission Understanding

The operator provides a statement such as:

> Deploy four drones to patrol the pipeline corridor and monitor for suspicious activity.

The system converts that into structured mission data, including:

- mission type
- environment
- location
- required number of drones
- mission objective
- preferred roles

### 2. Role Generation

The mission is transformed into explicit swarm roles, for example:

- `corridor_patrol_A`
- `corridor_patrol_B`
- `overwatch`
- `relay`

Each role includes clear capability requirements.

### 3. Local Drone Reasoning

Each drone is modeled as an autonomous agent with its own:

- capabilities
- feasible roles
- local execution path

This preserves decentralization by avoiding a single global selector for all downstream behavior.

### 4. Matching and Execution

The current implementation supports:

- deterministic role matching
- ArduPilot SITL execution
- QGroundControl monitoring
- MAVSDK-based role execution
- communication separation between monitoring and control

## Communication Architecture

The communication stack was intentionally separated into distinct planes.

### Ground Monitoring Plane

- QGroundControl monitors the swarm through MAVLink UDP telemetry
- multiple vehicles are visible simultaneously in QGC

### Control Plane

- each drone has its own dedicated MAVSDK control sidecar
- the operator binds to fixed per-drone control endpoints
- control is not multiplexed through one shared unstable path

### Swarm Logic Plane

- mission parsing, role generation, and decentralized role reasoning are handled in the project codebase
- the communication setup is designed to support transition toward real companion-computer deployment

This separation is important because it mirrors how a hardware-capable system should be engineered:

- one path for situational awareness
- one path for vehicle control
- one logic layer for autonomy

## Current Validation Status

The project has already demonstrated the following in simulation:

- natural-language mission parsing into structured mission JSON
- deterministic role generation
- local role-feasibility reasoning for a heterogeneous fleet
- decentralized role assignment logic
- simultaneous display of multiple simulated drones in QGroundControl
- successful single-drone movement using ArduPilot SITL, QGC, and dedicated MAVSDK control sidecars
- successful multi-drone mission execution for most assigned roles in a live pipeline-patrol scenario

This means the project has progressed beyond paper architecture. It is already operating as an integrated prototype.

## Remaining Work

The current system is functional but not complete. The main remaining tasks are:

- finish endpoint alignment for all assigned drones in the full swarm run
- harden mission execution across all fleet members
- improve failure recovery and mission continuity
- strengthen distributed communication between drones
- prepare the execution stack for companion-computer deployment on real aircraft

The project is therefore at a strong prototyping stage: the core architecture is validated, and the next investment should focus on robustness, scaling, and hardware transition.

## Why Fund This Project

This project is a credible funding candidate for three reasons.

### 1. It solves a real operational problem

The system reduces operator burden while preserving mission structure and drone-level autonomy.

### 2. It is technically differentiated

It combines:

- natural-language mission interpretation
- deterministic rule-based role decomposition
- decentralized drone reasoning
- hardware-oriented communication design

This is not a generic drone UI. It is a mission orchestration stack.

### 3. It already has working integration evidence

The project is not at the idea stage. It already integrates:

- OpenAI-based mission interpretation
- role and matching logic
- ArduPilot SITL
- QGroundControl
- MAVSDK execution paths

That makes it suitable for targeted funding aimed at:

- field-ready robustness
- real hardware trials
- mesh-networked deployment
- mission continuity under degraded communication

## Funding Use

Funding would accelerate:

- completion of decentralized execution across the full fleet
- hardware integration on companion computers
- field testing with real radios and real aircraft
- failure recovery and continuity logic
- safety validation and mission logging
- packaging into a demonstrable research and deployment platform

## Strategic Outcome

The long-term outcome is a practical decentralized swarm control framework that allows one operator to issue mission-level goals while multiple drones coordinate execution through a hardware-ready architecture.

In short:

Rule-Matching Drones is building a bridge from natural-language mission intent to decentralized autonomous drone execution.
