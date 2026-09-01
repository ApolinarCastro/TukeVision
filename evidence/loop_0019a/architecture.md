# QW-04 architecture

Existing camera flow → bounded per-camera temporal buffer → selected
BehaviorSignal → EvidenceClipAdapter → PyAV → clip metadata/ref → QW-00
review record. Static JPEG evidence remains preserved as fallback. No second
capture path, SourceManager, inference pipeline, or PersistentEvidence rewrite.
