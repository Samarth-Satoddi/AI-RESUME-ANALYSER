import { apiClient } from './client';

export interface JobRequirement {
  id: string;
  requirement_type: string;
  requirement_text: string;
  normalized_skill_name: string;
  category?: string;
  is_required: boolean;
}

export interface Job {
  id: string;
  user_id: string;
  title: string;
  company?: string;
  description: string;
  source_url?: string;
  requirements: JobRequirement[];
  created_at: string;
  updated_at: string;
}

export interface JobCreatePayload {
  title: string;
  company?: string;
  description: string;
  source_url?: string;
}

export const jobApi = {
  createJob: async (payload: JobCreatePayload): Promise<Job> => {
    const { data } = await apiClient.post<Job>('/jobs', payload);
    return data;
  },

  getJobs: async (): Promise<Job[]> => {
    const { data } = await apiClient.get<Job[]>('/jobs');
    return data;
  },

  getJob: async (id: string): Promise<Job> => {
    const { data } = await apiClient.get<Job>(`/jobs/${id}`);
    return data;
  },

  deleteJob: async (id: string): Promise<void> => {
    await apiClient.delete(`/jobs/${id}`);
  },
};
