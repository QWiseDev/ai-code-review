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

export interface GitLabProject {
  id: number
  name: string
  path: string
  path_with_namespace: string
  description: string
  web_url: string
  namespace: any
  visibility: string
  last_activity_at?: string
  created_at?: string
}

export interface GetGitLabProjectsPayload {
  source_type: 'user' | 'group'
  group_id?: string
  gitlab_url?: string
  gitlab_token?: string
}

export interface ImportProjectsPayload {
  projects: Array<{
    name: string
    path_with_namespace: string
  }>
}

export interface ImportProjectsResult {
  imported: number
  total: number
  errors: string[]
}

export const getGitLabProjects = async (payload: GetGitLabProjectsPayload): Promise<GitLabProject[]> => {
  const response = await apiClient.post<ApiResponse<GitLabProject[]>>(
    '/api/projects/gitlab-projects',
    payload
  )
  return response.data.data
}

export const importProjectsFromGitLab = async (payload: ImportProjectsPayload): Promise<ImportProjectsResult> => {
  const response = await apiClient.post<ApiResponse<ImportProjectsResult>>(
    '/api/projects/import-from-gitlab',
    payload
  )
  return response.data.data
}
