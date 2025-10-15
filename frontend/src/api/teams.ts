import { apiClient } from './client'

export interface Team {
  id: number
  name: string
  webhook_url?: string | null
  description?: string | null
  created_at?: number
  updated_at?: number
  members?: string[]
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
