const GOOD_MAX_MINUTES = 8; // one 5-min poll cycle + buffer
const WARNING_MAX_MINUTES = 20; // a couple of missed cycles

type Status = "good" | "warning" | "critical";

function statusFor(latestSnapshotAt: string | null): { status: Status; label: string } {
  if (!latestSnapshotAt) {
    return { status: "critical", label: "No data" };
  }
  const ageMinutes = (Date.now() - new Date(latestSnapshotAt).getTime()) / 60_000;
  if (ageMinutes <= GOOD_MAX_MINUTES) return { status: "good", label: "Live" };
  if (ageMinutes <= WARNING_MAX_MINUTES) return { status: "warning", label: "Delayed" };
  return { status: "critical", label: "Stalled" };
}

export function FreshnessBadge({ latestSnapshotAt }: { latestSnapshotAt: string | null }) {
  const { status, label } = statusFor(latestSnapshotAt);
  return (
    <span className={`freshness freshness--${status}`}>
      <span className="freshness__dot" aria-hidden="true" />
      {label}
    </span>
  );
}
