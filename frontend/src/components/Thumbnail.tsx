interface Props {
  path: string | null
  size?: number
  alt?: string
}

export function Thumbnail({ path, size = 56, alt = '' }: Props) {
  const style = { width: size, height: size }
  if (!path) {
    return (
      <div style={style} className="bg-slate-200 rounded flex items-center justify-center text-slate-400 text-xs">
        —
      </div>
    )
  }
  return (
    <img
      src={`/api/preview/${encodeURI(path)}`}
      alt={alt}
      style={style}
      className="rounded object-cover bg-slate-100"
      loading="lazy"
    />
  )
}
