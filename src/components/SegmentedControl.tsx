import type { ReactNode } from 'react'

export interface SegmentOption<T> {
  value: T
  label: ReactNode
}

interface SegmentedControlProps<T> {
  /** Accessible name for the group. */
  label: string
  options: readonly SegmentOption<T>[]
  value: T
  onChange: (value: T) => void
}

/** A row of toggle buttons where exactly one is pressed. */
export function SegmentedControl<T extends string | number>({
  label,
  options,
  value,
  onChange,
}: SegmentedControlProps<T>) {
  return (
    <div className="segmented" role="group" aria-label={label}>
      {options.map((option) => (
        <button
          key={option.value}
          type="button"
          className="segmented__option"
          aria-pressed={option.value === value}
          onClick={() => onChange(option.value)}
        >
          {option.label}
        </button>
      ))}
    </div>
  )
}
