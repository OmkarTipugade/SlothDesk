import type { ApplyResult, FileRecord, Health, PlanAction } from '../types'

const baseUrl = (import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000').replace(/\/$/, '')
const timeoutMs = 10_000

class ApiError extends Error {
  constructor(message: string, readonly status?: number) {
    super(message)
    this.name = 'ApiError'
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const controller = new AbortController()
  const timeout = window.setTimeout(() => controller.abort(), timeoutMs)
  try {
    const response = await fetch(`${baseUrl}${path}`, {
      ...init,
      headers: { Accept: 'application/json', 'Content-Type': 'application/json', ...init?.headers },
      signal: controller.signal,
    })
    const text = await response.text()
    let body: unknown
    try {
      body = text ? JSON.parse(text) : undefined
    } catch {
      throw new ApiError('The backend returned an invalid response.', response.status)
    }
    if (!response.ok) {
      const detail = typeof body === 'object' && body !== null && 'detail' in body
        ? String(body.detail)
        : `Request failed with status ${response.status}.`
      throw new ApiError(detail, response.status)
    }
    return body as T
  } catch (error) {
    if (error instanceof ApiError) throw error
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw new ApiError('The request timed out. Is the SlothDesk backend running?')
    }
    throw new ApiError('Unable to reach the SlothDesk backend.')
  } finally {
    window.clearTimeout(timeout)
  }
}

function isFileRecord(value: unknown): value is FileRecord {
  if (typeof value !== 'object' || value === null) return false
  const item = value as Record<string, unknown>
  return typeof item.name === 'string' && typeof item.relative_path === 'string' &&
    typeof item.extension === 'string' && typeof item.size_bytes === 'number'
}

export const api = {
  health: async () => {
    const data = await request<Health>('/api/health')
    if (!data || typeof data.status !== 'string') throw new ApiError('The health response was malformed.')
    return data
  },
  scan: async () => {
    const data = await request<{ files: unknown }>('/api/scan')
    if (!data || !Array.isArray(data.files) || !data.files.every(isFileRecord)) {
      throw new ApiError('The scan response was malformed.')
    }
    return data.files
  },
  plan: async () => {
    const data = await request<{ actions: PlanAction[] }>('/api/plan', { method: 'POST', body: JSON.stringify({}) })
    if (!data || !Array.isArray(data.actions)) throw new ApiError('The plan response was malformed.')
    return data.actions
  },
  apply: (actions: PlanAction[]) => request<ApplyResult>('/api/apply', {
    method: 'POST',
    body: JSON.stringify({ actions, confirmed: true }),
  }),
}

export { ApiError, baseUrl }

