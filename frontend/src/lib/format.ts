export function formatUSD(v: number, digits = 4): string {
  return `$${v.toFixed(digits)}`
}

export function formatTokens(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(2)}M`
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}k`
  return String(n)
}

export function formatDateShort(s: string | null): string {
  if (!s) return '—'
  const d = new Date(s)
  return d.toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}
