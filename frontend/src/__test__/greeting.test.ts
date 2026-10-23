import { describe, expect, it } from 'vitest'
import { getGreeting } from '../lib/greeting'

describe('getGreeting', () => {
  it('returns "Good morning." between 5:00 AM and 11:59 AM', () => {
    const earlyMorning = new Date('2026-10-24T05:00:00')
    const lateMorning = new Date('2026-10-24T11:59:59')
    expect(getGreeting(earlyMorning)).toBe('Good morning.')
    expect(getGreeting(lateMorning)).toBe('Good morning.')
  })

  it('returns "Good afternoon." between 12:00 PM and 4:59 PM', () => {
    const noon = new Date('2026-10-24T12:00:00')
    const lateAfternoon = new Date('2026-10-24T16:59:59')
    expect(getGreeting(noon)).toBe('Good afternoon.')
    expect(getGreeting(lateAfternoon)).toBe('Good afternoon.')
  })

  it('returns "Good evening." from 5:00 PM onwards and before 5:00 AM', () => {
    const evening = new Date('2026-10-24T17:00:00')
    const night = new Date('2026-10-24T23:30:00')
    const midnight = new Date('2026-10-24T00:55:00')
    const dawn = new Date('2026-10-24T04:59:59')
    expect(getGreeting(evening)).toBe('Good evening.')
    expect(getGreeting(night)).toBe('Good evening.')
    expect(getGreeting(midnight)).toBe('Good evening.')
    expect(getGreeting(dawn)).toBe('Good evening.')
  })
})
