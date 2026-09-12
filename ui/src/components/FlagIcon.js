import { Fragment } from "react";

/**
 * Inline SVG flags (4:3). Emoji flags do not render on Windows —
 * Segoe UI Emoji ships no country-flag glyphs, so browsers fall back
 * to the two-letter codes. SVG is consistent on every platform.
 */

function usStars() {
  // 50-star layout: 9 rows (6/5 alternating) inside the canton.
  const stars = [];
  for (let row = 0; row < 9; row += 1) {
    const count = row % 2 === 0 ? 6 : 5;
    const y = 14.4 + row * 28.7;
    for (let col = 0; col < count; col += 1) {
      const x = (count === 6 ? 21.3 : 42.7) + col * 42.7;
      stars.push(<use key={`${row}-${col}`} href="#flag-us-star" x={x} y={y} />);
    }
  }
  return stars;
}

const FLAG_ART = {
  us: (
    <Fragment>
      <defs>
        <path
          id="flag-us-star"
          d="M0 -4.8 L1.4 -1.4 L4.8 0 L1.4 1.4 L0 4.8 L-1.4 1.4 L-4.8 0 L-1.4 -1.4 Z"
          fill="#fff"
        />
      </defs>
      <rect width="640" height="480" fill="#fff" />
      <g fill="#B22234">
        {[0, 2, 4, 6, 8, 10, 12].map((i) => (
          <rect key={i} y={(i * 480) / 13} width="640" height={480 / 13} />
        ))}
      </g>
      <rect width="256" height="258.5" fill="#3C3B6E" />
      {usStars()}
    </Fragment>
  ),
  br: (
    <Fragment>
      <rect width="640" height="480" fill="#009C3B" />
      <path d="M320 52 L600 240 L320 428 L40 240 Z" fill="#FFDF00" />
      <circle cx="320" cy="240" r="98" fill="#002776" />
      <path
        d="M234 202 Q320 298 406 202"
        fill="none"
        stroke="#fff"
        strokeWidth="11"
      />
      <path
        d="M242 230 Q320 314 398 230"
        fill="none"
        stroke="#fff"
        strokeWidth="7"
      />
      <g fill="#fff">
        <circle cx="286" cy="216" r="2.6" />
        <circle cx="322" cy="236" r="2.6" />
        <circle cx="352" cy="256" r="2.6" />
        <circle cx="316" cy="282" r="2.6" />
        <circle cx="278" cy="266" r="2.6" />
        <circle cx="352" cy="216" r="2" />
        <circle cx="300" cy="300" r="2" />
      </g>
    </Fragment>
  ),
  fr: (
    <Fragment>
      <rect width="213.3" height="480" fill="#0055A4" />
      <rect x="213.3" width="213.4" height="480" fill="#fff" />
      <rect x="426.7" width="213.3" height="480" fill="#EF4135" />
    </Fragment>
  ),
  es: (
    <Fragment>
      <rect width="640" height="480" fill="#F1BF00" />
      <rect width="640" height="120" fill="#AA151B" />
      <rect y="360" width="640" height="120" fill="#AA151B" />
      <g transform="translate(320 196)">
        <path
          d="M0 -42 L36 -42 L36 6 Q36 38 0 54 Q-36 38 -36 6 L-36 -42 Z"
          fill="#C60B1E"
          stroke="#FFC400"
          strokeWidth="5"
        />
        <rect x="-15" y="-33" width="10" height="13" fill="#FFC400" />
        <rect x="5" y="-33" width="10" height="13" fill="#FFC400" />
        <rect x="-15" y="-14" width="10" height="11" fill="#FFC400" />
        <rect x="5" y="-14" width="10" height="11" fill="#FFC400" />
        <rect x="-12" y="4" width="24" height="11" rx="5" fill="#FFC400" />
      </g>
    </Fragment>
  ),
};

export default function FlagIcon({ code, title }) {
  if (!FLAG_ART[code]) {
    return null;
  }
  return (
    <svg
      className="flag-icon-svg"
      viewBox="0 0 640 480"
      role="img"
      aria-label={title}
    >
      {FLAG_ART[code]}
    </svg>
  );
}
