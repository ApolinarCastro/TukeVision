# LOOP-0018X benchmark report

- External adapter executed: **NO** (N/A baseline comparison).
- Reason: no candidate passed the controlled ingestion gate without new models, data, dependencies, or governance approval.
- Deterministic engine microbenchmark: 10,000 single-track evaluations in 0.208321 s; mean 0.020832 ms/evaluation on the local verification runtime.
- Method: warmed in-process `timeit`, bounded engine retention, no camera/model/network I/O.
- Interpretation: this measures rules-layer overhead only and is not extrapolated to end-to-end camera latency.
- Historical detector figures in TES were not reused as if they measured this layer.
