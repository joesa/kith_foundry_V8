import type { CSSProperties } from 'react';

export const typography = {
  heroDisplay: {
    fontFamily: 'var(--font-headline)',
    fontWeight: 900,
    letterSpacing: '-0.05em',
    lineHeight: 0.9,
  } satisfies CSSProperties,

  heroTitle: {
    fontFamily: 'var(--font-headline)',
    fontWeight: 800,
    letterSpacing: '-0.04em',
    lineHeight: 0.95,
  } satisfies CSSProperties,

  sectionTitle: {
    fontFamily: 'var(--font-headline)',
    fontWeight: 800,
    letterSpacing: '-0.025em',
    lineHeight: 1.1,
  } satisfies CSSProperties,

  heading: {
    fontFamily: 'var(--font-headline)',
    fontWeight: 700,
    letterSpacing: '-0.025em',
    lineHeight: 1.3,
  } satisfies CSSProperties,

  subheading: {
    fontFamily: 'var(--font-headline)',
    fontWeight: 700,
    letterSpacing: '-0.015em',
    lineHeight: 1.4,
  } satisfies CSSProperties,

  body: {
    fontFamily: 'var(--font-body)',
    fontWeight: 400,
    lineHeight: 1.625,
  } satisfies CSSProperties,

  bodyMedium: {
    fontFamily: 'var(--font-body)',
    fontWeight: 500,
    lineHeight: 1.625,
  } satisfies CSSProperties,

  caption: {
    fontFamily: 'var(--font-body)',
    fontWeight: 500,
    fontSize: '0.875rem',
    lineHeight: 1.4,
  } satisfies CSSProperties,

  label: {
    fontFamily: 'var(--font-label)',
    fontWeight: 700,
    fontSize: '0.75rem',
    letterSpacing: '0.1em',
    textTransform: 'uppercase' as const,
  } satisfies CSSProperties,

  labelSm: {
    fontFamily: 'var(--font-label)',
    fontWeight: 900,
    fontSize: '0.625rem',
    letterSpacing: '0.1em',
    textTransform: 'uppercase' as const,
  } satisfies CSSProperties,

  telemetry: {
    fontFamily: 'var(--font-sans)',
    fontWeight: 700,
    fontSize: '0.65rem',
    letterSpacing: '0.1em',
    textTransform: 'uppercase' as const,
  } satisfies CSSProperties,

  code: {
    fontFamily: 'var(--font-mono)',
    fontWeight: 400,
    fontSize: '0.875rem',
    lineHeight: 1.6,
  } satisfies CSSProperties,
} as const;
