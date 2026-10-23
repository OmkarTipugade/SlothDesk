import { afterEach, describe, expect, it, vi } from 'vitest'
import { api } from './api'

describe('api client', () => {
  afterEach(() => vi.restoreAllMocks())

  it('validates scan response data', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ files: [{ name: 'notes.txt' }] }), { status: 200 }),
    ))

    await expect(api.scan()).rejects.toThrow('scan response was malformed')
  })

  it('surfaces backend errors from non-2xx responses', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ detail: 'Ollama is unavailable' }), { status: 503 }),
    ))

    await expect(api.plan()).rejects.toThrow('Ollama is unavailable')
  })

  it('turns network failures into a useful message', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('failed')))

    await expect(api.health()).rejects.toThrow('Unable to reach the SlothDesk backend')
  })
})
