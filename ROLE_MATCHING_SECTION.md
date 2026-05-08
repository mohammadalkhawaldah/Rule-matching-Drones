# Role-Matching Methodology

## 1. Overview

This work develops a deterministic role-matching framework for decentralized multi-UAV mission execution. The objective of the framework is to translate a mission request into a set of executable swarm roles and to assign those roles to drones using explicit capability constraints rather than stochastic optimization, learned ranking, or centralized bidding. The resulting method is designed to be interpretable, reproducible, and suitable for transition from software-in-the-loop simulation to real hardware deployment.

The implemented pipeline contains four tightly coupled stages:

1. natural-language mission interpretation
2. deterministic role decomposition
3. local capability feasibility evaluation
4. deterministic role-to-drone matching

Although the overall project includes communication and execution layers, the present section focuses on the role-matching component: how mission semantics are transformed into concrete swarm roles and how those roles are matched to available drones.

## 2. Design Rationale

The role-matching framework was designed under three constraints.

First, the operator interface must remain simple. The operator should be able to express missions in plain language rather than manually configuring all drone actions.

Second, the decomposition from mission intent to executable roles must be deterministic. If the same mission statement is submitted repeatedly, the system should generate the same semantic mission structure, the same required roles, and the same matching outcome, provided that the fleet definition is unchanged.

Third, the downstream logic must remain compatible with decentralized execution. The mission may be introduced from a ground station, but each drone should still retain a local notion of whether it is capable of executing a given role. For this reason, the matching logic is explicitly capability-based and avoids opaque learned scores.

## 3. Mission Representation

The framework uses an intermediate semantic mission representation. A natural-language mission is first converted into a structured JSON-like object containing the mission attributes required for downstream reasoning. The implemented schema includes:

- `mission_type`
- `environment`
- `location`
- `objective`
- `mission_style`
- `coordination_required`
- `global_visibility_required`
- `num_drones`
- `preferred_roles`
- `constraints`

This representation serves two purposes. First, it isolates the uncertainty of natural-language interpretation from the deterministic downstream logic. Second, it defines a compact semantic layer that can be reused by role generation, local feasibility reasoning, matching, and execution.

An example mission statement such as:

> Deploy four drones to patrol the pipeline corridor and monitor for suspicious activity.

is converted into a semantic mission object with the key attributes:

- `mission_type = corridor_patrol`
- `environment = pipeline_corridor`
- `num_drones = 4`
- `objective = monitor for suspicious activity`
- `preferred_roles = [corridor_patrol_A, corridor_patrol_B, overwatch, relay]`

This semantic layer is generated in the current implementation by the mission parser in [mission_parser.py](C:/Users/moham/OneDrive/Documents/Rule-Based-Drones/mission_parser.py).

## 4. Deterministic Role Decomposition

### 4.1 Principle

Role decomposition is implemented as a deterministic rule engine rather than an LLM-driven generator. The reason for this separation is methodological: natural-language interpretation is inherently probabilistic, but role decomposition must remain stable, testable, and easy to validate. Therefore, once a mission has been mapped into the semantic representation, the required role set is produced through fixed templates and explicit capability requirements.

This logic is implemented in [role_engine.py](C:/Users/moham/OneDrive/Documents/Rule-Based-Drones/role_engine.py).

### 4.2 Supported Role Templates

The current implementation includes explicit templates for five mission families:

1. solar-field thermal inspection
2. farm-sector livestock search
3. pipeline corridor patrol
4. wind-farm visual inspection
5. forest-edge search with overwatch

For example, the pipeline corridor patrol template always produces the following role set:

- `corridor_patrol_A`
- `corridor_patrol_B`
- `overwatch`
- `relay`

Each role is associated with a required capability set. For the corridor patrol case:

- `corridor_patrol_A`: `stability_flight`, `visual_camera`, `corridor_tracking`
- `corridor_patrol_B`: `stability_flight`, `visual_camera`, `corridor_tracking`
- `overwatch`: `high_altitude`, `good_battery`, `wide_area_observation`
- `relay`: `communications_relay`, `stationary_hold`, `battery_reserve`

This means that the semantic mission is not directly matched to drones. Instead, it is first decomposed into a finite set of explicit roles, and only those roles are matched to fleet members.

### 4.3 Deterministic Behavior

The decomposition is deterministic in the strict sense that:

- the same semantic mission input always yields the same role list
- role names remain stable
- required capabilities remain stable
- the role order remains stable

This property is central to reproducibility. In an experimental or deployment setting, deterministic role decomposition allows the researcher or operator to trace any downstream behavior back to a specific role template rather than to a hidden generative process.

## 5. Drone Capability Modeling

### 5.1 Local Capability Definition

Each drone is represented as an autonomous software agent with a unique identifier and a finite set of capabilities. This abstraction is implemented in [drone_agent.py](C:/Users/moham/OneDrive/Documents/Rule-Based-Drones/drone_agent.py).

The capability model includes attributes such as:

- `thermal_camera`
- `high_resolution_camera`
- `visual_camera`
- `inspection_flight`
- `sector_coverage`
- `low_altitude_search`
- `agile_flight`
- `stability_flight`
- `corridor_tracking`
- `terrain_following`
- `high_altitude`
- `good_battery`
- `wide_area_observation`
- `communications_relay`
- `stationary_hold`
- `battery_reserve`

Each drone stores only its own capability set. This design supports later migration to a decentralized architecture in which local drone software can reason about its own suitability without requiring a global optimizer.

### 5.2 Feasibility Criterion

The feasibility test for a role is implemented as a subset check:

\[
\text{feasible}(d, r) =
\begin{cases}
1, & \text{if } C_r \subseteq C_d \\
0, & \text{otherwise}
\end{cases}
\]

where:

- \( d \) denotes a drone
- \( r \) denotes a role
- \( C_d \) denotes the drone capability set
- \( C_r \) denotes the role required-capability set

This criterion is intentionally strict. A drone is considered capable of fulfilling a role only if it possesses all required capabilities. No partial suitability score is used.

## 6. Matching Algorithm

### 6.1 Matching Objective

The goal of matching is to produce a one-to-one assignment between roles and drones, subject to capability feasibility and the restriction that each drone occupies at most one role in a given mission cycle.

The implemented matching engine is located in [matching_engine.py](C:/Users/moham/OneDrive/Documents/Rule-Based-Drones/matching_engine.py).

### 6.2 Ordered First-Feasible Matching

The implemented algorithm follows a deterministic first-feasible procedure:

1. sort drones lexicographically by `drone_id`
2. compute, for each role, the set of eligible drones
3. process roles in the order generated by the role engine
4. assign the first eligible drone that has not already been assigned
5. continue until all roles have been processed

The algorithm does not perform:

- global optimization
- learned ranking
- auction-based bidding
- utility scoring
- probabilistic tie-breaking

Thus, the method is deterministic both in role creation and in role assignment.

### 6.3 Match Report Structure

For each mission, the engine produces:

- `drone_feasibility`: the set of roles each drone can satisfy
- `role_matches`: each role with its eligible drones and final assignment state
- `final_assignments`: the final one-to-one selected role-to-drone pairs
- `unresolved_roles`: any roles that remain unassigned
- `summary`: counts of matched, contested, singleton, and unmatched roles

This structure is useful for both runtime execution and post-hoc analysis.

## 7. Worked Example

### 7.1 Mission

Consider the mission:

> Deploy four drones to patrol the pipeline corridor and monitor for suspicious activity.

### 7.2 Generated Roles

The role engine generates:

1. `corridor_patrol_A`
2. `corridor_patrol_B`
3. `overwatch`
4. `relay`

### 7.3 Fleet Feasibility

Using the current six-drone logical fleet in [operator.py](C:/Users/moham/OneDrive/Documents/Rule-Based-Drones/operator.py), the relevant feasibility sets are:

- `drone_2`: `corridor_patrol_A`, `corridor_patrol_B`
- `drone_5`: `corridor_patrol_A`, `corridor_patrol_B`
- `drone_6`: `corridor_patrol_A`, `corridor_patrol_B`, `overwatch`
- `drone_1`: `overwatch`
- `drone_4`: `overwatch`, `relay`

### 7.4 Matching Outcome

Because the drones are processed in sorted order and the roles are processed in fixed order, the matching engine selects:

- `drone_2 -> corridor_patrol_A`
- `drone_5 -> corridor_patrol_B`
- `drone_1 -> overwatch`
- `drone_4 -> relay`

The reasoning is fully transparent:

- `corridor_patrol_A` is assigned first to the first feasible unassigned drone, `drone_2`
- `corridor_patrol_B` is then assigned to the next feasible unassigned drone, `drone_5`
- `overwatch` is assigned to `drone_1`, the first feasible unassigned overwatch-capable drone
- `relay` is assigned to `drone_4`, which is the only relay-capable drone

This example illustrates the deterministic nature of the framework. No randomness or hidden ranking contributes to the assignment.

## 8. Relation to Decentralization

The current implementation uses a centralized script to construct the mission package and execute a simulation run. However, the role-matching logic itself was deliberately structured to be compatible with decentralized deployment.

This compatibility is achieved by separating:

- mission interpretation
- deterministic role definition
- local capability feasibility
- execution control

The most important decentralization-oriented property is that capability evaluation is local in concept. Each drone model knows only its own capability set and can independently determine whether a given role is feasible. This creates a direct path toward a future architecture in which:

- the mission package is distributed to the swarm
- drones locally evaluate feasible roles
- the swarm resolves contention through lightweight peer-to-peer coordination

The present implementation therefore serves both as a working prototype and as a structural precursor to a more fully distributed system.

## 9. Advantages of the Proposed Approach

The developed role-matching framework provides several practical advantages.

### 9.1 Interpretability

Every assignment can be explained directly in terms of:

- mission template
- role requirements
- drone capabilities
- deterministic ordering

This is valuable for engineering review, safety validation, and operator trust.

### 9.2 Reproducibility

The deterministic design ensures that the same mission and the same fleet state yield the same role structure and the same matching output. This property is particularly important for experimental evaluation and benchmarking.

### 9.3 Hardware Transition

Because the matching logic is rule-based and lightweight, it is suitable for deployment on companion-computer architectures with constrained compute budgets. It does not rely on cloud inference or online optimization during the actual matching stage.

### 9.4 Modularity

The framework cleanly separates:

- semantic parsing
- role decomposition
- local feasibility reasoning
- matching
- execution

This makes the system easier to test, modify, and extend.

## 10. Current Limitations

The current role-matching method also has limitations.

First, the matching engine uses deterministic first-feasible assignment rather than a globally optimal assignment rule. While this keeps the logic simple and reproducible, it may not always maximize overall mission utility.

Second, the role templates are currently hand-defined for a finite set of mission families. Extending the system to broader mission classes will require additional semantic templates or a more formal mission ontology.

Third, the present implementation of decentralized behavior is still partial. Capability reasoning is structured for decentralization, but final contention resolution is not yet implemented as a live peer-to-peer onboard negotiation process.

Fourth, execution support currently covers the main role families in software-in-the-loop testing, but full hardware validation across all possible fleet assignments remains future work.

## 11. Summary

The developed role-matching approach converts mission intent into swarm behavior through a deterministic sequence of semantic parsing, role decomposition, local capability evaluation, and explicit matching. The method avoids opaque or stochastic decision layers in the core matching process and instead emphasizes interpretability, reproducibility, and hardware-oriented design.

In its current form, the framework demonstrates a practical way to bridge natural-language mission specification and executable multi-UAV coordination while preserving a clear path toward decentralized deployment.
