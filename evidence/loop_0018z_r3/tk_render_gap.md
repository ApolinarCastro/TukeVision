# Tk render gap and reuse

Classification: `REUSE_WITH_MINIMAL_ADAPTATION`.

The existing `TkApp` used one `ttk.Label`, refreshed by `Tk.after`, converting
frames with OpenCV to a single retained `PhotoImage`. R3 reuses that conversion
and timer, materializing four labels and four retained images. `poll_multicamera`
is the sole visual source. No capture, RTSP, inference, or extra thread is
created by Tk.
