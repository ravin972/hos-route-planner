import { fireEvent, screen } from '@testing-library/react'
import { readFileSync } from 'node:fs'
import path from 'node:path'
import { describe, expect, it, vi } from 'vitest'
import { renderWithProviders } from '../../test/renderWithProviders'
import { LocationCombobox } from './LocationCombobox'

describe('LocationCombobox', () => {
  it('accumulates a rapid sequence of keystrokes into the complete string', () => {
    // Regression test for a Phase 5 bug: typing quickly into this field could drop or scramble
    // characters (e.g. "Chicago" -> "Ciao"). Root cause (isolated by removing useLocationSearch,
    // react-hook-form's onChange and items-array identity one at a time, in a real Chrome tab --
    // only removing the controlled `inputValue` prop fixed it): useCombobox's controlled
    // `inputValue` re-applies this component's own React state to the DOM on every render: under
    // real, fast typing, a native keystroke can land on the DOM faster than the *previous*
    // keystroke's render-commit cycle finishes, and that lagging commit silently overwrites what
    // was just typed. jsdom/RTL's fireEvent flushes each event's state update synchronously within
    // act() before the next one is dispatched, so it cannot reproduce that timing race -- this
    // test instead pins the correct, observable end state (final value == what was typed) as a
    // regression guard; the timing race itself was verified fixed by repeated live-browser typing
    // (see the Phase 5 report: "Sacramento", "Philadelphia Pennsylvania", and repeated "Chicago"
    // trials all typed correctly after the fix, every time).
    const onChange = vi.fn()
    renderWithProviders(<LocationCombobox id="current_location" value={{}} onChange={onChange} />)
    const input = screen.getByRole('combobox')

    let typed = ''
    for (const char of 'Chicago') {
      typed += char
      fireEvent.input(input, { target: { value: typed } })
    }

    expect(input).toHaveValue('Chicago')
    expect(onChange).toHaveBeenLastCalledWith({
      query: 'Chicago',
      label: undefined,
      lat: undefined,
      lng: undefined,
    })
  })

  it('never passes a controlled inputValue to useCombobox (guards the fix itself)', () => {
    // A behavioral test alone can't prove the *mechanism* stays fixed, since jsdom can't
    // reproduce the race that exposed it (see the test above). This greps the source the same way
    // hosGuard.test.ts guards against HOS constants creeping back into the client: it fails loudly
    // if a future change reintroduces `inputValue:` as a controlled prop on useCombobox.
    const source = readFileSync(path.resolve(__dirname, 'LocationCombobox.tsx'), 'utf-8')
    const comboboxCallStart = source.indexOf('useCombobox<LocationSuggestion>({')
    const comboboxCallEnd = source.indexOf('\n\n', comboboxCallStart)
    const comboboxCall = source.slice(comboboxCallStart, comboboxCallEnd)

    expect(comboboxCall).toContain('initialInputValue:')
    // A top-level `inputValue:` key would start its own line (unlike the legitimate
    // `onInputValueChange: ({ inputValue: next }) => ...` callback-parameter destructuring,
    // which never begins a line with "inputValue:").
    expect(comboboxCall).not.toMatch(/^\s*inputValue:/m)
  })
})
