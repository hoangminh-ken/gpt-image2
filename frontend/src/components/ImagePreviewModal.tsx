import { useEffect } from 'react'

interface Props {
  src: string | null
  caption?: string
  onClose: () => void
}

export function ImagePreviewModal({ src, caption, onClose }: Props) {
  useEffect(() => {
    if (!src) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    document.body.style.overflow = 'hidden'
    return () => {
      window.removeEventListener('keydown', onKey)
      document.body.style.overflow = ''
    }
  }, [src, onClose])

  if (!src) return null

  return (
    <div
      className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-6"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
    >
      <div
        className="relative max-w-[95vw] max-h-[92vh] flex flex-col items-center gap-3"
        onClick={(e) => e.stopPropagation()}
      >
        <button
          aria-label="Close preview"
          onClick={onClose}
          className="absolute -top-3 -right-3 bg-white text-slate-900 w-9 h-9 rounded-full text-lg font-bold shadow hover:bg-slate-100 z-10"
        >
          ×
        </button>
        <img
          src={src}
          alt={caption || 'preview'}
          className="max-w-[95vw] max-h-[80vh] object-contain rounded shadow-xl bg-white"
        />
        {caption && (
          <div className="bg-white/95 text-slate-700 text-sm px-4 py-2 rounded max-w-[80vw] truncate" title={caption}>
            {caption}
          </div>
        )}
        <div className="text-xs text-white/70">Click outside or press Esc to close · <a href={src} target="_blank" rel="noreferrer" className="underline">Open in new tab</a></div>
      </div>
    </div>
  )
}
