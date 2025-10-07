import { apiClient } from './client'
import type { ProjectWebhookConfig } from './settings'

interface ApiResponse<T> {
  success: boolean
  data: T
  message?: string
}

export interface ProjectOverview {
  project_name: string
  mr_review_count: number
  push_review_count: number
  total_review_count: number
  last_review_at: number | null
  webhook_config?: ProjectWebhookConfig | null
  webhook_enabled_channels: string[]
}

export type ProjectSummary = ProjectOverview

export const getProjectsOverview = async (search?: string): Promise<ProjectOverview[]> => {
  const response = await apiClient.get<ApiResponse<ProjectOverview[]>>('/api/projects', {
    params: search ? { search } : undefined
  })
  return response.data.data
}

export const getProjectSummary = async (projectName: string): Promise<ProjectSummary> => {
  const response = await apiClient.get<ApiResponse<ProjectSummary>>(
    `/api/projects/${encodeURIComponent(projectName)}/summary`
  )
  return response.data.data
}
