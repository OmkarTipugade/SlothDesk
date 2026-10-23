export type FileRecord = {
  name: string
  relative_path: string
  extension: string
  size_bytes: number
}

export type PlanAction = {
  source: string
  destination: string
  reason: string
  category: string
}

export type ApplyResult = {
  moved: string[]
  skipped: string[]
}

export type Health = {
  status: string
  model?: string
  root_directory?: string
}

