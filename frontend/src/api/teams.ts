import { apiClient } from './client'

export interface TeamMember {
  author: string
  name?: string | null
  email?: string | null
  avatar_url?: string | null
  access_level?: number | null
  access_level_name?: string | null
  created_at?: number
  updated_at?: number
}

export interface Team {
  id: number
  name: string
  webhook_url?: string | null
  description?: string | null
  created_at?: number
  updated_at?: number
  members?: TeamMember[]
}

export interface TeamPayload {
  name: string
  webhook_url?: string | null
  description?: string | null
}

interface ApiResponse<T> {
  success: boolean
  data: T
  message?: string
}

interface CreateTeamResponse {
  id: number
  name: string
  webhook_url?: string | null
  description?: string | null
  created_at?: number
  updated_at?: number
  members?: string[]
}

interface AddMembersResponse {
  added: number
  team: Team
}

export const fetchTeams = async (includeMembers = true): Promise<Team[]> => {
  const response = await apiClient.get<ApiResponse<Team[]>>('/api/teams', {
    params: {
      include_members: includeMembers ? '1' : '0'
    }
  })
  return response.data.data || []
}

export const fetchTeamDetail = async (teamId: number, includeMembers = true): Promise<Team> => {
  const response = await apiClient.get<ApiResponse<Team>>(`/api/teams/${teamId}`, {
    params: {
      include_members: includeMembers ? '1' : '0'
    }
  })
  return response.data.data
}

export const createTeam = async (payload: TeamPayload): Promise<CreateTeamResponse> => {
  const response = await apiClient.post<ApiResponse<CreateTeamResponse>>('/api/teams', payload)
  return response.data.data
}

export const updateTeam = async (teamId: number, payload: Partial<TeamPayload>): Promise<Team> => {
  const response = await apiClient.put<ApiResponse<Team>>(`/api/teams/${teamId}`, payload)
  return response.data.data
}

export const deleteTeam = async (teamId: number): Promise<void> => {
  await apiClient.delete<ApiResponse<null>>(`/api/teams/${teamId}`)
}

export const addTeamMembers = async (teamId: number, authors: string[]): Promise<AddMembersResponse> => {
  const response = await apiClient.post<ApiResponse<AddMembersResponse>>(`/api/teams/${teamId}/members`, {
    authors
  })
  return response.data.data
}

export const removeTeamMember = async (teamId: number, author: string): Promise<Team> => {
  const response = await apiClient.delete<ApiResponse<Team>>(
    `/api/teams/${teamId}/members/${encodeURIComponent(author)}`
  )
  return response.data.data
}

export interface SyncFromGitLabPayload {
  source_type: 'project' | 'group'
  source_id: string
  gitlab_url?: string
  gitlab_token?: string
  merge_strategy?: 'replace' | 'merge'
}

export interface SyncFromGitLabResponse {
  success: boolean
  added: number
  removed: number
  total: number
  team: Team
  sync_source: {
    type: string
    id: string
  }
}

export const syncTeamFromGitLab = async (
  teamId: number,
  payload: SyncFromGitLabPayload
): Promise<SyncFromGitLabResponse> => {
  const response = await apiClient.post<ApiResponse<SyncFromGitLabResponse>>(
    `/api/teams/${teamId}/sync-from-gitlab`,
    payload
  )
  return response.data.data
}
