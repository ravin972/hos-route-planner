/**
 * Guard test (architecture.md section 5.0): no HOS threshold may be hardcoded anywhere in the
 * client's *application* source (lib/hooks/components/features/types, App.tsx, main.tsx). Test
 * files are deliberately excluded: captured MSW fixtures and component-test assertions
 * legitimately contain these numbers as real minute-of-day *data* (e.g. a pre-trip ending at
 * minute 480 = 08:00, or a test using a round number as sample input), which is not the same thing
 * as a rule re-implemented in the client.
 */

import { readFileSync, readdirSync, statSync } from 'node:fs'
import path from 'node:path'
import { describe, expect, it } from 'vitest'

const SRC_DIR = path.resolve(__dirname, '..')
const EXCLUDED_DIR_NAMES = new Set(['test'])
const SOURCE_EXTENSIONS = new Set(['.ts', '.tsx'])
const TEST_FILE_PATTERN = /\.test\.tsx?$/

// 11h, 14h, 8h-break-threshold, 70h cycle, 34h restart (all in minutes) -- hos-rules.md section 2.
const HOS_CONSTANTS = [660, 840, 480, 4200, 2040]

function collectSourceFiles(dir: string): string[] {
  const files: string[] = []
  for (const entry of readdirSync(dir)) {
    const fullPath = path.join(dir, entry)
    const stats = statSync(fullPath)
    if (stats.isDirectory()) {
      if (EXCLUDED_DIR_NAMES.has(entry)) continue
      files.push(...collectSourceFiles(fullPath))
      continue
    }
    if (SOURCE_EXTENSIONS.has(path.extname(entry)) && !TEST_FILE_PATTERN.test(entry)) {
      files.push(fullPath)
    }
  }
  return files
}

describe('HOS constants guard', () => {
  it('never hardcodes an HOS threshold in frontend application source', () => {
    const offenders: string[] = []
    for (const file of collectSourceFiles(SRC_DIR)) {
      const content = readFileSync(file, 'utf-8')
      for (const constant of HOS_CONSTANTS) {
        const pattern = new RegExp(`(?<![\\w.])${constant}(?![\\w.])`)
        if (pattern.test(content)) {
          offenders.push(`${path.relative(SRC_DIR, file)}: contains ${constant}`)
        }
      }
    }
    expect(offenders).toEqual([])
  })
})
