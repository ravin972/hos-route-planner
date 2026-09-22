import { useCombobox } from 'downshift'
import { useRef, useState } from 'react'
import { Spinner } from '../../components/ui/Spinner'
import { useLocationSearch } from '../../hooks/useLocationSearch'
import { cn } from '../../lib/cn'
import type { LocationSuggestion } from '../../types/trip'

export interface LocationValue {
  label?: string
  lat?: number
  lng?: number
  query?: string
}

interface LocationComboboxProps {
  id: string
  value: LocationValue
  onChange: (value: LocationValue) => void
  onBlur?: () => void
  placeholder?: string
  invalid?: boolean
  describedBy?: string
}

export function LocationCombobox({
  id,
  value,
  onChange,
  onBlur,
  placeholder,
  invalid,
  describedBy,
}: LocationComboboxProps) {
  // Drives the search query only -- deliberately NOT passed back into useCombobox as a controlled
  // `inputValue` (Phase 5 bug fix). A controlled inputValue re-applies this component's own React
  // state to the DOM on every render; under fast typing, native keystrokes can land faster than
  // one full render-commit cycle completes, and the re-applied (lagging) state silently overwrites
  // what was just typed -- reproduced live and isolated to exactly this (removing useLocationSearch,
  // react-hook-form's onChange, and item-array identity each left the bug in place; only removing
  // the controlled `inputValue` prop itself fixed it). Downshift now owns `inputValue` internally
  // (initialInputValue seeds it once, uncontrolled from then on), so its own reducer reads and
  // writes the DOM value directly with no round trip through this component's state.
  const [searchText, setSearchText] = useState(value.label ?? value.query ?? '')
  const { suggestions, isFetching, enabled } = useLocationSearch(searchText)
  // Selection fires before the trailing input-value echo (downshift's callback order follows its
  // internal state-key order: selectedItem, then inputValue) -- this ref lets the input handler
  // recognise "this change is just that echo" without a stale-closure read of React state.
  const lastSelectedRef = useRef<LocationSuggestion | null>(null)

  const { getInputProps, getMenuProps, getItemProps, isOpen, highlightedIndex } =
    useCombobox<LocationSuggestion>({
      items: suggestions,
      initialInputValue: searchText,
      itemToString: (item) => item?.label ?? '',
      onInputValueChange: ({ inputValue: next = '' }) => {
        setSearchText(next)
        if (lastSelectedRef.current && next === lastSelectedRef.current.label) return
        lastSelectedRef.current = null
        onChange({ query: next || undefined, label: undefined, lat: undefined, lng: undefined })
      },
      onSelectedItemChange: ({ selectedItem }) => {
        if (!selectedItem) return
        lastSelectedRef.current = selectedItem
        onChange({
          label: selectedItem.label,
          lat: selectedItem.lat,
          lng: selectedItem.lng,
          query: undefined,
        })
      },
    })

  const showMenu = isOpen && suggestions.length > 0

  return (
    <div className="relative">
      <input
        placeholder={placeholder}
        aria-invalid={invalid || undefined}
        aria-describedby={describedBy}
        className={cn(
          'text-body w-full rounded-sm border px-3 py-2 text-ink',
          'focus:outline-none focus:ring-1',
          invalid
            ? 'border-danger focus:border-danger focus:ring-danger'
            : 'border-border focus:border-accent focus:ring-accent',
        )}
        /* aria-labelledby is overridden to undefined: downshift points it at a label id from its
           own getLabelProps(), which this component's caller (Field.tsx) never renders -- that
           would leave the input mislabelled for assistive tech. The plain <label for=id>
           association Field.tsx already renders is valid and sufficient on its own. */
        {...getInputProps({ id, onBlur, 'aria-labelledby': undefined })}
      />
      {isFetching && enabled && (
        <span className="absolute right-2 top-1/2 -translate-y-1/2">
          <Spinner label="Searching locations" />
        </span>
      )}
      <ul
        {...getMenuProps({ 'aria-labelledby': undefined })}
        className={cn(
          'absolute z-10 mt-1 max-h-60 w-full overflow-auto rounded-sm border border-border bg-surface shadow-sm',
          !showMenu && 'hidden',
        )}
      >
        {showMenu &&
          suggestions.map((item, index) => (
            <li
              key={`${item.lat},${item.lng}`}
              {...getItemProps({ item, index })}
              className={cn(
                'text-body cursor-pointer px-3 py-2',
                highlightedIndex === index ? 'bg-accent-tint text-ink' : 'text-ink-secondary',
              )}
            >
              {item.label}
            </li>
          ))}
      </ul>
    </div>
  )
}
