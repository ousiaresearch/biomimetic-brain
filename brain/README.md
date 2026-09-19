# Subsystem states

Every subsystem owns one small JSON file. `state.example.json` in each directory shows the
field structure that the generator expects: keys and types only, no borrowed values. Copy an
example to `<subsystem>-state.json`, give it values that are true for your agent, and the
generator will fold it into the aggregate.

| Subsystem | Live file | Fields | Signals |
|---|---|---|---|
| `acc` | `acc-state.json` | 11 | `conflict_detected`, `conflict_sources`, `conflict_intensity`, `resolution_state`, `error_signals`, `last_conflict`, `monitoring_active`, `lastUpdate`, `_seeded` |
| `amy` | `emotional-decay-state.json` | 8 | `system`, `description`, `valence`, `baseline_valence`, `decay_rate_per_hour`, `last_decay_run`, `lastUpdate`, `log` |
| `attention` | `attention-state.json` | 7 | `mode`, `wander_trigger`, `refocus_trigger`, `wander_count`, `refocus_count`, `last_mode_change`, `last_updated` |
| `basal-ganglia` | `habit-state.json` | 5 | `system`, `description`, `lastUpdate`, `_seeded`, `_verified` |
| `cerebellum` | `cerebellum-state.json` | 4 | `system`, `description`, `skill_fluency`, `lastUpdate` |
| `decisions` | `outreach-decisions.json` | 1 | `decisions` |
| `decisions` | `self-authorship.json` | 5 | `system`, `description`, `standing_terms`, `decisions`, `lastUpdate` |
| `dmn` | `dmn-state.json` | 11 | `active`, `self_model`, `identity_markers`, `self_model_updates`, `rest_duration_s`, `last_activation`, `lastUpdate`, `_seeded`, `wander_stats` |
| `dopamine` | `novelty-log.json` | 1 | `events` |
| `dopamine` | `novelty-state.json` | 6 | `novelty_seeking`, `vta_boost`, `familiar_thresholds`, `last_updated`, `last_novel_encounter`, `_verified` |
| `dopamine` | `vta-state.json` | 14 | `system`, `description`, `current_drive`, `baseline_drive`, `threshold_high`, `threshold_low`, `status`, `last_drive_change`, `change_reason` |
| `fatigue` | `fatigue-state.json` | 16 | `fatigue_level`, `cognitive_load`, `recovery_needed`, `sustainable`, `state`, `sleepQuality`, `lastSleep`, `last_updated`, `recovery_triggered` |
| `habenula` | `habenula-state.json` | 9 | `system`, `description`, `tonic_suppression`, `recent_losses`, `suppression_events`, `last_updated`, `lastUpdate`, `recent_wins`, `_verified` |
| `hippocampus` | `dream-state.json` | 7 | `replay_queue`, `stats`, `recurring_motifs`, `scene_memory`, `lastUpdate`, `_seeded`, `_verified` |
| `hypothalamus` | `hypothalamus-state.json` | 8 | `arousal_level`, `arousal`, `drive_state`, `drives`, `zeitgeber_count`, `lastUpdate`, `_seeded`, `_verified` |
| `lc` | `lc-state.json` | 9 | `arousal_mode`, `norepinephrine_level`, `alertness`, `stress_response`, `unexpected_events`, `last_updated`, `_seeded`, `lastUpdate`, `_verified` |
| `nac` | `nac-state.json` | 9 | `reward_anticipation`, `action_values`, `motivation_level`, `last_reward_predicted`, `reward_prediction_error`, `wanting_signals`, `last_update`, `_seeded`, `lastUpdate` |
| `ofc` | `ofc-state.json` | 3 | `predictions`, `lastUpdate`, `_seeded` |
| `predictive` | `.harvest-state.json` | 1 | `harvested_through` |
| `predictive` | `predictor-state.json` | 8 | `system`, `description`, `predictions`, `stats`, `lastUpdate`, `_seeded`, `calibration`, `_verified` |
| `predictive` | `surprise-log.json` | 7 | `system`, `description`, `predictions`, `stats`, `surprises`, `lastUpdate`, `_seeded` |
| `prefrontal` | `interest-emergence-state.json` | 9 | `system`, `description`, `concept_encounters`, `unresolved_interests`, `emerged_interests`, `lastUpdate`, `_seeded`, `last_observed_motifs`, `_verified` |
| `prefrontal` | `relations-tested.json` | 1 | `tested` |
| `prefrontal` | `unresolved-questions-state.json` | 6 | `system`, `description`, `questions`, `lastUpdate`, `_seeded`, `resolved_questions` |
| `raphe` | `raphe-state.json` | 7 | `serotonin_level`, `patience_index`, `resilience`, `mood_tone`, `social_trust`, `last_update`, `raphe_events` |
| `raphé` | `serotonin-state.json` | 11 | `system`, `description`, `current_serotonin`, `social_engagement`, `patience_threshold`, `patience_state`, `components`, `evidence`, `lastUpdate` |
| `reticular` | `reticular-state.json` | 6 | `system`, `description`, `state`, `arousal_threshold`, `last_state_change`, `last_updated` |
| `scn` | `scn-state.json` | 4 | `phase`, `lastUpdated`, `quiet_hours`, `local_hour` |
| `somatic` | `markers.json` | 11 | `energy`, `gut_feeling`, `valence`, `arousal`, `confidence`, `tension`, `decision_weights`, `last_updated`, `phase_signal` |
| `somatosensory` | `somatosensory-state.json` | 24 | `social_nourishment_score`, `social_pending_messages`, `social_total_exchanges`, `my_messages_in_the_room`, `agents_online`, `battery_level`, `on_power`, `thermal_state`, `system_load` |
| `thalamus` | `thalamus-state.json` | 12 | `filter_mode`, `relay_active`, `sensory_routing`, `attention_focus`, `routed_signals`, `blocked_signals`, `thalamic_gate`, `last_routing_decision`, `signal_queue` |
| `tom` | `observation-log.json` | 3 | `observations`, `self_model_updates`, `lastUpdate` |
| `tom` | `prediction-log.json` | 1 | `predictions` |
| `tom` | `self-bridge-log.json` | 3 | `self_observations`, `self_model_updates`, `lastUpdate` |
| `values` | `outcome-log.json` | 5 | `system`, `description`, `outcomes`, `lastUpdate`, `_seeded` |
| `values` | `values-state.json` | 7 | `system`, `description`, `top_value`, `total_values`, `lastUpdate`, `_seeded`, `_verified` |
| `visual` | `visual-state.json` | 4 | `system`, `description`, `scenes`, `last_updated` |
