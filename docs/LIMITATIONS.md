# Limitations and next priorities

## Data semantics

- Sales equal observed fulfilled transactions, not unconstrained demand.
- Missing dates are filled with zero under the daily-export contract; an absent upstream extract would
  need a separate availability flag instead.
- Duplicate dates are summed. This is correct for line-level transactions but may be wrong for duplicate
  snapshots, so production connectors need source-specific keys.
- The public converter removes customer identifiers but is not a general privacy classification tool.

## Forecasting

- v1 contains explainable baselines, not state-of-the-art forecasting models.
- Price, promotion and stockout fields are validated but are not yet explanatory model features.
- Series are selected independently; category, store and total forecasts are not reconciled.
- Residual intervals are heuristic and have no formal calibration guarantee.
- WAPE is undefined when validation actuals total zero and is returned as `null` at JSON boundaries.

## Scenario planning

- Multiplier, additive and override rules are arithmetic overlays.
- Scenario results are not causal estimates of price or promotional lift.
- Rule order is significant and preserved. The interface currently creates one rule at a time, while the
  API supports up to 50 ordered rules.

## Operations and security

- SQLite is suitable for a local single-user workbench, not concurrent planners.
- The API has no login and must remain on loopback. CORS is not an authorization control.
- The HTTP endpoint accepts at most 5 MiB; larger inputs should use the local CLI or a future job queue.
- No retry queue, migration framework, retention policy, telemetry or disaster recovery is included.
- Performance numbers describe one local run and are not a production capacity guarantee.

## Prioritized follow-up

1. Add exogenous calendar, promotion, price and availability features with leakage-safe backtests.
2. Add PostgreSQL migrations, background jobs, OIDC and tenant-aware access.
3. Add hierarchical forecast reconciliation and planner override accuracy tracking.
4. Add inventory, lead time and service-level inputs before producing replenishment recommendations.
5. Calibrate prediction intervals and document empirical coverage by series class.
