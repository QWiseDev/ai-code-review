import { apiClient } from './client'

export interface ProjectWebhookConfig {
  id?: number
  project_name: string
  url_slug?: string | null
  dingtalk_webhook_url?: string | null
  wecom_webhook_url?: string | null
  feishu_webhook_url?: string | null
  extra_webhook_url?: string | null
  dingtalk_enabled?: number
  wecom_enabled?: number
  feishu_enabled?: number
  extra_webhook_enabled?: number
  created_at?: number
  updated_at?: number
}

export interface SaveProjectWebhookConfigPayload {
  project_name: string
  url_slug?: string | null
  dingtalk_webhook_url?: string | null
  wecom_webhook_url?: string | null
  feishu_webhook_url?: string | null
  extra_webhook_url?: string | null
  dingtalk_enabled?: number | boolean
  wecom_enabled?: number | boolean
  feishu_enabled?: number | boolean
  extra_webhook_enabled?: number | boolean
}

export interface ProjectWebhookFilter {
  project_name?: string
  url_slug?: string
}

interface ApiResponse<T> {
  success: boolean
  data: T
  message?: string
}

const normalizeBooleanFlag = (value?: number | boolean | null): number => {
  if (typeof value === 'boolean') {
    return value ? 1 : 0
  }
  if (typeof value === 'number') {
    return value ? 1 : 0
  }
  return 0
}

export const fetchProjectWebhookConfigs = async (
  filters?: ProjectWebhookFilter
): Promise<ProjectWebhookConfig[]> => {
  const response = await apiClient.get<ApiResponse<ProjectWebhookConfig | ProjectWebhookConfig[]>>(
    '/api/project-webhook-config',
    {
      params: filters
    }
  )

  const result = response.data.data

  if (Array.isArray(result)) {
    return result
  }

  return result ? [result] : []
}

export const saveProjectWebhookConfig = async (
  payload: SaveProjectWebhookConfigPayload
): Promise<ApiResponse<null>> => {
  const requestBody = {
    ...payload,
    dingtalk_enabled: normalizeBooleanFlag(payload.dingtalk_enabled),
    wecom_enabled: normalizeBooleanFlag(payload.wecom_enabled),
    feishu_enabled: normalizeBooleanFlag(payload.feishu_enabled),
    extra_webhook_enabled: normalizeBooleanFlag(payload.extra_webhook_enabled)
  }

  const response = await apiClient.post<ApiResponse<null>>('/api/project-webhook-config', requestBody)
  return response.data
}

export const removeProjectWebhookConfig = async (projectName: string): Promise<ApiResponse<null>> => {
  const response = await apiClient.delete<ApiResponse<null>>(
    `/api/project-webhook-config/${encodeURIComponent(projectName)}`
  )
  return response.data
}
