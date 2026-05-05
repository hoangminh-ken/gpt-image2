interface Props {
  path: string | null
  size?: number
  alt?: string
  onClick?: () => void
}

export function Thumbnail({ path, size = 56, alt = '', onClick }: Props) {
  const style = { width: size, height: size }
  if (!path) {
    return (
      <div style={style} className="bg-slate-200 rounded flex items-center justify-center text-slate-400 text-xs">
        —
      </div>
    )
  }
  const img = (
    <img
      src={`/api/preview/${encodeURI(path)}`}
      alt={alt}
      style={style}
      className={`rounded object-cover bg-slate-100 ${onClick ? 'cursor-zoom-in hover:ring-2 hover:ring-blue-400 transition' : ''}`}
      loading="lazy"
    />
  )
  if (onClick) {
    return (
      <button onClick={onClick} className="block" aria-label={`Preview ${alt}`}>
        {img}
      </button>
    )
  }
  return img
}
