# Responders

Task-specific QA and simulation responders live here.

- `TaskSamplerResponder` can emit scripted or sampled tap sequences for the synchronization and continuation windows.
- The same responder also returns space-key continue actions for the instruction, ready, break, and goodbye screens.
- Scripted sim uses `config/config_scripted_sim.yaml`.
- Sampler sim uses `config/config_sampler_sim.yaml` and points to `responders.task_sampler:TaskSamplerResponder`.
