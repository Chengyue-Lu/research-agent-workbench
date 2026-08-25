def channel_means(rows):
    """Deterministic fixture: per-channel mean and max delta.

    Re-running this function on the admitted fixture bytes reproduces
    outputs/channel-means.csv byte-for-byte (see runs/RUN-SIM-001).
    """
    sums = {}
    counts = {}
    minimums = {}
    maximums = {}
    for row in rows:
        channel = row["channel"]
        value = float(row["reading_mv"])
        sums[channel] = sums.get(channel, 0.0) + value
        counts[channel] = counts.get(channel, 0) + 1
        minimums[channel] = min(minimums.get(channel, value), value)
        maximums[channel] = max(maximums.get(channel, value), value)
    lines = ["channel,mean_mv,delta_mv"]
    for channel in sorted(sums):
        mean = sums[channel] / counts[channel]
        lines.append(f"{channel},{mean:.2f},{maximums[channel] - minimums[channel]:.1f}")
    return "\n".join(lines) + "\n"
