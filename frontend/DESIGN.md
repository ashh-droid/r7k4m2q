# Gate — design decisions

Direction A, *Forecast in Words*, is the primary visual language. It is deliberately not a four-KPI-card dashboard: a single readable sentence carries the decision-time forecast, the chart shows the hour-by-hour evidence, and a revision trail preserves its provenance.

## Visual vocabulary

- **Fog** `#E4E9EA`: open, quiet page background.
- **Ink** `#13262F`: headings, navigation, observed outturn.
- **Deep water** `#1F5E66`: exploratory adjusted estimate.
- **Range tint** `#C9DBDC`: historical interval, visually subordinate to the line.
- **Gale amber** `#B86A0E`: published WINDFOR and retrospective overforecast.
- **Commissioner variable** throughout, with tabular numerals.

No decorative KPI cards, false 'live' indicators, ornamental badges, or generic dashboard breadcrumbs. Navigation is readable text; the day ribbon contains actual data. The default experience is calm and light. A matching night palette follows the system preference.

## Interaction

- The day-ahead forecast is always based on a publication available *before* the selected auction gate, with a transparent five-minute safety margin.
- The trial adjustment only appears when seven complete prior delivery days exist; later outturns never enter its fitted coefficients.
- Outturn is **hidden initially** and deliberately revealed by the user, distinguishing purchase-time knowledge from hindsight.
- Each hour button can be selected with arrows, Home or End; the forecast history is rendered directly below, without changing page.
- The month view is a separate retrospective report, with walk-forward rather than future-trained figures.
- Small screens preserve readable text, horizontally scrollable charts, and keyboard-accessible controls; reduced-motion preferences are respected.

The interface is a pilot analytics tool, not a procurement optimizer. 'Lower reference' intentionally replaces language suggesting a guaranteed wind floor.
