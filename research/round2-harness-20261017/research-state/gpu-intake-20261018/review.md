# GPU-first intake review

Independent static review completed in two passes. Findings addressed: unknown SSH/probe observations were incorrectly hard-blocked; default BF16 checks could allocate an emulation tensor without explicit smoke; allocation filtering happened after device operations; numerical smoke needed an exact-output check; interpreter realpath alone could confuse virtual environments; real CUDA UUID strings needed canonical NVIDIA mapping. Final consistency finding was resolved by requiring typed GPU-/MIG- allocation IDs before probing. Parent inspected this final validator and corresponding regression.

No universal experiment feasibility, native scorer qualification, or multi-GPU communication qualification is claimed. This standalone helper does not change controller admission or repin existing projects. GPU-first prompting and stage feasibility requirements are wired into the Skill and runtime guidance; their use still requires the agent/reviewer workflow.
