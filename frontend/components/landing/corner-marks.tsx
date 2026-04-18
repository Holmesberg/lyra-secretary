/**
 * Viewfinder registration marks — four cyan L-shapes anchored to the corners
 * of the parent. Used on display panels, feature cards, and the laptop
 * chrome to read as "system display" rather than "generic card."
 *
 * Parent must be `relative`.
 */
export function CornerMarks({
  size = 14,
  thickness = 1,
  color = "rgba(77, 212, 232, 0.6)",
  offset = -1,
}: {
  size?: number;
  thickness?: number;
  color?: string;
  offset?: number;
}) {
  const base: React.CSSProperties = {
    position: "absolute",
    width: size,
    height: size,
    borderColor: color,
    borderStyle: "solid",
    pointerEvents: "none",
  };
  return (
    <>
      <span
        aria-hidden
        style={{
          ...base,
          top: offset,
          left: offset,
          borderWidth: `${thickness}px 0 0 ${thickness}px`,
        }}
      />
      <span
        aria-hidden
        style={{
          ...base,
          top: offset,
          right: offset,
          borderWidth: `${thickness}px ${thickness}px 0 0`,
        }}
      />
      <span
        aria-hidden
        style={{
          ...base,
          bottom: offset,
          left: offset,
          borderWidth: `0 0 ${thickness}px ${thickness}px`,
        }}
      />
      <span
        aria-hidden
        style={{
          ...base,
          bottom: offset,
          right: offset,
          borderWidth: `0 ${thickness}px ${thickness}px 0`,
        }}
      />
    </>
  );
}
